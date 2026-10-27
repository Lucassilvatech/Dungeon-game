"""Persist once at creation. Potential resources become economic mass only on collection."""

import hashlib
import logging
from collections import deque
from sqlalchemy import select, func
from fastapi import HTTPException
from . import models as m, lunar, finance
from .clock import utc_now
from .config import runtime_setting, settings

VERSION = "lunar-resource-v1"
WEIGHTS = {"nugget_small": 100000, "nugget_medium": 500000, "nugget_large": 1000000}
CONFIG = {
    "lunar_resource_spawn_enabled",
    "lunar_resource_spawn_chance_ppm",
    "lunar_resource_weight_distribution",
    "lunar_guild_prices",
}
log = logging.getLogger("dungeon.lunar_resources")
log.setLevel(logging.INFO)


def fail(message, status=409):
    raise HTTPException(status, message)


def validate_setting(name, value):
    if name == "lunar_resource_spawn_enabled":
        valid = type(value) is bool
    elif name == "lunar_resource_spawn_chance_ppm":
        valid = type(value) is int and 0 <= value <= 1000000
    else:
        valid = (
            isinstance(value, dict)
            and set(value) == set(WEIGHTS)
            and all(type(v) is int and 0 <= v <= 1000000000 for v in value.values())
        )
        if name == "lunar_resource_weight_distribution":
            valid = valid and sum(value.values()) > 0
    if not valid:
        fail("Configuração Lunar inválida; use inteiros e tamanhos definidos", 422)


def policy(db):
    result = {
        k: runtime_setting(db, k) for k in sorted(CONFIG) if k != "lunar_guild_prices"
    }
    for k, v in result.items():
        validate_setting(k, v)
    return result


def roll(expedition_id, room_id, seed, generation, config):
    """No fresh RNG or secret in a request. Room UUID/seed are server-created."""
    digest = hashlib.sha256(
        f"{VERSION}:{expedition_id}:{room_id}:{seed}:{generation}".encode()
    ).hexdigest()
    if (
        not config["lunar_resource_spawn_enabled"]
        or int(digest[:16], 16) % 1000000 >= config["lunar_resource_spawn_chance_ppm"]
    ):
        return digest, None
    distribution = config["lunar_resource_weight_distribution"]
    ticket = int(digest[16:32], 16) % sum(distribution.values())
    for code in sorted(WEIGHTS):
        ticket -= distribution[code]
        if ticket < 0:
            return digest, code
    raise AssertionError("Distribution exhausted")


def reachable_points(room):
    data = room.data
    walls = {tuple(p) for p in data["walls"]}
    queue = deque([(2, 2)])
    seen = {(2, 2)}
    while queue:
        x, y = queue.popleft()
        for p in [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]:
            if (
                0 <= p[0] < data["width"]
                and 0 <= p[1] < data["height"]
                and p not in walls
                and p not in seen
            ):
                seen.add(p)
                queue.append(p)
    blocked = {(s["x"], s["y"]) for s in data.get("spawns", {}).values()} | {
        (2, 2),
        (2, 9),
    }
    return sorted(seen - blocked)


def generate(db, c, room, expedition):
    lunar.mutex(db)
    old = db.get(m.LunarResourceGeneration, expedition.id)
    if old:
        return old
    if (
        room.owner_id != c.id
        or expedition.character_id != c.id
        or expedition.status != "ACTIVE"
    ):
        fail("Instância privada inválida")
    config = policy(db)
    config["lunar_resource_spawn_enabled"] &= finance.active(db)
    generation = db.get(m.RoomState, (c.id, room.id)).generation
    digest, code = roll(expedition.id, room.id, room.seed, generation, config)
    points = reachable_points(room)
    record = m.LunarResourceGeneration(
        expedition_id=expedition.id,
        room_id=room.id,
        generation=generation,
        version=VERSION,
        group_snapshot={"mode": "SOLO", "member_ids": [c.id]},
        config_snapshot=config,
        decision_hash=digest,
        spawned=bool(code and points),
    )
    db.add(record)
    db.flush()
    if record.spawned:
        asset = db.get(m.LunarAsset, code)
        if not asset or asset.kind != "nugget" or asset.weight_mg != WEIGHTS[code]:
            fail("Definição de pepita incompatível")
        x, y = points[int(digest[32:48], 16) % len(points)]
        db.add(
            m.LunarResourceOccurrence(
                expedition_id=expedition.id,
                room_id=room.id,
                generation=generation,
                spawn_key="lunar:0",
                asset_code=code,
                weight_mg=asset.weight_mg,
                x=x,
                y=y,
            )
        )
        db.flush()
        log.info(
            "resource_spawned expedition=%s weight_mg=%s",
            expedition.id,
            asset.weight_mg,
        )
    return record


