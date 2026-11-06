"""Finite physical Guild commerce. Quotes read state; checkout moves real custody."""

from sqlalchemy import select, func
from . import models as m, lunar, finance, mineral_lots as lots
from .config import runtime_setting, settings
from .clock import utc_now
from .game import fail

MINERAL_KEYS = [
    "lunar_guild_buy_rate_milliunits_per_gram",
    "lunar_guild_sell_rate_milliunits_per_gram",
    "lunar_guild_buy_enabled",
    "lunar_guild_sell_enabled",
    "lunar_guild_allow_zero_price",
]


def mineral_policy(db):
    values = {k: runtime_setting(db, k) for k in MINERAL_KEYS}
    values["revision"] = {
        k: (
            db.get(m.GameSetting, k).value.get("revision", "initial")
            if db.get(m.GameSetting, k)
            else "initial"
        )
        for k in MINERAL_KEYS
    }
    return values


def item_policy(db, definition):
    row = db.get(m.GuildItemPolicy, definition)
    return {
        "definition_id": definition,
        "buy_price_units": str(row.buy_price_units if row else 0),
        "sell_price_units": str(row.sell_price_units if row else 0),
        "buy_enabled": row.buy_enabled if row else False,
        "sell_enabled": row.sell_enabled if row else False,
        "revision": row.revision if row else 0,
        "updated_at": row.updated_at.isoformat() if row else None,
        "updated_by": row.updated_by if row else None,
    }


def validation_warnings(buy, sell, buy_on, sell_on):
    return (["POSSIBLE_ARBITRAGE"] if buy_on and sell_on and sell < buy else []) + (
        ["ZERO_PRICE"] if (buy_on and buy == 0) or (sell_on and sell == 0) else []
    )


def validate_prices(values, mineral=False, acknowledgements=None):
    acknowledgements = acknowledgements or {}
    prefix = "lunar_guild_" if mineral else ""
    bkey, skey = (
        (
            prefix + "buy_rate_milliunits_per_gram",
            prefix + "sell_rate_milliunits_per_gram",
        )
        if mineral
        else ("buy_price_units", "sell_price_units")
    )
    b, s = values[bkey], values[skey]
    for v in (b, s):
        lunar.integer(v)
        if v > 1000000000:
            fail("Preço excede limite administrativo", 422)
    bo, so = values[prefix + "buy_enabled"], values[prefix + "sell_enabled"]
    if type(bo) is not bool or type(so) is not bool:
        fail("Flags comerciais devem ser booleanas", 422)
    warnings = validation_warnings(b, s, bo, so)
    if (
        "POSSIBLE_ARBITRAGE" in warnings
        and acknowledgements.get("acknowledge_arbitrage") is not True
    ):
        fail(
            "POSSIBLE_ARBITRAGE: confirme conscientemente a compra acima da venda", 422
        )
    free = "ZERO_PRICE" in warnings or (
        mineral
        and values.get("lunar_guild_allow_zero_price", False)
        and ((bo and b < 1000) or (so and s < 1000))
    )
    if free and "ZERO_PRICE" not in warnings:
        warnings.append("ZERO_PRICE")
    if free and acknowledgements.get("acknowledge_free") is not True:
        fail(
            "ZERO_PRICE: transferência gratuita exige confirmação administrativa explícita",
            422,
        )
    return warnings


def ensure_active(db, c):
    from .npc_economy import at_service

    if not finance.active(db):
        fail("Comércio Lunar exige cutover ativo")
    at_service(db, c)


def replay(db, key, c, parameters):
    receipt = db.get(m.GuildTradeReceipt, key)
    if receipt:
        if receipt.character_id != c.id or receipt.parameters != parameters:
            fail("REQUEST_CONFLICT: identificador de comércio já utilizado")
        return {**receipt.result, "replayed": True}


def save(db, key, c, parameters, result):
    db.add(
        m.GuildTradeReceipt(
            key=key, character_id=c.id, parameters=parameters, result=result
        )
    )
    db.flush()
    from .lunar_resources import assert_audit

    assert_audit(db)
    return {**result, "replayed": False}


def eligible(d, i):
    return d.id != "sword" and d.death_transferable and not i.equipped


