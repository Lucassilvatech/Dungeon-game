"""Personal death recovery. One lost unit counts as one item, including stack materials."""

import secrets
from sqlalchemy import select
from .models import Item, ItemDefinition, RecoveryItem, Treasury
from .clock import utc_now
from .rooms import event
from .economy import ledger


def eligible(db, c):
    return db.execute(
        select(Item, ItemDefinition)
        .join(ItemDefinition, Item.definition == ItemDefinition.id)
        .where(
            Item.owner == c.id,
            Item.location == "inventory",
            ItemDefinition.death_transferable == True,
            ItemDefinition.id != "sword",
            ~ItemDefinition.kind.in_(["system", "structural", "quest"]),
            (ItemDefinition.base_value != None)
            | (
                (ItemDefinition.unique_item == False)
                & (ItemDefinition.rarity.in_(["common", "uncommon"]))
            ),
        )
        .order_by(Item.id)
        .with_for_update(of=Item)
    ).all()


def detach_units(db, item, quantity):
    """Full equipment retains ID; partial stacks create exactly one custody stack."""
    if quantity < item.quantity:
        item.quantity -= quantity
        copy = Item(
            owner=item.owner,
            definition=item.definition,
            quantity=quantity,
            equipped=False,
        )
        db.add(copy)
        db.flush()
        item = copy
    item.owner = None
    item.equipped = False
    return item


def loss_count(maximum):
    return secrets.randbelow(maximum + 1)


def lose(db, c, death):
    rows = eligible(db, c)
    total = sum(i.quantity for i, _ in rows)
    count = loss_count(min(5, total))
    # Sample at most five indexes without expanding a potentially large inventory.
    indexes = set(__import__("random").SystemRandom().sample(range(total), count))
    offset = 0
    lost = []
    for item, definition in rows:
        units = sum(offset <= index < offset + item.quantity for index in indexes)
        offset += item.quantity
        if not units:
            continue
        item = detach_units(db, item, units)
        valuable = definition.unique_item or definition.rarity in (
            "rare",
            "epic",
            "legendary",
            "unique",
        )
        item.location = "recovery" if valuable else "destroyed"
        recovery = None
        if valuable:
            if definition.base_value is None or definition.base_value < 0:
                # Unknown-valued valuables are protected from selection, handled by eligible filter below.
                raise ValueError("Recovery requires trustworthy base value")
            recovery = RecoveryItem(
                character_id=c.id,
                item_id=item.id,
                death_event_id=death.id,
                price=definition.base_value * units * 2,
            )
            db.add(recovery)
            db.flush()
        lost.append(
            {
                "item_id": item.id,
                "name": definition.name,
                "quantity": units,
                "destination": item.location,
                "recovery_id": recovery.id if recovery else None,
                "recovery_price": str(recovery.price) if recovery else None,
            }
        )
    event(
        db,
        "DEATH_ITEMS_LOST",
        c,
        key=f"death-items:{death.id}",
        items=lost,
        units=count,
    )
    from .observability import add

    add(
        db,
        c,
        items_lost_units=count,
        items_destroyed_units=sum(
            i["quantity"] for i in lost if i["destination"] == "destroyed"
        ),
        items_recovery_units=sum(
            i["quantity"] for i in lost if i["destination"] == "recovery"
        ),
    )
    return lost


def listing(db, c):
    result = []
    for r in db.scalars(
        select(RecoveryItem)
        .where(RecoveryItem.character_id == c.id)
        .order_by(RecoveryItem.id.desc())
    ):
        item = db.get(Item, r.item_id)
        d = db.get(ItemDefinition, item.definition)
        result.append(
            {
                "id": r.id,
                "name": d.name,
                "item_id": item.id,
                "quantity": item.quantity,
                "base_value": str(r.price // 2),
                "price": str(r.price),
                "markup_percent": 100,
                "recovered": r.recovered_at is not None,
            }
        )
    return result


def recover(db, c, id, request_id):
    from .game import fail, idle
    from .world import distance
    from .rooms import current

    idle(db, c)
    r = db.scalar(
        select(RecoveryItem)
        .where(RecoveryItem.id == id, RecoveryItem.character_id == c.id)
        .with_for_update()
    )
    if not r:
        fail("Item de recuperação inexistente", 404)
    if r.recovered_at:
        if r.request_id != request_id:
            fail("Item já recuperado")
        return {"message": "Recuperação já confirmada.", "replayed": True}
    room = current(db, c)
    if room.id != "recovery_hall" or distance((c.x, c.y), room.data["npc"]) > 1:
        fail("Aproxime-se do Guardião de Recuperação na Guilda")
    if c.coins < r.price or c.coins < 0:
        fail("Saldo insuficiente para recuperar o item")
    item = db.get(Item, r.item_id)
    if item.location != "recovery" or item.owner is not None:
        fail("Custódia de recuperação inconsistente")
    treasury = db.scalar(select(Treasury).where(Treasury.id == 1).with_for_update())
    c.coins -= r.price
    treasury.balance += r.price
    ledger(db, f"recovery:{r.id}", f"character:{c.id}", "treasury", r.price)
    item.owner = c.id
    item.location = "inventory"
    item.equipped = False
    from .observability import add

    add(db, c, recovery_spent=r.price, recovered_items=item.quantity)
    r.recovered_at = utc_now()
    r.request_id = request_id
    event(
        db,
        "PERSONAL_ITEM_RECOVERED",
        c,
        key=f"recovery:{r.id}",
        item_id=item.id,
        price=str(r.price),
        request_id=request_id,
    )
    return {"message": "Item recuperado por 200% do valor-base.", "replayed": False}
