"""Authoritative individual mineral custody. Ledger mineral_mg quantities are exact mg.
No material LunarHolding is maintained for this accounting asset.
"""

from sqlalchemy import select, func
from . import models as m, lunar, finance
from .clock import utc_now

ASSET = "mineral_mg"
LEGACY = {"nugget_small": 100000, "nugget_medium": 500000, "nugget_large": 1000000}


def held(db, owner=None):
    q = select(m.LunarMineralLot).where(m.LunarMineralLot.state == "HELD")
    if owner is not None:
        q = q.where(m.LunarMineralLot.owner_account_id == owner)
    return db.scalars(q.order_by(m.LunarMineralLot.id)).all()


def mass(db, owner):
    return int(
        db.scalar(
            select(func.coalesce(func.sum(m.LunarMineralLot.weight_mg), 0)).where(
                m.LunarMineralLot.state == "HELD",
                m.LunarMineralLot.owner_account_id == owner,
            )
        )
    )


def payload(r):
    return {
        "id": r.id,
        "lot_id": r.id,
        "weight_mg": str(r.weight_mg),
        "weight_g": r.weight_mg // 1000,
        "owner": r.owner_account_id,
        "state": r.state,
        "origin_occurrence_id": r.origin_occurrence_id,
        "parent_lot_id": r.parent_lot_id,
        "source_entry_id": r.source_entry_id,
        "split_operation_id": r.split_operation_id,
        "mint_operation_id": r.mint_operation_id,
        "burn_operation_id": r.burn_operation_id,
        "created_at": r.created_at.isoformat(),
        "details": r.details,
    }


def get(db, id, owner=None):
    r = db.scalar(
        select(m.LunarMineralLot).where(m.LunarMineralLot.id == id).with_for_update()
    )
    if not r or owner is not None and r.owner_account_id != owner:
        lunar.fail("Pepita inexistente ou de outro proprietário", 404)
    if r.state != "HELD":
        lunar.fail("Pepita já consumida/dividida")
    return r


def replay(db, key, params):
    old = db.scalar(select(m.LunarEntry).where(m.LunarEntry.key == key))
    if old and old.context.get("parameters") != params:
        lunar.fail("Chave já usada com outros parâmetros")
    return old


def create(
    db,
    owner,
    weight,
    entry,
    occurrence=None,
    parent=None,
    details=None,
    state="HELD",
    operation=None,
):
    lunar.integer(weight, True)
    if weight % 1000:
        lunar.fail("Peso deve ser inteiro em gramas", 422)
    r = m.LunarMineralLot(
        owner_account_id=owner,
        weight_mg=weight,
        state=state,
        source_entry_id=parent.source_entry_id if parent else entry.id,
        origin_occurrence_id=parent.origin_occurrence_id if parent else occurrence,
        parent_lot_id=parent.id if parent else None,
        created_at=utc_now(),
        updated_at=utc_now(),
        consumed_at=utc_now() if state != "HELD" else None,
        details={**(details or {}), "initial_owner": owner},
    )
    if operation == "split":
        r.split_operation_id = entry.id
    if operation == "mint":
        r.mint_operation_id = entry.id
    if operation == "burn":
        r.burn_operation_id = entry.id
    db.add(r)
    db.flush()
    return r


def finish(r, state, entry):
    r.state = state
    r.updated_at = utc_now()
    r.consumed_at = utc_now()
    if state == "SPLIT":
        r.split_operation_id = entry.id
    if state == "MINTED":
        r.mint_operation_id = entry.id
    if state == "BURNED":
        r.burn_operation_id = entry.id


