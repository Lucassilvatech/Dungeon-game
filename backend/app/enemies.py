"""Personal encounter instances with durable death, low-frequency authoritative wandering."""

from enum import StrEnum
from datetime import timedelta
import random
from sqlalchemy import select
from .models import EnemyInstance, Battle, RoomConnection
from .clock import utc_now
from .rooms import current, discover, event
from .balance import ENEMIES, NAMES
from .config import settings


class EnemyState(StrEnum):
    ALIVE = "ALIVE"
    IN_COMBAT = "IN_COMBAT"
    DYING = "DYING"
    DEAD = "DEAD"


def instances(db, c, wander=False):
    room = current(db, c)
    rs = discover(db, c, room)
    spawns = room.data.get("spawns") or {
        key: {"species": key, "x": p[0], "y": p[1]}
        for key, p in room.data["monsters"].items()
    }
    existing = db.scalars(
        select(EnemyInstance)
        .where(
            EnemyInstance.character_id == c.id,
            EnemyInstance.room_id == room.id,
            EnemyInstance.generation == rs.generation,
        )
        .order_by(EnemyInstance.id)
    ).all()
    if room.data.get("procedural_version"):
        from .models import Expedition
        record=db.scalar(select(Expedition).where(Expedition.room_id==room.id))
        if record and record.status != "ACTIVE":
            return existing
    known = {e.spawn_key for e in existing}
    for key, spawn in spawns.items():
        if key in known:
            continue
        species = spawn["species"]
        from .danger import scale_stats

        from .models import MonsterDefinition

        definition = db.get(MonsterDefinition, species)
        stats = (
            tuple(
                getattr(definition, k)
                for k in ("hp", "attack", "defense", "level", "xp")
            )
            if definition
            else ENEMIES.get(species, ENEMIES["slime"])
        )
        hp, attack, defense, level, xp = scale_stats(stats, room.danger_tier, room.kind)
        if species == "warden":
            hp = room.data.get("enemy_hp", hp)
            attack = room.data.get("enemy_attack", attack)
            level = room.data.get("enemy_level", level)
        if spawn.get("stats"):
            generated = spawn["stats"]
            hp, attack, defense, level, xp = (generated[k] for k in ("hp", "attack", "defense", "level", "xp"))
        old = db.scalar(
            select(Battle)
            .where(
                Battle.character_id == c.id,
                Battle.room_id == room.id,
                Battle.monster == key,
                Battle.enemy_id == None,
            )
            .order_by(
                (Battle.status == "active").desc(),
                (Battle.status == "won").desc(),
                Battle.id.desc(),
            )
        )
        state = EnemyState.ALIVE
        if rs.generation == 0 and old and old.status in ("won", "active"):
            state = EnemyState.DEAD if old.status == "won" else EnemyState.IN_COMBAT
        e = EnemyInstance(
            character_id=c.id,
            room_id=room.id,
            generation=rs.generation,
            spawn_key=key,
            species=species,
            category=spawn.get("category", "boss" if species == "boss" else "unique" if species == "warden" else "common"),
            hp=(
                0
                if state == EnemyState.DEAD
                else old.hp if state == EnemyState.IN_COMBAT else hp
            ),
            max_hp=hp,
            xp_reward=xp,
            attack=attack,
            defense=defense,
            level=level,
            x=spawn["x"],
            y=spawn["y"],
            home_x=spawn["x"],
            home_y=spawn["y"],
            state=state,
            death_at=utc_now() if state == EnemyState.DEAD else None,
        )
        db.add(e)
        db.flush()
        existing.append(e)
        if old and rs.generation == 0 and old.status in ("won", "active"):
            old.enemy_id = e.id
        event(
            db, "ENEMY_SPAWNED", c, key=f"spawn:{e.id}", enemy_id=e.id, species=species
        )
    if wander:
        blocked = {tuple(p) for p in room.data["walls"]} | {(c.x, c.y)}
        if room.data.get("npc"):
            blocked.add(tuple(room.data["npc"]))
        blocked |= {
            (e.x, e.y)
            for e in db.scalars(
                select(RoomConnection).where(RoomConnection.source == room.id)
            )
        }
        for e in existing:
            if (
                e.state != EnemyState.ALIVE
                or e.species not in ("slime", "goblin")
                or utc_now() - e.moved_at < timedelta(seconds=settings.wander_interval)
            ):
                continue
            positions = {
                (p.x, p.y)
                for p in existing
                if p.id != e.id and p.state != EnemyState.DEAD
            }
            rng = random.Random(
                e.id + int(utc_now().timestamp() // settings.wander_interval)
            )
            dx, dy = rng.choice([(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)])
            p = (e.x + dx, e.y + dy)
            valid = (
                p not in blocked | positions
                and 0 < p[0] < room.data["width"] - 1
                and 0 < p[1] < room.data["height"] - 1
                and abs(p[0] - e.home_x) + abs(p[1] - e.home_y) <= 2
            )
            e.ai_state = "WANDER" if valid and (dx or dy) else "IDLE"
            if e.ai_state == "WANDER":
                e.x, e.y = p
            e.moved_at = utc_now()
    db.flush()
    return existing


def payload(e):
    from .procedural import CATEGORIES
    label, color, icon = CATEGORIES[e.category]
    return dict(
        category=e.category, category_label=label, name_color=color, category_icon=icon,
        id=e.id,
        spawn_key=e.spawn_key,
        species=e.species,
        name=NAMES.get(e.species, e.species),
        x=e.x,
        y=e.y,
        hp=e.hp,
        max_hp=e.max_hp,
        level=e.level,
        state=e.state,
        ai_state=e.ai_state,
    )


def target(db, c, key):
    enemies = instances(db, c)
    return next(
        (e for e in enemies if str(e.id) == str(key) or e.spawn_key == key), None
    )
