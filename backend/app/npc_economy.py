"""Finite custody stock. No implicit products/prices, restock or starting NPC cash."""

from sqlalchemy import select
from . import models as m, finance, lunar
from .game import fail, idle
from .rooms import current
from .world import distance


def at_service(db, c):
    idle(db, c)
    r = current(db, c)
    if (
        r.id not in ("guild", "auction_hall", "recovery_hall")
        or not r.data.get("npc")
        or distance((c.x, c.y), r.data["npc"]) > 1
    ):
        fail("Aproxime-se de um serviço da Guilda")


def quote(item, price, account):
    return lunar.fingerprint(
        [
            item.id,
            item.definition,
            item.owner,
            item.location,
            item.quantity,
            str(price),
            account,
        ]
    )


def sell_to_player(db, c, item_id, key, expected_quote=None):
    lunar.mutex(db)
    at_service(db, c)
    if not finance.active(db):
        fail("Cutover necessário")
    old = db.scalar(select(m.WorldEvent).where(m.WorldEvent.key == "npc-sale:" + key))
    if old:
        if old.payload != {"character": c.id, "item": item_id}:
            fail("Chave de compra já usada")
        return {"replayed": True}
    stock = db.get(m.NPCStock, item_id)
    item = db.get(m.Item, item_id)
    if not stock or not item or item.location != "npc" or item.owner is not None:
        fail("Estoque indisponível")
    if expected_quote is not None and expected_quote != quote(
        item, stock.sale_weight_mg, stock.account_id
    ):
        fail("Preço ou estoque mudou; revise a prévia")
    if finance.debt_mg(db, c):
        fail("Quite a dívida antes de comprar")
    from .inventory import ensure_collection_capacity
    from .config import settings

    ensure_collection_capacity(
        db,
        c,
        db.get(m.ItemDefinition, item.definition),
        item.quantity,
        settings.collection_slots,
    )
    if stock.sale_weight_mg % 1000:
        fail("Preço não representável")
    finance.move(
        db,
        f"player:{c.id}",
        stock.account_id,
        stock.sale_weight_mg // 1000,
        key,
        amortize=False,
    )
    # Context is immutable: item receipt is separate from the money receipt.
    db.add(
        m.WorldEvent(
            key="npc-sale:" + key,
            kind="NPC_SALE",
            payload={"character": c.id, "item": item_id},
        )
    )
    item.owner = c.id
    item.location = "inventory"
    db.delete(stock)
    return {"item_id": item.id}


def buy_from_player(db, c, item_id, npc, price_mg, key):
    # Internal service only: quote is server-provided, never a client price.
    lunar.mutex(db)
    at_service(db, c)
    if not finance.active(db):
        fail("Cutover necessário")
    old = db.scalar(select(m.WorldEvent).where(m.WorldEvent.key == "npc-buy:" + key))
    if old:
        if old.payload != {
            "character": c.id,
            "item": item_id,
            "npc": npc,
            "price_mg": str(price_mg),
        }:
            fail("Chave de venda já usada")
        return {"replayed": True}
    item = db.get(m.Item, item_id)
    if not item or item.owner != c.id or item.location != "inventory":
        fail("Item indisponível")
    d = db.get(m.ItemDefinition, item.definition)
    if d.id == "sword" or not d.death_transferable or item.equipped:
        fail("Item protegido")
    lunar.integer(price_mg, True)
    if price_mg % 1000:
        fail("Preço não representável")
    finance.ensure(db, npc)
    finance.move(db, npc, f"player:{c.id}", price_mg // 1000, key)
    db.add(
        m.WorldEvent(
            key="npc-buy:" + key,
            kind="NPC_PURCHASE",
            payload={
                "character": c.id,
                "item": item_id,
                "npc": npc,
                "price_mg": str(price_mg),
            },
        )
    )
    item.owner = None
    item.location = "npc"
    item.equipped = False
    db.add(m.NPCStock(item_id=item.id, account_id=npc, sale_weight_mg=price_mg))
    return {"item_id": item.id}
