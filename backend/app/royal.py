"""Manual Royal administration, routed through existing preview/confirmation/audit."""

from sqlalchemy import select, func
from . import (
    models as m,
    lunar,
    finance,
    mineral_lots as lots,
    lunar_resources as resources,
)
from .config import runtime_setting

ACTIONS = {
    name: "economy.manage"
    for name in [
        "royal.mint",
        "royal.transfer_lot",
        "royal.transfer_coins",
        "royal.burn",
        "royal.injection",
    ]
}
PARAMS = {
    "royal.mint": {"coins", "lot_ids"},
    "royal.transfer_lot": {"lot_id", "destination"},
    "royal.transfer_coins": {"destination", "amount_units"},
    "royal.burn": {"grams", "coins", "lot_ids", "strong_confirmation"},
    "royal.injection": {"grams", "coins", "strong_confirmation"},
}


def coins(value):
    if not isinstance(value, dict) or set(value) - {
        "coin_small",
        "coin_medium",
        "coin_large",
    }:
        lunar.fail("Informe denominações válidas", 422)
    for v in value.values():
        lunar.integer(v)
    return value


def account(db, id):
    id = finance.normalize(id)
    row = db.get(m.LunarAccount, id)
    if not row:
        lunar.fail("Conta Lunar inexistente", 422)
    return row


def describe(db, action, target, p):
    if not finance.active(db):
        lunar.fail("Conclua o cutover auditado antes de administrar moeda operacional")
    owner = account(db, target).id
    if action in ("royal.burn", "royal.injection") and not runtime_setting(
        db, "royal_admin_extraordinary_controls_enabled"
    ):
        lunar.fail("Controles extraordinários desativados", 403)
    source = lots.held(db, owner)
    ids = p.get("lot_ids")
    if ids is not None and (
        not isinstance(ids, list)
        or len(ids) > 1000
        or any(type(i) is not int or i < 1 for i in ids)
        or len(ids) != len(set(ids))
    ):
        lunar.fail("Lista de pepitas inválida", 422)
    mintmass = 0
    if action == "royal.mint":
        if owner != "treasury":
            lunar.fail("Cunhagem restrita ao Tesouro")
        cs = coins(p.get("coins"))
        mintmass = sum(q * db.get(m.LunarAsset, a).weight_mg for a, q in cs.items())
        if mintmass <= 0:
            lunar.fail("Cunhagem vazia", 422)
    if action in ("royal.transfer_coins", "royal.transfer_lot"):
        destination = account(db, p.get("destination", "")).id
        if owner == destination:
            lunar.fail("Contas devem diferir", 422)
        if action == "royal.transfer_coins":
            lunar.integer(p.get("amount_units"), True)
        else:
            lunar.integer(p.get("lot_id"), True)
    if action in ("royal.injection", "royal.burn"):
        lunar.integer(p.get("grams", 0))
        coins(p.get("coins", {}))
        if p.get("grams", 0) > 1000000000:
            lunar.fail("Peso excede limite administrativo", 422)
        if p.get("strong_confirmation") != (
            "DESTRUIR" if action == "royal.burn" else "INJETAR"
        ):
            lunar.fail("Confirmação forte obrigatória", 422)
        if not p.get("grams", 0) and not any(p.get("coins", {}).values()):
            lunar.fail("Operação vazia", 422)
    # Preview remains readable after execution, including consumed/transferred lots.
    selected = db.get(m.LunarMineralLot, p.get("lot_id")) if p.get("lot_id") else None
    if action == "royal.transfer_lot" and not selected:
        lunar.fail("Pepita inexistente", 404)
    supply = db.get(m.LunarSupply, 1)
    accounts = {owner, p.get("destination", owner)}
    remaining = mintmass
    plan = []
    for lot in source:
        if not remaining:
            break
        if ids is not None and lot.id not in ids:
            continue
        used = min(lot.weight_mg, remaining)
        remaining -= used
        plan.append(
            {
                "lot_id": lot.id,
                "consume_mg": str(used),
                "remaining_mg": str(lot.weight_mg - used),
            }
        )
    affected = p.get("grams", 0) * 1000 + sum(
        q * db.get(m.LunarAsset, a).weight_mg for a, q in p.get("coins", {}).items()
    )
    if action == "royal.transfer_coins":
        affected = p["amount_units"] * 1000
    elif action == "royal.transfer_lot":
        affected = selected.weight_mg
    delta = (
        affected
        if action == "royal.injection"
        else -affected if action == "royal.burn" else 0
    )
    return {
        "action": action,
        "source": owner,
        "destination": p.get("destination"),
        "parameters": p,
        "supply_delta": str(delta),
        "supply_delta_unit": "mg",
        "mint_plan": plan,
        "validation_errors": ["Minério insuficiente"] if remaining else [],
        "owner": owner,
        "selected_lot": lots.payload(selected) if selected else None,
        "lots": [lots.payload(r) for r in source],
        "coins": {a: lunar.balances(db, a) for a in sorted(accounts)},
        "debt": {
            str(d.character_id): str(d.weight_mg)
            for d in db.scalars(select(m.LunarDebt))
        },
        "supply": {
            "genesis": str(supply.legacy_backing_mg),
            "discovery": str(supply.discovered_mg),
            "injection": str(supply.admin_injected_mg),
            "destroyed": str(supply.destroyed_mg),
        },
        "impact": {
            "affected_mass_mg": str(affected),
            "mint_mass_mg": str(mintmass),
            "available_mineral_mg": str(
                sum(r.weight_mg for r in source if ids is None or r.id in ids)
            ),
            "grams": p.get("grams", 0),
            "coins": p.get("coins", {}),
            "extraordinary": action in ("royal.burn", "royal.injection"),
        },
    }


