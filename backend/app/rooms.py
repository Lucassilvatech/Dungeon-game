"""Persistent room graph, deterministic templates and discovery projections."""

from enum import StrEnum
import random
import secrets
from sqlalchemy import select
from .models import Floor, Room, RoomConnection, RoomState, WorldEvent
from .world import map_data


class RoomType(StrEnum):
    CITY = "CITY"
    COMMON = "COMMON"
    COMBAT = "COMBAT"
    BOSS = "BOSS"
    PROCEDURAL = "PROCEDURAL"
    SECRET_DUNGEON = "SECRET_DUNGEON"
    BUILDING_INTERIOR = "BUILDING_INTERIOR"
    GUILD = "GUILD"
    TRAINING = "TRAINING"
    SPECIAL = "SPECIAL"


class DomainEvent(StrEnum):
    ROOM_DISCOVERED = "ROOM_DISCOVERED"
    ROOM_ENTERED = "ROOM_ENTERED"
    ADVENTURE_STARTED = "ADVENTURE_STARTED"
    SECRET_DUNGEON_DISCOVERED = "SECRET_DUNGEON_DISCOVERED"
    SECRET_DUNGEON_COMPLETED = "SECRET_DUNGEON_COMPLETED"
    FLOOR_BOSS_DISCOVERED = "FLOOR_BOSS_DISCOVERED"
    FLOOR_BOSS_DEFEATED = "FLOOR_BOSS_DEFEATED"
    FLOOR_UNLOCKED = "FLOOR_UNLOCKED"
    RAID_CREATED = "RAID_CREATED"
    RAID_JOINED = "RAID_JOINED"
    COMBAT_STARTED = "COMBAT_STARTED"
    COMBAT_FINISHED = "COMBAT_FINISHED"


class RoomTemplate(StrEnum):
    GROVE = "grove"
    RUINS = "ruins"
    POND = "pond"


ENEMY_SPAWN_TABLE = {
    "grove": {"slime": (5, 6)},
    "ruins": {"slime": (10, 6)},
    "pond": {"slime": (6, 8)},
}
RESOURCE_SPAWN_TABLE = {"grove": [[4, 8]], "ruins": [[11, 4]], "pond": [[3, 7]]}
ENVIRONMENT_THEMES = {"grove": "forest", "ruins": "ruins", "pond": "water"}


def event(db, kind, c, room_id=None, key=None, **payload):
    key = key or secrets.token_hex(16)
    if db.scalar(select(WorldEvent).where(WorldEvent.key == key)):
        return
    db.add(
        WorldEvent(
            key=key,
            kind=str(kind),
            payload={"character": c.id, "room": room_id or c.room_id, **payload},
            processed=True,
        )
    )


def template(seed):
    from .layouts import generate

    return generate("PROCEDURAL", seed)


def basic(kind,seed=0):
    from .layouts import generate

    return generate(str(kind),seed)


STATIC_ROOMS = [
    ("city1", 1, "Vila do Alvorecer", RoomType.CITY),
    ("guild", 1, "Guilda · Recepção", RoomType.GUILD),
    ("training", 1, "Pátio de treinamento", RoomType.TRAINING),
    ("common_a", 1, "Bosque das lanternas", RoomType.COMMON),
    ("common_b", 1, "Trilha dos vagalumes", RoomType.COMMON),
    ("combat", 1, "Clareira dos ecos", RoomType.COMBAT),
    ("boss", 1, "Santuário do Guardião", RoomType.BOSS),
    ("secret", 1, "Cripta da Maré Antiga", RoomType.SECRET_DUNGEON),
    ("city2", 2, "Mirante das Nuvens", RoomType.CITY),
]
EDGES = [
    ("city1", "guild", (9, 7), (2, 9)),
    ("guild", "training", (35, 10), (2, 9)),
    ("city1", "common_a", (50, 18), (2, 9)),
    ("common_a", "common_b", (32, 13), (2, 9)),
    ("common_b", "combat", (32, 13), (2, 9)),
    ("combat", "boss", (38, 14), (2, 9)),
]


