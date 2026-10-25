"""Committed procedural encounters. All commands run under the character row lock."""

from enum import StrEnum
import hashlib
import json
from sqlalchemy import select
from .models import Expedition, Room, Battle, EnemyInstance, RoomState
from .clock import utc_now
from .rooms import RoomType, event, enter, current


class ExpeditionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FLED = "FLED"
    FAILED = "FAILED"


MESSAGE = "Você ainda está em uma expedição. Derrote os inimigos restantes ou fuja da aventura."


def get_active(db, c):
    return db.scalar(
        select(Expedition)
        .where(
            Expedition.character_id == c.id,
            Expedition.status == ExpeditionStatus.ACTIVE,
        )
        .with_for_update()
    )


def register(db, c, room):
    record = db.scalar(select(Expedition).where(Expedition.room_id == room.id))
    if not record:
        record = Expedition(character_id=c.id, room_id=room.id, seed=room.seed)
        db.add(record)
        db.flush()
        event(
            db,
            "EXPEDITION_STARTED",
            c,
            room.id,
            key=f"exp-start:{record.id}",
            expedition=record.id,
        )
    return record


def sync(db, c):
    """Finish only when every spawn is persisted and every instance is DEAD."""
    from .enemies import instances, EnemyState

    record = get_active(db, c)
    if not record and current(db, c).kind == RoomType.PROCEDURAL:
        record = register(db, c, current(db, c))
    if not record:
        return None, 0
    if record.status != ExpeditionStatus.ACTIVE:
        return record, 0
    # Active encounters are the location authority, including reconnects after legacy updates.
    if c.room_id != record.room_id:
        room = db.get(Room, record.room_id)
        c.room_id = room.id
        c.floor = room.floor_id
        c.x = 2
        c.y = 2
    enemies = instances(db, c)
    alive = sum(e.state != EnemyState.DEAD for e in enemies)
    if not alive:
        record.status = ExpeditionStatus.COMPLETED
        record.finished_at = utc_now()
        db.get(RoomState, (c.id, record.room_id)).completed = True
        event(
            db,
            "EXPEDITION_COMPLETED",
            c,
            record.room_id,
            key=f"exp-completed:{record.id}",
            expedition=record.id,
        )
    return record, alive


def resume(db, c):
    # Never silently replace a living expedition with a city/another room.
    record = get_active(db, c)
    if record and c.room_id != record.room_id:
        c.room_id = record.room_id
        c.floor = db.get(Room, record.room_id).floor_id
        c.x = 2
        c.y = 2


def guard_departure(db, c):
    from .game import fail

    record, alive = sync(db, c)
    if record and record.status == ExpeditionStatus.ACTIVE and alive:
        fail(MESSAGE)


def state(db, c):
    record, alive = sync(db, c)
    if not record:
        record = db.scalar(
            select(Expedition).where(
                Expedition.character_id == c.id, Expedition.room_id == c.room_id
            )
        )
    if not record:
        return None
    return dict(
        id=record.id,
        room_id=record.room_id,
        seed=record.seed,
        status=record.status,
        alive_enemies=alive,
        can_leave=record.status != ExpeditionStatus.ACTIVE,
        started_at=record.started_at,
        finished_at=record.finished_at,
    )


def preview(db, c, expedition_id):
    from .game import fail, pending, reward_value, active

    record = db.scalar(
        select(Expedition)
        .where(Expedition.id == expedition_id, Expedition.character_id == c.id)
        .with_for_update()
    )
    if not record:
        fail("Expedição inexistente", 404)
    if record.status == ExpeditionStatus.FLED:
        return {"status": "FLED", **record.result}
    synced, alive = sync(db, c)
    if (
        record.status != ExpeditionStatus.ACTIVE
        or not synced
        or synced.id != record.id
        or not alive
    ):
        fail("A expedição não está ativa")
    rows = pending(db, c)
    amounts = [(b.id, reward_value(b)) for b in rows]
    total = sum(amount for _, amount in amounts)
    battle = active(db, c)
    fingerprint = json.dumps(
        [
            record.id,
            amounts,
            c.level,
            c.xp,
            battle.id if battle else None,
            battle.turn if battle else None,
        ],
        separators=(",", ":"),
    )
    return dict(
        expedition_id=record.id,
        status=record.status,
        alive_enemies=alive,
        pending_before=total,
        pending_after=total // 2,
        reward_loss=total - total // 2,
        xp_lost=c.xp,
        level=c.level,
        confirmation_token=hashlib.sha256(fingerprint.encode()).hexdigest(),
    )


def flee(db, c, expedition_id, confirmation_token):
    from .game import fail, pending, reward_value, active

    record = db.scalar(
        select(Expedition)
        .where(Expedition.id == expedition_id, Expedition.character_id == c.id)
        .with_for_update()
    )
    if not record:
        fail("Expedição inexistente", 404)
    if record.status == ExpeditionStatus.FLED:
        return {"status": "FLED", **record.result, "replayed": True}
    current_preview = preview(db, c, expedition_id)
    if current_preview["confirmation_token"] != confirmation_token:
        fail("Os valores mudaram. Revise a confirmação da fuga novamente.")
    rows = pending(db, c)
    remaining = current_preview["pending_after"]
    adjustments = []
    for b in rows:
        before = reward_value(b)
        after = min(before, remaining)
        remaining -= after
        b.reward_amount = after
        adjustments.append(dict(battle_id=b.id, before=before, after=after))
    c.xp = 0
    battle = active(db, c)
    if battle:
        battle.status = "fled"
        battle.claimed = True
        event(
            db,
            "COMBAT_FINISHED",
            c,
            record.room_id,
            battle=battle.id,
            result="fled",
            enemy_id=battle.enemy_id,
        )
        if battle.enemy_id:
            enemy = db.get(EnemyInstance, battle.enemy_id)
            enemy.state = "ALIVE"
            enemy.ai_state = "IDLE"
            enemy.hp = enemy.max_hp
    record.status = ExpeditionStatus.FLED
    record.finished_at = utc_now()
    result = {
        k: v
        for k, v in current_preview.items()
        if k not in ("confirmation_token", "status")
    }
    result.update(
        adjustments=adjustments,
        destination="city1",
        message=f"Você fugiu da expedição. Recompensas perdidas: {result['reward_loss']}; pendentes restantes: {result['pending_after']}; XP atual perdido: {result['xp_lost']}. Você retornou à cidade.",
    )
    record.result = result
    event(
        db,
        "EXPEDITION_FLED",
        c,
        record.room_id,
        key=f"exp-fled:{record.id}",
        expedition=record.id,
        **result,
    )
    enter(db, c, db.get(Room, "city1"))
    db.flush()
    return {"status": "FLED", **result, "replayed": False}