def state(db, c):
    # Only reads persisted occurrences. Closed/foreign instances reveal nothing.
    rows = db.scalars(
        select(m.LunarResourceOccurrence)
        .join(m.Expedition, m.Expedition.id == m.LunarResourceOccurrence.expedition_id)
        .where(
            m.Expedition.character_id == c.id,
            m.Expedition.room_id == c.room_id,
            m.Expedition.status == "ACTIVE",
            m.LunarResourceOccurrence.state == "AVAILABLE",
        )
        .order_by(m.LunarResourceOccurrence.id)
    ).all()
    return [
        {
            "id": r.id,
            "expedition_id": r.expedition_id,
            "name": "Minério Lunar",
            "weight_mg": str(r.weight_mg),
            "x": r.x,
            "y": r.y,
            "state": r.state,
        }
        for r in rows
    ]


def nugget_slots(db, c):
    return int(
        db.scalar(
            select(func.coalesce(func.sum(m.LunarHolding.quantity), 0))
            .join(m.LunarAsset, m.LunarAsset.code == m.LunarHolding.asset_code)
            .where(
                m.LunarHolding.account_id == f"player:{c.id}",
                m.LunarAsset.kind == "nugget",
            )
        )
    )


def capacity(db, c, extra=1):
    used = int(
        db.scalar(
            select(func.count())
            .select_from(m.Item)
            .where(m.Item.owner == c.id, m.Item.location == "inventory")
        )
    ) + nugget_slots(db, c)
    if used + extra > settings.collection_slots:
        fail("Mochila sem espaço para pepita; cada pepita ocupa um slot")
    return used


def assert_audit(db):
    r = finance.reconcile(db)
    if r["gap_mg"] != "0" or r["ledger_mismatches"] or r["metadata_mismatches"]:
        fail("Auditoria Lunar rejeitou operação")


def collect(db, c, expedition_id, occurrence_id, request_id):
    lunar.mutex(db)
    key = f"lunar-collect:{c.id}:{request_id}"
    old = db.scalar(select(m.LunarEntry).where(m.LunarEntry.key == key))
    if old:
        if (
            old.context.get("occurrence_id") != occurrence_id
            or old.context.get("expedition_id") != expedition_id
        ):
            fail("Chave já usada em outra coleta")
        return {
            "receipt": old.id,
            "replayed": True,
            "message": "Coleta Lunar já confirmada.",
        }
    from .game import idle
    from .world import distance

    idle(db, c)
    r = db.scalar(
        select(m.LunarResourceOccurrence)
        .where(m.LunarResourceOccurrence.id == occurrence_id)
        .with_for_update()
    )
    g = db.get(m.LunarResourceGeneration, expedition_id)
    e = db.get(m.Expedition, expedition_id)
    if (
        not r
        or not g
        or not e
        or r.expedition_id != e.id
        or c.id not in g.group_snapshot["member_ids"]
        or e.character_id != c.id
        or e.room_id != r.room_id
        or g.room_id != r.room_id
        or g.generation != r.generation
    ):
        fail("Recurso fora da sua instância", 404)
    if r.state != "AVAILABLE":
        log.info("resource_collection_conflict occurrence=%s", r.id)
        fail(
            "RESOURCE_ALREADY_COLLECTED"
            if r.state == "COLLECTED"
            else "RESOURCE_EXPIRED"
        )
    rs = db.get(m.RoomState, (c.id, r.room_id))
    if (
        e.status != "ACTIVE"
        or c.room_id != r.room_id
        or not rs
        or rs.generation != r.generation
    ):
        fail("Expedição encerrada ou instância inválida")
    if distance((c.x, c.y), (r.x, r.y)) > 1:
        fail("Aproxime-se do Minério Lunar")
    if not finance.active(db):
        fail("Cutover Lunar ainda inativo")
    capacity(db, c)
    finance.ensure(db, f"player:{c.id}")
    receipt = lunar.post(
        db,
        key,
        "DISCOVERED_MINERAL",
        f"player:{c.id}",
        "Coleta de ocorrência procedural persistente",
        [(f"player:{c.id}", r.asset_code, 1)],
        source="discovery",
        context={
            "occurrence_id": r.id,
            "expedition_id": e.id,
            "weight_mg": str(r.weight_mg),
        },
    )
    r.state = "COLLECTED"
    r.collected_by = c.id
    r.collected_at = utc_now()
    r.receipt_key = key
    db.flush()
    assert_audit(db)
    log.info(
        "resource_collected occurrence=%s character=%s weight_mg=%s",
        r.id,
        c.id,
        r.weight_mg,
    )
    return {
        "receipt": receipt.id,
        "replayed": False,
        "message": f"Minério Lunar coletado: {r.weight_mg//1000} g.",
        "weight_mg": str(r.weight_mg),
    }