def seed_world(db):
    for i in (1, 2):
        if not db.get(Floor, i):
            db.add(Floor(id=i, name=f"Andar {i}"))
    db.flush()
    for id, floor, name, kind in STATIC_ROOMS:
        if not db.get(Room, id):
            db.add(
                Room(
                    id=id,
                    floor_id=floor,
                    name=name,
                    kind=str(kind),
                    seed=0,
                    data=(
                        basic(kind)
                        if floor == 1
                        else {
                            **map_data(2),
                            "width": 28,
                            "height": 20,
                            "theme": "city",
                            "npc": None,
                            "monsters": {},
                            "portal": [24, 3],
                        }
                    ),
                )
            )
    db.flush()
    for a, b, pa, pb in EDGES:
        for src, dst, p in [(a, b, pa), (b, a, pb)]:
            if not db.scalar(
                select(RoomConnection).where(
                    RoomConnection.source == src, RoomConnection.target == dst
                )
            ):
                db.add(RoomConnection(source=src, target=dst, x=p[0], y=p[1]))


def current(db, c):
    return db.get(Room, c.room_id)


def discover(db, c, room):
    state = db.get(RoomState, (c.id, room.id))
    if not state:
        state = RoomState(character_id=c.id, room_id=room.id, codex={}, visits=0)
        db.add(state)
        kind = (
            DomainEvent.SECRET_DUNGEON_DISCOVERED
            if room.kind == RoomType.SECRET_DUNGEON
            else DomainEvent.ROOM_DISCOVERED
        )
        event(db, kind, c, room.id, key=f"discover:{c.id}:{room.id}")
        if room.kind == RoomType.BOSS:
            event(
                db,
                DomainEvent.FLOOR_BOSS_DISCOVERED,
                c,
                room.id,
                key=f"boss-found:{c.id}",
            )
        db.flush()
    return state


def enter(db, c, room):
    c.room_id = room.id
    c.floor = room.floor_id
    c.x = 2
    c.y = 2
    state = discover(db, c, room)
    state.visits += 1
    state.codex = {
        **state.codex,
        **{
            name: state.codex.get(name, {"name": name, "seen": True, "defeated": False})
            for name in room.data["monsters"]
        },
    }
    event(db, DomainEvent.ROOM_ENTERED, c)


def room_payload(db, c):
    room = current(db, c)
    rs = discover(db, c, room)
    data = dict(room.data)
    labels = {
        "slime": "Slime",
        "boss": "Guardião da Clareira",
        "dummy": "Boneco de treinamento",
        "warden": "Sentinela da Maré",
    }
    data["enemy_names"] = {key: labels.get(key, key) for key in data["monsters"]}
    exits = []
    for e in db.scalars(select(RoomConnection).where(RoomConnection.source == room.id)):
        target = db.get(Room, e.target)
        if target.owner_id not in (None, c.id):
            continue
        known = db.get(RoomState, (c.id, target.id))
        exits.append(
            {
                "id": e.id,
                "x": e.x,
                "y": e.y,
                "name": target.name if known else "Caminho desconhecido",
                "known": bool(known),
            }
        )
    return {
        "id": room.id,
        "name": room.name,
        "kind": room.kind,
        "seed": room.seed,
        "safe": room.kind in (RoomType.CITY, RoomType.GUILD),
        "completed": rs.completed,
        "codex": rs.codex,
        "exits": exits,
    }, data


def atlas(db, c):
    result = []
    for room, state in db.execute(
        select(Room, RoomState)
        .join(RoomState, Room.id == RoomState.room_id)
        .where(RoomState.character_id == c.id, Room.floor_id == c.floor)
    ):
        result.append(
            {
                "id": room.id,
                "name": room.name,
                "kind": room.kind,
                "completed": state.completed,
                "codex": state.codex,
            }
        )
    # No secret room identifiers, content or graph edges before discovery.
    found = sum(r["kind"] == RoomType.SECRET_DUNGEON for r in result)
    total = db.scalar(
        select(__import__("sqlalchemy").func.count())
        .select_from(Room)
        .where(Room.floor_id == c.floor, Room.kind == RoomType.SECRET_DUNGEON)
    )
    known = {r["id"] for r in result}
    edges = []
    for e in db.scalars(select(RoomConnection).where(RoomConnection.source.in_(known))):
        target = db.get(Room, e.target)
        if target.kind == RoomType.SECRET_DUNGEON and e.target not in known:
            continue
        if target.owner_id not in (None, c.id):
            continue
        edges.append(
            {"source": e.source, "target": e.target if e.target in known else None}
        )
    return {
        "rooms": result,
        "connections": edges,
        "secrets": {"found": found, "total": total},
    }
