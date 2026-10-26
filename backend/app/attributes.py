"""Manual allocation: preserve legacy stats, grant points only on future levels."""

from .rooms import event

MIN_LEVEL = 1
DEBT_LEVEL_PENALTY = 10
MAX_ATTRIBUTE = 2147483647


def gain_levels(db, c):
    gained = 0
    while c.xp >= c.level * 50:
        c.xp -= c.level * 50
        c.level += 1
        gained += 1
        if c.attribute_point_debt:
            c.attribute_point_debt -= 1
        else:
            c.unspent_attribute_points += 1
    if gained:
        c.hp = 30 + (c.level - 1) * 5
        event(
            db,
            "ATTRIBUTE_POINT_GAINED",
            c,
            levels_gained=gained,
            available=c.unspent_attribute_points,
            debt=c.attribute_point_debt,
        )
    return gained


def penalize_levels(c):
    before = c.level
    c.level = max(MIN_LEVEL, c.level - DEBT_LEVEL_PENALTY)
    lost = before - c.level
    consumed = min(lost, c.unspent_attribute_points)
    c.unspent_attribute_points -= consumed
    c.attribute_point_debt += lost - consumed
    return dict(
        level_before=before,
        level_after=c.level,
        levels_lost=lost,
        unspent_consumed=consumed,
        attribute_debt_added=lost - consumed,
    )


def allocate(db, c, strength, defense, request_id):
    from .game import fail
    from sqlalchemy import select
    from .models import WorldEvent

    key = f"attributes:{c.id}:{request_id}"
    previous = db.scalar(select(WorldEvent).where(WorldEvent.key == key))
    if previous:
        if (
            previous.payload["strength"] != strength
            or previous.payload["defense"] != defense
        ):
            fail("Chave de distribuição já usada com outros valores")
        return {"message": "Distribuição já confirmada.", "replayed": True}
    if min(strength, defense) < 0 or strength + defense <= 0:
        fail("Escolha uma distribuição positiva", 422)
    if strength + defense > c.unspent_attribute_points:
        fail("Pontos de atributo insuficientes")
    if c.strength + strength > MAX_ATTRIBUTE or c.defense + defense > MAX_ATTRIBUTE:
        fail("Atributo fora da capacidade de armazenamento", 422)
    c.strength += strength
    c.defense += defense
    c.unspent_attribute_points -= strength + defense
    event(
        db,
        "ATTRIBUTE_POINT_SPENT",
        c,
        key=key,
        strength=strength,
        defense=defense,
        remaining=c.unspent_attribute_points,
    )
    return {"message": "Distribuição de atributos confirmada."}


def effective(db, c):
    """One read-only projection shared by status and combat; legacy power is strength."""
    from sqlalchemy import select
    from .models import Item, ItemDefinition
    bonuses = {"strength": 0, "defense": 0}
    for definition in db.scalars(select(ItemDefinition).join(Item, Item.definition == ItemDefinition.id).where(Item.owner == c.id, Item.location == "inventory", Item.equipped == True)):
        bonuses["strength"] += definition.power if definition.kind == "weapon" else 0
    return {key: {"base": getattr(c, key), "equipment": bonuses[key], "temporary": 0, "effective": getattr(c, key) + bonuses[key]} for key in bonuses}
