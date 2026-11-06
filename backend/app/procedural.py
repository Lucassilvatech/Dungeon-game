"""Universal, seed-local generator. Distances follow directed room exits, never pixels."""

from collections import deque
from math import floor
import random
from sqlalchemy import select
from .models import Room, RoomConnection, MonsterDefinition
from .config import settings

FLOOR_LEVEL_CAP = {1: 5}
# Conservative ranges anchored to current first-floor profiles, not illustrative 3..15 attack.
SPECIES = {
    "slime": {
        "floors": {
            "1": {
                "level": [1, 5],
                "hp": [24, 36],
                "attack": [6, 8],
                "defense": [2, 3],
                "xp": [30, 42],
            }
        },
        "regions": ["PROCEDURAL"],
        "miniboss": True,
    },
    "goblin": {
        "floors": {
            "1": {
                "level": [2, 5],
                "hp": [30, 44],
                "attack": [7, 9],
                "defense": [3, 4],
                "xp": [40, 54],
            }
        },
        "regions": ["PROCEDURAL"],
        "miniboss": True,
    },
}
CATEGORIES = {
    "common": ("Comum", "#eeeeee", "●"),
    "rare": ("Raro", "#5599ff", "◆"),
    "miniboss": ("Miniboss", "#bb66ee", "▲"),
    "boss": ("Boss", "#ff5555", "☠"),
    "unique": ("Secreto/único", "#ffd166", "★"),
}


def chance(streak):
    return min(0.10, 0.01 + max(0, streak) * settings.adventure_boss_increment)


def proximity(db, room):
    eligible = {
        r.id
        for r in db.scalars(
            select(Room).where(
                Room.floor_id == room.floor_id,
                (Room.owner_id == None) | (Room.owner_id == room.owner_id),
            )
        )
    }
    reverse = {}
    for edge in db.scalars(select(RoomConnection)):
        if edge.source in eligible and edge.target in eligible:
            reverse.setdefault(edge.target, []).append(edge.source)
    distances = {"boss": 0}
    queue = deque(["boss"])
    while queue:
        target = queue.popleft()
        for source in reverse.get(target, []):
            if source not in distances:
                distances[source] = distances[target] + 1
                queue.append(source)
    if room.id not in distances:
        return None
    maximum = max(distances.values(), default=0)
    return 1.0 if maximum == 0 else max(0.0, min(1.0, 1 - distances[room.id] / maximum))


def generate(config, floor_id, p, seed, category="common", k=None, level_weight=None):
    if p is None:
        raise ValueError("Room has no valid path to the boss")
    limits = config["floors"][str(floor_id)]
    rng = random.Random(str(seed))
    low, high = limits["level"]
    high = min(high, FLOOR_LEVEL_CAP[floor_id])
    if low > high or low < 1 or not 0 <= p <= 1:
        raise ValueError("Invalid species/floor limits")
    k = settings.procedural_proximity_k if k is None else k
    # Preserve all old bins except a small upper tail of the transformed draw.
    # The tail makes the configured maximum possible without widening every bin.
    u = rng.random() ** (1 / (1 + k * p))
    level = high if high > low and u >= 0.995 else low + floor((high - low) * u)
    level = max(low, min(high, level))
    t = (level - low) / max(1, high - low)
    weight = settings.procedural_level_weight if level_weight is None else level_weight
    result = {"level": level}
    for attribute in ("hp", "attack", "defense", "xp"):
        minimum, maximum = limits[attribute]
        if minimum < 0 or maximum < minimum:
            raise ValueError("Invalid attribute bounds")
        q = max(
            0.0, min(1.0, weight * t + (1 - weight) * rng.random() ** (1 / (1 + 2 * p)))
        )
        result[attribute] = max(
            minimum, min(maximum, round(minimum + (maximum - minimum) * q))
        )
    if category == "miniboss":
        for attr, multiplier in config.get(
            "miniboss_multipliers",
            {"hp": 1.35, "attack": 1.15, "defense": 1.1, "xp": 1.5},
        ).items():
            result[attr] = round(result[attr] * multiplier)
    return result


def configure_room(db, c, room, expedition):
    """One roll at creation; persist result and seed before the first enemy materializes."""
    import secrets

    expedition.boss_chance = round(chance(c.adventure_streak) * 10000)
    expedition.special_boss = secrets.randbelow(10000) < expedition.boss_chance
    expedition.boss_rolled = True
    p = proximity(db, room)
    if p is None:
        raise ValueError("Procedural room must connect to floor boss")
    rng = random.Random(room.seed)
    spawns = {key: dict(value) for key, value in room.data["spawns"].items()}
    mini_count = 0
    from .world_events import rare_multiplier

    rare_chance = min(0.25, 0.05 * rare_multiplier(db, room))
    for index, (key, spawn) in enumerate(sorted(spawns.items())):
        definition = db.get(MonsterDefinition, spawn["species"])
        config = (definition.procedural_config if definition else None) or SPECIES.get(
            spawn["species"]
        )
        if not config or room.kind not in config.get("regions", [room.kind]):
            continue
        category = "common"
        if mini_count < 1 and config.get("miniboss") and rng.random() < 0.02 + 0.06 * p:
            category = "miniboss"
            mini_count += 1
        elif rng.random() < rare_chance:
            category = "rare"
        stats = generate(config, room.floor_id, p, f"{room.seed}:{key}", category)
        spawn.update(stats=stats, category=category)
    if expedition.special_boss and spawns:
        last = sorted(spawns)[-1]
        # Local procedural guardian, independent from unique floor/secret bosses and their gates.
        spawns[last].update(
            species="champion",
            category="boss",
            stats={"hp": 60, "attack": 9, "defense": 3, "level": 5, "xp": 100},
        )
    room.data = {
        **room.data,
        "spawns": spawns,
        "procedural_version": 2,
        "boss_proximity": p,
    }
