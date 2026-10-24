"""Stack mutations run under the owner's character lock, never from a client quantity."""

from sqlalchemy import select
from .models import Item, ItemDefinition, WorldEvent
from .rooms import event


def add_item(db, c, definition_id, quantity, reference):
    if db.scalar(select(WorldEvent).where(WorldEvent.key == f"item:{reference}")):
        return
    if quantity <= 0:
        raise ValueError("Item quantity must be positive")
    definition = db.get(ItemDefinition, definition_id)
    if not definition:
        raise ValueError("Unknown item definition")
    remaining = quantity
    if definition.stackable:
        stacks = db.scalars(
            select(Item)
            .where(
                Item.owner == c.id,
                Item.definition == definition_id,
                Item.location == "inventory",
                Item.equipped == False,
            )
            .order_by(Item.id)
            .with_for_update()
        ).all()
        for stack in stacks:
            moved = min(remaining, max(0, definition.max_stack_size - stack.quantity))
            stack.quantity += moved
            remaining -= moved
            if remaining == 0:
                break
    while remaining:
        count = min(remaining, definition.max_stack_size if definition.stackable else 1)
        db.add(Item(owner=c.id, definition=definition_id, quantity=count))
        remaining -= count
    event(
        db,
        "ITEM_ADDED",
        c,
        key=f"item:{reference}",
        definition=definition_id,
        quantity=quantity,
    )
    db.flush()
