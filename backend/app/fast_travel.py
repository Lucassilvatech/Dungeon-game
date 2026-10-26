"""Fast travel uses visited permanent destinations, never instance discovery alone."""

from sqlalchemy import select
from .models import Room, RoomState
from .rooms import enter, event

ELIGIBLE = {
    "city1",
    "guild",
    "auction_hall",
    "recovery_hall",
    "training",
    "common_a",
    "common_b",
    "combat",
    "boss",
}


def destinations(db, c):
    return [
        dict(id=r.id, name=r.name, danger_tier=r.danger_tier)
        for r, s in db.execute(
            select(Room, RoomState)
            .join(RoomState, RoomState.room_id == Room.id)
            .where(
                RoomState.character_id == c.id,
                Room.id.in_(ELIGIBLE),
                Room.floor_id == 1,
                Room.owner_id == None,
            )
        )
        if s.visits > 0 or r.id == c.room_id or r.id == "city1"
    ]


def travel(db, c, target):
    from .game import idle, fail
    from .expeditions import guard_departure

    guard_departure(db, c)
    idle(db, c)
    if target not in {d["id"] for d in destinations(db, c)}:
        fail("Destino permanente ainda não visitado ou inelegível", 403)
    enter(db, c, db.get(Room, target))
    event(db, "FAST_TRAVEL", c, destination=target)