def item_quote(db, c, item_id, quantity, direction):
    if direction not in ("buy", "sell"):
        fail("Operação inválida", 422)
    i = db.get(m.Item, item_id)
    if not i:
        fail("OUT_OF_STOCK: item inexistente", 404)
    d = db.get(m.ItemDefinition, i.definition)
    stock = db.get(m.NPCStock, item_id)
    if direction == "sell":
        if i.owner != c.id or i.location != "inventory":
            fail("OWNERSHIP: item não pertence ao personagem")
    elif (
        not stock
        or stock.account_id != "guild"
        or i.owner is not None
        or i.location != "npc"
    ):
        fail("OUT_OF_STOCK: estoque insuficiente")
    if not eligible(d, i):
        fail("PROTECTED_ITEM: item protegido, equipado ou não transferível")
    quantity = i.quantity if quantity is None else quantity
    lunar.integer(quantity, True)
    if quantity > i.quantity or (not d.stackable and quantity != 1):
        fail("OUT_OF_STOCK: quantidade insuficiente ou equipamento indivisível")
    policy = item_policy(db, d.id)
    side = "buy" if direction == "sell" else "sell"
    unit = int(policy[side + "_price_units"])
    total = unit * quantity
    q = {
        "item_id": i.id,
        "definition": d.id,
        "name": d.name,
        "quantity": quantity,
        "operation_type": direction,
        "guild_operation": side,
        "unit_price_units": str(unit),
        "total_price_units": str(total),
        "price_weight_mg": str(total * 1000),
        "price_revision": policy["revision"],
        "stock_revision": i.quantity,
        "enabled": policy[side + "_enabled"],
        "owner": i.owner,
        "state": i.location,
    }
    from .market_pricing import price as market_price

    q.update(market_price(db, "guild", d.id, quantity, direction))
    total = int(q["total_price_units"])
    q["price_weight_mg"] = str(total * 1000)
    q["quote_hash"] = q["quote"] = lunar.fingerprint(q)
    payer = "guild" if direction == "sell" else f"player:{c.id}"
    q["payment"] = finance.payment_quote(db, payer, total)
    return q


def transfer_item(db, c, i, qty, direction, total, receive=None, account="guild"):
    """Keep equipment identities; partial stack transfer creates an explicit child receipt."""
    stock = db.get(m.NPCStock, i.id)
    if direction == "buy" and receive is None:
        from .inventory import ensure_collection_capacity

        ensure_collection_capacity(
            db,
            c,
            db.get(m.ItemDefinition, i.definition),
            qty,
            settings.collection_slots,
        )
    if qty == i.quantity:
        moved = i
        if stock:
            db.delete(stock)
    else:
        i.quantity -= qty
        moved = m.Item(
            owner=c.id if direction == "sell" else None,
            definition=i.definition,
            quantity=qty,
            location="inventory" if direction == "sell" else "npc",
            equipped=False,
        )
        db.add(moved)
        db.flush()
    if direction == "sell":
        moved.owner, moved.location, moved.equipped = None, "npc", False
        db.add(
            m.NPCStock(
                item_id=moved.id, account_id=account, sale_weight_mg=total * 1000
            )
        )
    else:
        # Fill existing partial stacks without inventing material. The moved row
        # remains as destroyed historical custody if fully merged, preserving FKs.
        d = db.get(m.ItemDefinition, moved.definition)
        remaining = moved.quantity
        if d.stackable:
            targets = (
                receive["rows"]
                if receive is not None
                else list(
                    db.scalars(
                        select(m.Item)
                        .where(m.Item.owner == c.id, m.Item.location == "inventory")
                        .order_by(m.Item.id)
                        .with_for_update()
                    )
                )
            )
            for stack in targets:
                if stack.definition != d.id or stack.equipped or stack.id == moved.id:
                    continue
                n = min(remaining, max(0, d.max_stack_size - stack.quantity))
                stack.quantity += n
                remaining -= n
                if not remaining:
                    break
        if remaining:
            moved.quantity = (
                min(remaining, d.max_stack_size) if d.stackable else remaining
            )
            remaining -= moved.quantity
            moved.owner, moved.location, moved.equipped = c.id, "inventory", False
            if receive is not None:
                receive["rows"].append(moved)
            while remaining:
                count = min(remaining, d.max_stack_size)
                extra = m.Item(
                    owner=c.id,
                    definition=d.id,
                    quantity=count,
                    location="inventory",
                    equipped=False,
                )
                db.add(extra)
                if receive is not None:
                    receive["rows"].append(extra)
                remaining -= count
        else:
            moved.owner, moved.location, moved.equipped = None, "destroyed", False
    return moved