def audit(db):
    db.flush()
    errors = []
    allrows = db.scalars(select(m.LunarMineralLot)).all()
    byid = {r.id: r for r in allrows}
    children = {}
    entries = db.scalars(select(m.LunarEntry).order_by(m.LunarEntry.id)).all()
    moves, roots, minted, burned = {}, {}, {}, {}
    for e in entries:
        if e.kind in ("MINERAL_TRANSFER", "MINERAL_SALE"):
            for id in e.context.get("lot_ids", []):
                moves.setdefault(id, []).append(e)
    for r in allrows:
        if r.parent_lot_id is None and r.details.get("origin") != "LEGACY_FIXED_NUGGET":
            roots[r.source_entry_id] = roots.get(r.source_entry_id, 0) + r.weight_mg
        if r.state == "MINTED":
            minted[r.mint_operation_id] = (
                minted.get(r.mint_operation_id, 0) + r.weight_mg
            )
        if r.state == "BURNED":
            burned[r.burn_operation_id] = (
                burned.get(r.burn_operation_id, 0) + r.weight_mg
            )
        expected = r.details.get("initial_owner", r.owner_account_id)
        for e in moves.get(r.id, []):
            negative = [
                p for p in e.postings if p["asset"] == ASSET and p["quantity"] < 0
            ]
            positive = [
                p for p in e.postings if p["asset"] == ASSET and p["quantity"] > 0
            ]
            if (
                len(negative) != 1
                or len(positive) != 1
                or negative[0]["account"] != expected
                or negative[0]["quantity"] != -r.weight_mg
                or positive[0]["quantity"] != r.weight_mg
            ):
                errors.append(f"lot-transfer:{r.id}")
            else:
                expected = positive[0]["account"]
        if expected != r.owner_account_id:
            errors.append(f"lot-owner:{r.id}")
        if r.parent_lot_id:
            children.setdefault(r.parent_lot_id, []).append(r)
        if r.parent_lot_id and (
            r.parent_lot_id not in byid
            or byid[r.parent_lot_id].origin_occurrence_id != r.origin_occurrence_id
        ):
            errors.append(f"lot-parent:{r.id}")
    for e in entries:
        delta = sum(p["quantity"] for p in e.postings if p["asset"] == ASSET)
        if (
            e.kind
            in ("ADMIN_INJECTION", "DISCOVERED_MINERAL", "LUNAR_MINERAL_DISCOVERED")
            and delta > 0
            and roots.get(e.id, 0) != delta
        ):
            errors.append(f"lot-source:{e.id}")
        if (
            e.kind == "MINT"
            and "lot_ids" in e.context
            and minted.get(e.id, 0) != -delta
        ):
            errors.append(f"lot-mint:{e.id}")
        if e.kind == "ADMIN_BURN" and burned.get(e.id, 0) != -delta:
            errors.append(f"lot-burn:{e.id}")
    for r in allrows:
        if (
            r.state == "SPLIT"
            and sum(c.weight_mg for c in children.get(r.id, [])) != r.weight_mg
        ):
            errors.append(f"lot-split:{r.id}")
        if r.state != "SPLIT" and children.get(r.id):
            errors.append(f"lot-unclosed-parent:{r.id}")
    if db.scalar(
        select(m.LunarHolding.account_id)
        .join(m.LunarAsset, m.LunarAsset.code == m.LunarHolding.asset_code)
        .where(m.LunarAsset.kind == "nugget", m.LunarHolding.quantity != 0)
        .limit(1)
    ):
        errors.append("duplicate-mineral-holding")
    return errors


def check(db):
    from .lunar_resources import assert_audit

    db.flush()
    assert_audit(db)


def split(db, owner, id, grams, key, actor=None, reason="Divisão gratuita sem perda"):
    lunar.mutex(db)
    params = [owner, id, grams]
    old = replay(db, key, params)
    if old:
        return old
    if (
        not isinstance(grams, list)
        or not 2 <= len(grams) <= 1000
        or any(type(g) is not int or g < 1 for g in grams)
    ):
        lunar.fail("Informe 2..1000 fragmentos em gramas inteiros positivos", 422)
    r = get(db, id, owner)
    if sum(grams) * 1000 != r.weight_mg:
        lunar.fail("Fragmentos não conservam o peso", 422)
    account = db.get(m.LunarAccount, owner)
    if account.kind == "player":
        from .lunar_resources import capacity

        capacity(db, db.get(m.Character, account.character_id), len(grams) - 1)
    entry = lunar.post(
        db,
        key,
        "MINERAL_SPLIT",
        actor or owner,
        reason,
        [],
        context={"parameters": params, "lot_ids": [id], "weight_mg": str(r.weight_mg)},
    )
    finish(r, "SPLIT", entry)
    for g in grams:
        create(db, owner, g * 1000, entry, parent=r, operation="split")
    check(db)
    return entry


def transfer(db, id, source, destination, key, actor, reason):
    params = [id, source, destination]
    old = replay(db, key, params)
    if old:
        return old
    if source == destination:
        lunar.fail("Contas devem diferir", 422)
    r = get(db, id, source)
    finance.ensure(db, destination)
    dst = db.get(m.LunarAccount, destination)
    if dst.kind == "player":
        from .lunar_resources import capacity

        capacity(db, db.get(m.Character, dst.character_id))
    entry = lunar.post(
        db,
        key,
        "MINERAL_TRANSFER",
        actor,
        reason,
        [(source, ASSET, -r.weight_mg), (destination, ASSET, r.weight_mg)],
        context={"parameters": params, "lot_ids": [id], "weight_mg": str(r.weight_mg)},
    )
    r.owner_account_id = destination
    r.updated_at = utc_now()
    return entry


def consume(db, owner, weight, entry, terminal, ids=None):
    remaining = weight
    for r in held(db, owner):
        if ids is not None and r.id not in ids:
            continue
        if not remaining:
            break
        used = min(remaining, r.weight_mg)
        if used == r.weight_mg:
            finish(r, terminal, entry)
        else:
            finish(r, "SPLIT", entry)
            create(
                db,
                owner,
                used,
                entry,
                parent=r,
                state=terminal,
                operation="mint" if terminal == "MINTED" else "burn",
            )
            create(db, owner, r.weight_mg - used, entry, parent=r, operation="split")
        remaining -= used
    if remaining:
        lunar.fail("Minério insuficiente")


