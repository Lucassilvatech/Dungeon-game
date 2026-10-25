"""A single, durable, atomic PLAYER_DIED_IN_EXPEDITION per valid expedition."""

from sqlalchemy import select
from .models import DeathEvent, Expedition, Room, Battle
from .clock import utc_now
from .rooms import RoomType, event, enter
from .config import settings, runtime_setting
from .economy import medical_fee, DEBT_LIMIT
from .attributes import penalize_levels
from .auctions import create_from_death


def resolve(db, c, battle):
    # Replays return the immutable receipt, even after a later expedition starts.
    previous = db.scalar(select(DeathEvent).where(DeathEvent.battle_id == battle.id))
    if previous:
        return previous.receipt
    room = db.get(Room, battle.room_id)
    expedition = db.scalar(
        select(Expedition)
        .where(Expedition.room_id == battle.room_id, Expedition.character_id == c.id)
        .with_for_update()
    )
    if not (
        room
        and room.kind == RoomType.PROCEDURAL
        and room.owner_id == c.id
        and expedition
        and expedition.status == "ACTIVE"
        and c.room_id == room.id
        and c.hp == 0
        and battle.status == "lost"
        and battle.character_id == c.id
    ):
        return None
    death = DeathEvent(
        character_id=c.id, expedition_id=expedition.id, battle_id=battle.id, receipt={}
    )
    db.add(death)
    db.flush()
    from .game import pending, reward_value

    rows = pending(db, c)
    adjustments = [dict(battle_id=b.id, amount=reward_value(b)) for b in rows]
    lost = sum(row["amount"] for row in adjustments)
    for b in rows:
        b.reward_amount = 0
        b.claimed = True
    event(
        db,
        "PENDING_REWARD_LOST",
        c,
        key=f"death-pending:{death.id}",
        death_event_id=death.id,
        amount=lost,
        adjustments=adjustments,
    )
    xp_lost = c.xp
    c.xp = 0
    fee = medical_fee(
        db, c, runtime_setting(db, "medical_fee_base"), death.id, expedition.id
    )
    penalty = dict(
        level_before=c.level,
        level_after=c.level,
        levels_lost=0,
        unspent_consumed=0,
        attribute_debt_added=0,
    )
    at_limit = c.coins == -DEBT_LIMIT
    if at_limit:
        penalty = penalize_levels(c)
        event(
            db,
            "LEVEL_PENALTY",
            c,
            key=f"death-level:{death.id}",
            death_event_id=death.id,
            **penalty,
        )
    items = create_from_death(db, c, death)
    expedition.status = "FAILED"
    expedition.finished_at = utc_now()
    receipt = dict(
        **fee,
        battle_id=battle.id,
        xp_lost=xp_lost,
        pending_lost=lost,
        pending_lost_exact=str(lost),
        balance_after_exact=str(c.coins),
        items=items,
        debt_limit_reached=at_limit,
        **penalty,
    )
    death.receipt = receipt
    expedition.result = receipt
    event(
        db,
        "PLAYER_DIED_IN_EXPEDITION",
        c,
        room.id,
        key=f"exp-death:{expedition.id}",
        **receipt,
    )
    enter(db, c, db.get(Room, "city1"))
    max_hp = 30 + (c.level - 1) * 5
    c.hp = max(1, max_hp * settings.respawn_hp_percent // 100)
    c.energy = 10
    db.flush()
    return receipt


def latest(db, c):
    death = db.scalar(
        select(DeathEvent)
        .where(DeathEvent.character_id == c.id, DeathEvent.acknowledged == False)
        .order_by(DeathEvent.id.desc())
        .limit(1)
    )
    return death.receipt if death else None


def acknowledge(db, c, death_id):
    from .game import fail

    death = db.get(DeathEvent, death_id)
    if not death or death.character_id != c.id:
        fail("Registro de morte inexistente", 404)
    death.acknowledged = True
    return {"message": "Resgate concluído. Você está na cidade."}
