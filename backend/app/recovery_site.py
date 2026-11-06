"""Recovery service lives at the village's secluded southwest tent, not in the Guild."""

from sqlalchemy import select
from . import models as m
from .world import distance

ROOM = "city1"
NPC = [5, 30]
NAME = "Figura encapuzada"
TENT = {"kind": "recovery_tent", "x": 3, "y": 27, "width": 5, "height": 5}


def patch(data):
    return {
        **data,
        "npc": NPC,
        "npc_name": NAME,
        "npc_role": "recovery",
        "recovery_site_version": 1,
        "decorations": [
            *[
                d
                for d in data.get("decorations", [])
                if d.get("kind") != "recovery_tent"
            ],
            TENT,
        ],
    }


def require_near(db, c):
    from .game import fail

    room = db.get(m.Room, c.room_id)
    if (
        c.room_id != ROOM
        or room.data.get("npc_role") != "recovery"
        or not room.data.get("npc")
        or distance((c.x, c.y), room.data["npc"]) > 1
    ):
        fail("Aproxime-se da figura encapuzada na barraca ao sudoeste da vila")


def seed(db):
    city = db.get(m.Room, ROOM)
    if city and city.data.get("recovery_site_version") != 1:
        if city.data.get("npc") and city.data.get("npc_role") != "recovery":
            raise RuntimeError(
                "NPC primário personalizado na cidade; revise a instalação da barraca"
            )
        city.data = patch(city.data)