def expire(db, expedition_id):
    for r in db.scalars(
        select(m.LunarResourceOccurrence)
        .where(
            m.LunarResourceOccurrence.expedition_id == expedition_id,
            m.LunarResourceOccurrence.state == "AVAILABLE",
        )
        .with_for_update()
    ):
        r.state = "EXPIRED"
        log.info("resource_expired occurrence=%s", r.id)


def quotes(db, c):
    prices = runtime_setting(db, "lunar_guild_prices")
    validate_setting("lunar_guild_prices", prices)
    held = lunar.balances(db, f"player:{c.id}")
    return [
        {
            "asset_code": a,
            "weight_mg": str(w),
            "quantity": str(held.get(a, 0)),
            "price_units": str(prices[a]),
            "quote": lunar.fingerprint([a, prices[a]]),
        }
        for a, w in WEIGHTS.items()
        if prices[a] > 0
    ]


def sell(db, c, asset, quote, request_id):
    lunar.mutex(db)
    key = f"lunar-sale:{c.id}:{request_id}"
    old = db.scalar(select(m.LunarEntry).where(m.LunarEntry.key == key))
    if old:
        if old.context.get("parameters") != [asset, quote]:
            fail("Chave já usada em outra venda")
        return {
            "receipt": old.id,
            "replayed": True,
            "message": "Venda de minério já confirmada.",
        }
    from .game import idle, receptionist

    idle(db, c)
    receptionist(db, c)
    if not finance.active(db):
        fail("Cutover Lunar ainda inativo")
    offer = next((o for o in quotes(db, c) if o["asset_code"] == asset), None)
    if not offer or quote != offer["quote"]:
        fail("Preço mudou ou compra de minério desativada")
    if int(offer["quantity"]) < 1:
        fail("Pepita inexistente na sua carteira")
    finance.ensure(db, "guild")
    # Real coins only; automatic debt amortization remains in the existing facade.
    finance.move(
        db, "guild", f"player:{c.id}", int(offer["price_units"]), key + ":coins"
    )
    receipt = lunar.post(
        db,
        key,
        "MINERAL_SALE",
        f"player:{c.id}",
        "Venda física de uma pepita à Guilda",
        [(f"player:{c.id}", asset, -1), ("guild", asset, 1)],
        context={
            "parameters": [asset, quote],
            "weight_mg": str(WEIGHTS[asset]),
            "price_units": offer["price_units"],
        },
    )
    assert_audit(db)
    log.info("resource_sale character=%s weight_mg=%s", c.id, WEIGHTS[asset])
    return {
        "receipt": receipt.id,
        "replayed": False,
        "message": "Pepita vendida à Guilda; pagamento físico confirmado.",
    }


