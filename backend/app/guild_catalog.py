"""Aggregated views and atomic multi-stack checkout over existing physical custody."""

from math import gcd
from sqlalchemy import select
from fastapi import HTTPException
from . import models as m, guild_commerce as commerce, finance, lunar
from .config import settings
from .game import fail

MAX_QUANTITY = 9007199254740991
COINS = {"coin_large": 10000, "coin_medium": 5000, "coin_small": 1000}


def stack_group(d):
    return d.stackable and not d.unique_item and d.kind in ("material", "consumable")


def maximum_exact_quantity(available, price, limit, fixed_fee=0, minimum=1, step=1):
    """Find the largest exact physical payment in <=10 multiplier residue classes."""
    for value in (price, limit, fixed_fee):
        lunar.integer(value)
    for value in (minimum, step):
        lunar.integer(value, True)

    def payable(q):
        if price * q + fixed_fee == 0:
            return True
        try:
            lunar.select_coins(available, COINS, (price * q + fixed_fee) * 1000)
            return True
        except HTTPException:
            return False

    if not price:
        candidate = limit // step * step
        return candidate if candidate >= minimum and payable(candidate) else 0
    funds = sum(available.get(k, 0) * w for k, w in COINS.items()) // 1000
    limit = min(limit, max(0, funds - fixed_fee) // price)
    period = 10 // gcd(price * step, 10)
    first_multiplier = (minimum + step - 1) // step
    maximum_multiplier = limit // step
    best = 0
    for residue in range(period):
        first = first_multiplier + (residue - first_multiplier) % period
        if first > maximum_multiplier or not payable(first * step):
            continue
        low, high = 0, (maximum_multiplier - first) // period
        while low < high:
            mid = (low + high + 1) // 2
            if payable((first + mid * period) * step):
                low = mid
            else:
                high = mid - 1
        best = max(best, (first + low * period) * step)
    return best


def capacity_quantity(db, c, d, inventory=None):
    from .lunar_resources import nugget_slots

    inventory = (
        inventory
        if inventory is not None
        else list(
            db.scalars(
                select(m.Item).where(
                    m.Item.owner == c.id, m.Item.location == "inventory"
                )
            )
        )
    )
    free = sum(
        max(0, d.max_stack_size - i.quantity)
        for i in inventory
        if d.stackable and i.definition == d.id and not i.equipped
    )
    slots = max(0, settings.collection_slots - len(inventory) - nugget_slots(db, c))
    return free + slots * (d.max_stack_size if d.stackable else 1)


def sources(
    db, c, direction, definition_id=None, item_id=None, lock=False, account="guild"
):
    if direction not in ("buy", "sell") or (definition_id is None) == (item_id is None):
        fail("Informe um item ou um material do catálogo", 422)
    query = select(m.Item, m.ItemDefinition).join(
        m.ItemDefinition, m.ItemDefinition.id == m.Item.definition
    )
    if direction == "buy":
        query = query.join(m.NPCStock, m.NPCStock.item_id == m.Item.id).where(
            m.NPCStock.account_id == account,
            m.Item.owner == None,
            m.Item.location == "npc",
        )
    else:
        query = query.where(m.Item.owner == c.id, m.Item.location == "inventory")
    query = (
        query.where(m.Item.definition == definition_id)
        if definition_id is not None
        else query.where(m.Item.id == item_id)
    )
    query = query.order_by(m.Item.id)
    if lock:
        query = query.with_for_update(of=m.Item)
    rows = [(i, d) for i, d in db.execute(query) if commerce.eligible(d, i)]
    if not rows:
        fail(
            "OUT_OF_STOCK: estoque insuficiente"
            if direction == "buy"
            else "OWNERSHIP: você não possui itens vendáveis dessa quantidade"
        )
    d = rows[0][1]
    if definition_id is not None and not stack_group(d):
        fail("Equipamento deve ser selecionado individualmente", 422)
    return d, [i for i, _ in rows]


def quote(
    db, c, quantity, direction, definition_id=None, item_id=None, account="guild"
):
    lunar.integer(quantity, True)
    if quantity > MAX_QUANTITY:
        fail("Quantidade excede o limite seguro", 422)
    if account != "guild" and direction != "buy":
        fail("Este balcão vende somente seu estoque disponível", 422)
    d, rows = sources(db, c, direction, definition_id, item_id, account=account)
    if quantity > sum(i.quantity for i in rows) or (
        not stack_group(d) and quantity != 1
    ):
        fail(
            "OUT_OF_STOCK: estoque insuficiente"
            if direction == "buy"
            else "Você não possui essa quantidade"
        )
    from .market_pricing import price as market_price

    price = market_price(db, account, d.id, quantity, direction)
    total = int(price["total_price_units"])
    remaining = quantity
    selection = []
    for i in rows:
        count = min(remaining, i.quantity)
        if count:
            selection.append(
                {"item_id": i.id, "quantity": count, "before_quantity": i.quantity}
            )
        remaining -= count
        if not remaining:
            break
    offer = {
        "definition_id": definition_id,
        "item_id": item_id,
        "name": d.name,
        "quantity": quantity,
        "operation_type": direction,
        **price,
        "selection": selection,
        "pool_fingerprint": lunar.fingerprint(
            [[i.id, i.quantity, i.owner, i.location, i.equipped] for i in rows]
        ),
    }
    offer["quote_hash"] = lunar.fingerprint(offer)
    offer["payment"] = finance.payment_quote(
        db, f"player:{c.id}" if direction == "buy" else account, total
    )
    return offer


def catalog(db, c, account="guild"):
    inventory = list(
        db.scalars(
            select(m.Item)
            .where(m.Item.owner == c.id, m.Item.location == "inventory")
            .order_by(m.Item.id)
        )
    )
    defs = {d.id: d for d in db.scalars(select(m.ItemDefinition))}
    stock = list(
        db.scalars(
            select(m.Item)
            .join(m.NPCStock, m.NPCStock.item_id == m.Item.id)
            .where(
                m.NPCStock.account_id == account,
                m.Item.location == "npc",
                m.Item.owner == None,
            )
            .order_by(m.Item.id)
        )
    )
    available = lunar.balances(db, f"player:{c.id}")
    debt = finance.debt_mg(db, c)
    result = {"active": finance.active(db), "buy": [], "sell": []}
    for direction, pool in (
        ("buy", stock),
        ("sell", inventory) if account == "guild" else ("sell", []),
    ):
        groups = {}
        for i in pool:
            d = defs[i.definition]
            if not commerce.eligible(d, i):
                continue
            key = "definition:" + d.id if stack_group(d) else "item:" + str(i.id)
            groups.setdefault(key, []).append(i)
        for key, rows in groups.items():
            d = defs[rows[0].definition]
            from .market_pricing import price as market_price
            from . import models as m2

            profile = db.scalar(
                select(m2.NpcProfile).where(m2.NpcProfile.account_id == account)
            )
            policy = (
                db.get(m2.NpcInventoryPolicy, (profile.id, d.id))
                if profile and account != "guild"
                else None
            )
            if account != "guild" and (not policy or not policy.sell_enabled):
                continue
            minimum = policy.minimum_lot_size if policy and direction == "buy" else 1
            p = market_price(db, account, d.id, minimum, direction)
            qty = sum(i.quantity for i in rows)
            price = int(p["unit_price_units"])
            enabled = p["enabled"]
            maximum = min(qty, MAX_QUANTITY)
            if not enabled:
                maximum = 0
            if direction == "buy":
                maximum = (
                    0
                    if debt
                    else maximum_exact_quantity(
                        available,
                        price,
                        min(maximum, capacity_quantity(db, c, d, inventory)),
                        fixed_fee=int(p["fixed_margin_units"]),
                        minimum=minimum,
                        step=p["order_step"],
                    )
                )
            result[direction].append(
                {
                    "key": key,
                    "definition_id": d.id if stack_group(d) else None,
                    "item_id": None if stack_group(d) else rows[0].id,
                    "name": d.name,
                    "quantity": str(qty),
                    "unit_price_units": str(price),
                    "maximum_quantity": str(maximum),
                    "enabled": enabled,
                    "price_revision": p["price_revision"],
                    "market_revision": p["market_revision"],
                    "fixed_margin_units": p["fixed_margin_units"],
                    "minimum_lot_size": p["minimum_lot_size"],
                    "order_step": p["order_step"],
                    "minimum_total_price_units": p["total_price_units"],
                    "stackable": stack_group(d),
                }
            )
        result[direction].sort(key=lambda r: (r["name"].casefold(), r["key"]))
    return result


def trade(
    db,
    c,
    quantity,
    direction,
    quote_hash,
    request_id,
    definition_id=None,
    item_id=None,
    account="guild",
):
    lunar.mutex(db)
    key = (
        f"guild-catalog:{c.id}:{request_id}"
        if account == "guild"
        else f"shop:{account}:{c.id}:{request_id}"
    )
    params = {
        "definition_id": definition_id,
        "item_id": item_id,
        "quantity": quantity,
        "direction": direction,
        "quote": quote_hash,
    }
    if account != "guild":
        params["account"] = account
    old = commerce.replay(db, key, c, params)
    if old:
        return old
    if account == "guild":
        commerce.ensure_active(db, c)
    else:
        from .npc_economy import require_service

        if not finance.active(db):
            fail("Cutover necessário")
        require_service(db, c, account)
    offer = quote(db, c, quantity, direction, definition_id, item_id, account=account)
    if offer["quote_hash"] != quote_hash:
        fail("STALE_QUOTE: o preço ou estoque mudou. Revise a operação novamente")
    if not offer["enabled"]:
        fail(
            "Compra desativada para este item"
            if direction == "sell"
            else "Venda desativada para este item"
        )
    if direction == "buy" and finance.debt_mg(db, c):
        fail("Quite a dívida antes de comprar")
    d, rows = sources(
        db, c, direction, definition_id, item_id, lock=True, account=account
    )
    receive = None
    if direction == "buy":
        from .inventory import ensure_collection_capacity

        ensure_collection_capacity(db, c, d, quantity, settings.collection_slots)
        receive = {
            "definition": d,
            "rows": list(
                db.scalars(
                    select(m.Item)
                    .where(m.Item.owner == c.id, m.Item.location == "inventory")
                    .order_by(m.Item.id)
                    .with_for_update()
                )
            ),
        }
    src, dst = (
        (account, f"player:{c.id}")
        if direction == "sell"
        else (f"player:{c.id}", account)
    )
    finance.ensure(db, account)
    money = finance.move(
        db,
        src,
        dst,
        int(offer["total_price_units"]),
        key + ":coins",
        amortize=direction == "sell",
    )
    byid = {i.id: i for i in rows}
    movements = []
    for chosen in offer["selection"]:
        i = byid[chosen["item_id"]]
        moved = commerce.transfer_item(
            db,
            c,
            i,
            chosen["quantity"],
            direction,
            int(offer["unit_price_units"]) * chosen["quantity"],
            receive=receive,
            account=account,
        )
        db.flush()
        movements.append({**chosen, "moved_item_id": moved.id})
    result = {
        "receipt": money.id,
        "quantity": quantity,
        "total_price_units": offer["total_price_units"],
        "movements": movements,
        "message": "Compra concluída." if direction == "buy" else "Venda concluída.",
    }
    db.add(
        m.WorldEvent(
            key=key,
            kind="GUILD_AGGREGATE_TRADE",
            payload={
                "character": c.id,
                **params,
                **result,
                "price_revision": offer["price_revision"],
            },
        )
    )
    if account != "guild":
        from .npc_economy import record

        record(
            db,
            key + ":sale",
            "NPC_SALE",
            npc=account.split(":", 1)[1],
            actor=f"player:{c.id}",
            definition=d.id,
            quote=offer,
            **result,
        )
    return commerce.save(db, key, c, params, result)