def mint(db, coins, key, actor, reason, owner="treasury", ids=None):
    lunar.mutex(db)
    params = [owner, coins, ids]
    old = replay(db, key, params)
    if old:
        return old
    if owner != "treasury":
        lunar.fail("Somente minério do Tesouro pode ser cunhado")
    total = 0
    posts = []
    if set(coins) - {"coin_small", "coin_medium", "coin_large"}:
        lunar.fail("Denominação inválida", 422)
    for code, q in coins.items():
        lunar.integer(q)
        weight = db.get(m.LunarAsset, code).weight_mg
        total += q * weight
        posts.append((owner, code, q))
    if total <= 0:
        lunar.fail("Cunhagem vazia", 422)
    available = sum(r.weight_mg for r in held(db, owner) if ids is None or r.id in ids)
    if total > available:
        lunar.fail("Minério insuficiente no Tesouro")
    entry = lunar.post(
        db,
        key,
        "MINT",
        actor,
        reason,
        posts + [(owner, ASSET, -total)],
        context={
            "parameters": params,
            "lot_ids": [r.id for r in held(db, owner) if ids is None or r.id in ids],
            "weight_mg": str(total),
        },
    )
    consume(db, owner, total, entry, "MINTED", ids)
    db.get(m.LunarSupply, 1).minted_mg += total
    check(db)
    return entry


def inject(db, owner, grams, key, actor, reason):
    lunar.integer(grams, True)
    if grams > 1000000000:
        lunar.fail("Limite administrativo de peso excedido", 422)
    params = [owner, grams]
    old = replay(db, key, params)
    if old:
        return old
    finance.ensure(db, owner)
    dst = db.get(m.LunarAccount, owner)
    if dst.kind == "player":
        from .lunar_resources import capacity

        capacity(db, db.get(m.Character, dst.character_id))
    entry = lunar.post(
        db,
        key,
        "ADMIN_INJECTION",
        actor,
        reason,
        [(owner, ASSET, grams * 1000)],
        source="admin_injection",
        context={
            "parameters": params,
            "weight_mg": str(grams * 1000),
            "extraordinary": True,
        },
    )
    create(db, owner, grams * 1000, entry, details={"origin": "ADMIN_INJECTION"})
    return entry


def burn(db, owner, grams, coins, key, actor, reason, ids=None):
    lunar.integer(grams)
    params = [owner, grams, coins, ids]
    old = replay(db, key, params)
    if old:
        return old
    posts = []
    if grams:
        posts.append((owner, ASSET, -grams * 1000))
    if set(coins) - {"coin_small", "coin_medium", "coin_large"}:
        lunar.fail("Denominação inválida", 422)
    for a, q in coins.items():
        lunar.integer(q)
        posts.append((owner, a, -q))
    if grams * 1000 > sum(
        r.weight_mg for r in held(db, owner) if ids is None or r.id in ids
    ):
        lunar.fail("Minério insuficiente")
    entry = lunar.post(
        db,
        key,
        "ADMIN_BURN",
        actor,
        reason,
        posts,
        source="destruction",
        context={
            "parameters": params,
            "lot_ids": [r.id for r in held(db, owner) if ids is None or r.id in ids],
        },
    )
    if grams:
        consume(db, owner, grams * 1000, entry, "BURNED", ids)
    return entry


def lineage(db, id):
    root = db.get(m.LunarMineralLot, id)
    if not root:
        lunar.fail("Pepita inexistente", 404)
    seen = set()
    while root.parent_lot_id:
        if root.id in seen:
            lunar.fail("Linhagem cíclica")
        seen.add(root.id)
        root = db.get(m.LunarMineralLot, root.parent_lot_id)
    rows = db.scalars(select(m.LunarMineralLot).order_by(m.LunarMineralLot.id)).all()
    desc = {root.id}
    for _ in range(len(rows)):
        new = {r.id for r in rows if r.parent_lot_id in desc}
        prior = len(desc)
        desc |= new
        if len(desc) == prior:
            break
    entries = [
        {
            "id": e.id,
            "kind": e.kind,
            "actor": e.actor,
            "reason": e.reason,
            "created": e.created_at.isoformat(),
            "context": e.context,
            "postings": e.postings,
        }
        for e in db.scalars(select(m.LunarEntry).order_by(m.LunarEntry.id))
        if set(e.context.get("lot_ids", [])) & desc
        or e.id == root.source_entry_id
        or e.id in root.details.get("legacy_entry_ids", [])
    ]
    occurrence = (
        db.get(m.LunarResourceOccurrence, root.origin_occurrence_id)
        if root.origin_occurrence_id
        else None
    )
    return {
        "root_id": root.id,
        "lots": [payload(r) for r in rows if r.id in desc],
        "history": entries,
        "origin_occurrence": (
            {
                "id": occurrence.id,
                "expedition_id": occurrence.expedition_id,
                "collector": occurrence.collected_by,
            }
            if occurrence
            else None
        ),
    }