def origin_totals(db):
    weights = {a.code: a.weight_mg for a in db.scalars(select(m.LunarAsset))}
    totals = {"genesis_mg": 0, "discovered_mg": 0, "burned_mg": 0}
    for entry in db.scalars(select(m.LunarEntry)):
        net = sum(p["quantity"] * weights[p["asset"]] for p in entry.postings)
        if net > 0:
            totals[
                "genesis_mg" if entry.kind == "GENESIS_BACKING" else "discovered_mg"
            ] += net
        elif net < 0:
            totals["burned_mg"] -= net
    return totals


def audit(db):
    errors = []
    totals = origin_totals(db)
    supply = db.get(m.LunarSupply, 1)
    if supply and (
        totals["genesis_mg"],
        totals["discovered_mg"],
        totals["burned_mg"],
    ) != (supply.legacy_backing_mg, supply.discovered_mg, supply.destroyed_mg):
        errors.append("lunar-supply-origins")
    receipts = {
        e.key: e
        for e in db.scalars(
            select(m.LunarEntry).where(m.LunarEntry.kind == "DISCOVERED_MINERAL")
        )
    }
    for r in db.scalars(
        select(m.LunarResourceOccurrence).where(
            m.LunarResourceOccurrence.state == "COLLECTED"
        )
    ):
        e = receipts.pop(r.receipt_key, None)
        if (
            not e
            or e.context.get("occurrence_id") != r.id
            or e.context.get("weight_mg") != str(r.weight_mg)
            or e.postings
            != [
                {
                    "account": f"player:{r.collected_by}",
                    "asset": r.asset_code,
                    "quantity": 1,
                }
            ]
        ):
            errors.append(f"lunar-occurrence:{r.id}")
    errors += [f"lunar-unbound-discovery:{e.id}" for e in receipts.values()]
    return errors


def metrics(db):
    by_state = {
        state: (int(n), int(w))
        for state, n, w in db.execute(
            select(
                m.LunarResourceOccurrence.state,
                func.count(),
                func.sum(m.LunarResourceOccurrence.weight_mg),
            ).group_by(m.LunarResourceOccurrence.state)
        )
    }
    mass = lambda state: by_state.get(state, (0, 0))[1]
    collected = mass("COLLECTED")
    sold = sum(
        int(e.context["weight_mg"])
        for e in db.scalars(
            select(m.LunarEntry).where(m.LunarEntry.kind == "MINERAL_SALE")
        )
    )
    mineral = {}
    for kind, total in db.execute(
        select(
            m.LunarAccount.kind,
            func.sum(m.LunarHolding.quantity * m.LunarAsset.weight_mg),
        )
        .select_from(m.LunarHolding)
        .join(m.LunarAccount, m.LunarAccount.id == m.LunarHolding.account_id)
        .join(m.LunarAsset, m.LunarAsset.code == m.LunarHolding.asset_code)
        .where(m.LunarAsset.kind == "nugget")
        .group_by(m.LunarAccount.kind)
    ):
        mineral[kind] = str(int(total))
    return {
        "lunar_resource_occurrences_generated": sum(n for n, w in by_state.values()),
        "lunar_resource_occurrences_collected": by_state.get("COLLECTED", (0, 0))[0],
        "lunar_resource_occurrences_expired": by_state.get("EXPIRED", (0, 0))[0],
        "lunar_resource_discovered_mg": str(collected),
        "lunar_resource_collected_mg": str(collected),
        "lunar_resource_sold_to_guild_mg": str(sold),
        "lunar_resource_uncollected_mg": str(mass("AVAILABLE")),
        "lunar_resource_expired_mg": str(mass("EXPIRED")),
        "mineral_by_account_kind_mg": mineral,
        "origin_ledger_mg": {k: str(v) for k, v in origin_totals(db).items()},
    }


def inventory(db, c):
    return [
        {
            "asset_code": h.asset_code,
            "quantity": str(h.quantity),
            "weight_mg": str(a.weight_mg),
        }
        for h, a in db.execute(
            select(m.LunarHolding, m.LunarAsset)
            .join(m.LunarAsset, m.LunarAsset.code == m.LunarHolding.asset_code)
            .where(
                m.LunarHolding.account_id == f"player:{c.id}",
                m.LunarHolding.quantity > 0,
                m.LunarAsset.kind == "nugget",
            )
            .order_by(m.LunarHolding.asset_code)
        )
    ]