def item_trade(db, c, item_id, quantity, quote_hash, request_id, direction):
    lunar.mutex(db)
    key = f"guild-commerce:{c.id}:{request_id}"
    parameters = {
        "item_id": item_id,
        "quantity": quantity,
        "quote": quote_hash,
        "direction": direction,
    }
    old = replay(db, key, c, parameters)
    if old:
        return old
    ensure_active(db, c)
    offer = item_quote(db, c, item_id, quantity, direction)
    if offer["quote_hash"] != quote_hash:
        fail("STALE_QUOTE: cotação desatualizada; preço ou estoque mudou")
    if not offer["enabled"]:
        fail(
            "GUILD_BUY_DISABLED: compra pela Guilda desativada"
            if direction == "sell"
            else "GUILD_SELL_DISABLED: venda pela Guilda desativada"
        )
    if direction == "buy" and finance.debt_mg(db, c):
        fail("Quite a dívida antes de comprar")
    src, dst = (
        ("guild", f"player:{c.id}")
        if direction == "sell"
        else (f"player:{c.id}", "guild")
    )
    finance.ensure(db, "guild")
    money = finance.move(
        db,
        src,
        dst,
        int(offer["total_price_units"]),
        key + ":coins",
        amortize=direction == "sell",
    )
    item = db.scalar(select(m.Item).where(m.Item.id == item_id).with_for_update())
    before_qty = item.quantity
    moved = transfer_item(
        db, c, item, offer["quantity"], direction, int(offer["total_price_units"])
    )
    result = {
        "item_id": moved.id,
        "source_item_id": item_id,
        "quantity": offer["quantity"],
        "source_quantity_before": before_qty,
        "quote": offer,
        "receipt": money.id,
        "message": "Comércio concluído com moedas físicas e estoque real.",
    }
    db.add(
        m.WorldEvent(
            key=key,
            kind="GUILD_ITEM_TRADE",
            payload={"character": c.id, **parameters, **result},
        )
    )
    return save(db, key, c, parameters, result)