def apply(db, actor, op):
    owner = finance.normalize(op.target)
    p = op.params
    key = f"royal:{op.id}"
    who = f"admin:{actor.id}"
    if op.action == "royal.mint":
        lots.mint(db, p["coins"], key, who, op.reason, ids=p.get("lot_ids"))
    elif op.action == "royal.transfer_lot":
        lots.transfer(
            db,
            p["lot_id"],
            owner,
            finance.normalize(p["destination"]),
            key,
            who,
            op.reason,
        )
    elif op.action == "royal.transfer_coins":
        finance.move(
            db,
            owner,
            finance.normalize(p["destination"]),
            p["amount_units"],
            key,
            actor=who,
            reason=op.reason,
        )
    elif op.action == "royal.burn":
        lots.burn(
            db,
            owner,
            p.get("grams", 0),
            p.get("coins", {}),
            key,
            who,
            op.reason,
            p.get("lot_ids"),
        )
    elif op.action == "royal.injection":
        grams = p.get("grams", 0)
        posts = [(owner, a, q) for a, q in p.get("coins", {}).items()]
        if grams:
            posts.append((owner, lots.ASSET, grams * 1000))
        target = db.get(m.LunarAccount, owner)
        if grams and target.kind == "player":
            resources.capacity(db, db.get(m.Character, target.character_id))
        e = lunar.post(
            db,
            key,
            "ADMIN_INJECTION",
            who,
            op.reason,
            posts,
            source="admin_injection",
            context={
                "parameters": [owner, p],
                "extraordinary": True,
                "operation_id": op.id,
            },
        )
        if grams:
            lots.create(
                db,
                owner,
                grams * 1000,
                e,
                details={"origin": "ADMIN_INJECTION", "administrator": actor.id},
            )
    lots.check(db)


def overview(db):
    a = finance.metrics(db) if finance.active(db) else lunar.audit(db)
    if a.get("initialized") is False:
        return {
            "audit": a,
            "accounts": [],
            "entries": [],
            "operations": [],
            "configuration": {k: runtime_setting(db, k) for k in resources.CONFIG},
        }
    rows = lots.held(db)
    heldmass = {}
    for r in rows:
        heldmass[r.owner_account_id] = heldmass.get(r.owner_account_id, 0) + r.weight_mg
    money = {}
    for h in db.scalars(
        select(m.LunarHolding).where(m.LunarHolding.asset_code.like("coin_%"))
    ):
        money.setdefault(h.account_id, {})[h.asset_code] = h.quantity
    debt = {r.character_id: r.weight_mg for r in db.scalars(select(m.LunarDebt))}
    item_counts = dict(
        db.execute(
            select(m.Item.owner, func.count())
            .where(m.Item.location == "inventory")
            .group_by(m.Item.owner)
        ).all()
    )
    stock_counts = dict(
        db.execute(
            select(m.NPCStock.account_id, func.count()).group_by(m.NPCStock.account_id)
        ).all()
    )
    accounts = [
        {
            "id": r.id,
            "kind": r.kind,
            "character_id": r.character_id,
            "coins": {
                k: str(money.get(r.id, {}).get(k, 0))
                for k in ["coin_small", "coin_medium", "coin_large"]
            },
            "coin_mg": str(
                sum(
                    money.get(r.id, {}).get(k, 0) * w
                    for k, w in [
                        ("coin_small", 1000),
                        ("coin_medium", 5000),
                        ("coin_large", 10000),
                    ]
                )
            ),
            "mineral_mg": str(heldmass.get(r.id, 0)),
            "debt_mg": str(debt.get(r.character_id, 0)),
            "inventory_items": (
                item_counts.get(r.character_id, 0)
                if r.character_id
                else stock_counts.get(r.id, 0)
            ),
            "legacy": r.id == "central_bank",
        }
        for r in db.scalars(select(m.LunarAccount).order_by(m.LunarAccount.id))
    ]
    metrics = resources.metrics(db)
    return {
        "audit": {
            **a,
            **metrics,
            "potential_world_mg": metrics["lunar_resource_uncollected_mg"],
        },
        "accounts": accounts,
        "configuration": {k: runtime_setting(db, k) for k in sorted(resources.CONFIG)},
        "entries": [
            {
                "id": e.id,
                "key": e.key,
                "kind": e.kind,
                "actor": e.actor,
                "reason": e.reason,
                "created_at": e.created_at.isoformat(),
                "postings": e.postings,
                "context": e.context,
            }
            for e in db.scalars(
                select(m.LunarEntry).order_by(m.LunarEntry.id.desc()).limit(200)
            )
        ],
        "operations": [
            {
                "id": o.id,
                "actor": o.actor_id,
                "action": o.action,
                "reason": o.reason,
                "status": o.status,
                "before": o.before,
                "after": o.after,
            }
            for o in db.scalars(
                select(m.AdminOperation)
                .order_by(m.AdminOperation.created_at.desc())
                .limit(100)
            )
        ],
    }