def mineral_quotes(db, c, direction="sell"):
    p = mineral_policy(db)
    side = "buy" if direction == "sell" else "sell"
    rate = p[f"lunar_guild_{side}_rate_milliunits_per_gram"]
    payer = "guild" if direction == "sell" else f"player:{c.id}"
    owner = f"player:{c.id}" if direction == "sell" else "guild"
    result = []
    for r in lots.held(db, owner):
        price = (r.weight_mg // 1000) * rate // 1000
        offer = {
            **lots.payload(r),
            "operation_type": direction,
            "rate": rate,
            "rate_revision": p["revision"],
            "price_units": str(price),
            "enabled": p[f"lunar_guild_{side}_enabled"],
            "guild_balance": str(finance.coin_mg(db, "guild") // 1000),
            "free_allowed": p["lunar_guild_allow_zero_price"],
        }
        offer["quote_hash"] = lunar.fingerprint(
            [
                r.id,
                r.weight_mg,
                r.owner_account_id,
                r.state,
                direction,
                rate,
                p["revision"],
                offer["enabled"],
                offer["free_allowed"],
            ]
        )
        offer["payment"] = finance.payment_quote(db, payer, price)
        result.append(offer)
    return result


def mineral_trade(db, c, lot_id, quote, request_id, direction):
    lunar.mutex(db)
    key = f"lunar-{'sale' if direction=='sell' else 'purchase'}:{c.id}:{request_id}"
    params = [lot_id, quote]
    old = lots.replay(db, key, params)
    if old:
        return {
            "receipt": old.id,
            "replayed": True,
            "message": "Operação já confirmada.",
        }
    ensure_active(db, c)
    offer = next(
        (r for r in mineral_quotes(db, c, direction) if r["lot_id"] == lot_id), None
    )
    if not offer or offer["quote_hash"] != quote:
        fail("STALE_QUOTE: pepita inexistente ou cotação desatualizada")
    if not offer["enabled"]:
        fail(
            "GUILD_BUY_DISABLED: compra pela Guilda desativada"
            if direction == "sell"
            else "GUILD_SELL_DISABLED: venda pela Guilda desativada"
        )
    if int(offer["price_units"]) == 0 and not offer["free_allowed"]:
        fail("ZERO_PRICE: transferência gratuita não autorizada")
    if direction == "buy" and finance.debt_mg(db, c):
        fail("Quite a dívida antes de comprar")
    source, dest = (
        (f"player:{c.id}", "guild")
        if direction == "sell"
        else ("guild", f"player:{c.id}")
    )
    finance.ensure(db, "guild")
    money = finance.move(
        db,
        dest,
        source,
        int(offer["price_units"]),
        key + ":coins",
        amortize=direction == "sell",
    )
    r = lots.get(db, lot_id, source)
    if direction == "buy":
        from .lunar_resources import capacity

        capacity(db, c)
    entry = lunar.post(
        db,
        key,
        "MINERAL_SALE",
        f"player:{c.id}",
        "Comércio de lote inteiro por preço por grama",
        [(source, lots.ASSET, -r.weight_mg), (dest, lots.ASSET, r.weight_mg)],
        context={
            "parameters": params,
            "lot_ids": [lot_id],
            "weight_mg": str(r.weight_mg),
            "direction": direction,
            "rate": offer["rate"],
            "price_units": offer["price_units"],
            "rate_revision": offer["rate_revision"],
            "coin_receipt": money.id,
        },
    )
    r.owner_account_id = dest
    r.updated_at = utc_now()
    result = {
        "receipt": entry.id,
        "lot_id": lot_id,
        "weight_mg": str(r.weight_mg),
        "direction": direction,
        "price_units": offer["price_units"],
        "coin_receipt": money.id,
        "message": "Pepita transferida inteira; pagamento em moedas físicas.",
    }
    import logging

    logging.getLogger("dungeon.lunar_resources").info(
        "resource_sale lot=%s direction=%s weight_mg=%s", lot_id, direction, r.weight_mg
    )
    return save(
        db, key, c, {"lot_id": lot_id, "quote": quote, "direction": direction}, result
    )


def catalog(db, c):
    offers, stock = [], []
    rows = db.scalars(
        select(m.Item)
        .where(m.Item.owner == c.id, m.Item.location == "inventory")
        .order_by(m.Item.id)
        .limit(100)
    ).all()
    stocks = db.scalars(
        select(m.NPCStock)
        .where(m.NPCStock.account_id == "guild")
        .order_by(m.NPCStock.item_id)
        .limit(100)
    ).all()
    for i, direction, target in [(i, "sell", offers) for i in rows] + [
        (db.get(m.Item, r.item_id), "buy", stock) for r in stocks
    ]:
        if i and eligible(db.get(m.ItemDefinition, i.definition), i):
            q = item_quote(db, c, i.id, None, direction)
            target.append({**q, "account": "guild"})
    # Preserve unrelated finite NPC shops; they are never priced from Guild policy.
    from .npc_economy import quote

    for n, i in db.execute(
        select(m.NPCStock, m.Item)
        .join(m.Item, m.Item.id == m.NPCStock.item_id)
        .where(m.NPCStock.account_id != "guild")
        .limit(100)
    ):
        if i.owner is None and i.location == "npc":
            stock.append(
                {
                    "item_id": i.id,
                    "name": db.get(m.ItemDefinition, i.definition).name,
                    "quantity": i.quantity,
                    "account": n.account_id,
                    "price_weight_mg": str(n.sale_weight_mg),
                    "quote": quote(i, n.sale_weight_mg, n.account_id),
                    "enabled": True,
                }
            )
    return {
        "active": finance.active(db),
        "guild_cash": finance.cash(db, "guild"),
        "guild_balance_mg": str(finance.coin_mg(db, "guild")),
        "offers": offers,
        "stock": stock,
    }


def admin_catalog(db):
    stocks = dict(
        db.execute(
            select(m.Item.definition, func.sum(m.Item.quantity))
            .join(m.NPCStock, m.NPCStock.item_id == m.Item.id)
            .where(
                m.NPCStock.account_id == "guild",
                m.Item.location == "npc",
                m.Item.owner == None,
            )
            .group_by(m.Item.definition)
        ).all()
    )
    return [
        {
            **item_policy(db, d.id),
            "name": d.name,
            "stock": str(stocks.get(d.id, 0)),
            "protected": d.id == "sword" or not d.death_transferable,
        }
        for d in db.scalars(select(m.ItemDefinition).order_by(m.ItemDefinition.id))
    ]
