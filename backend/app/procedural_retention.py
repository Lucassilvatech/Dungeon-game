"""Prune only new procedural transient state. Preserve receipts and unpaid rewards."""
from sqlalchemy import select, delete, update
from .models import Room, Expedition, Battle, EnemyInstance, DeathEvent, WorldEvent


def prune(db, c, room_id):
    room=db.get(Room,room_id)
    expedition=db.scalar(select(Expedition).where(Expedition.room_id==room_id))
    if not room or not room.data.get("procedural_version") or not expedition or expedition.status=="ACTIVE":
        return
    db.flush()
    common=list(db.scalars(select(EnemyInstance.id).where(EnemyInstance.room_id==room_id,EnemyInstance.character_id==c.id,EnemyInstance.category.in_(["common","rare","miniboss"]))))
    if common:
        db.execute(update(Battle).where(Battle.enemy_id.in_(common)).values(enemy_id=None))
        db.execute(delete(EnemyInstance).where(EnemyInstance.id.in_(common)))
    specials=select(Battle.id).join(EnemyInstance,EnemyInstance.id==Battle.enemy_id).where(EnemyInstance.category.in_(["boss","unique"]))
    db.execute(delete(Battle).where(Battle.room_id==room_id,Battle.status!="active",Battle.claimed==True,~Battle.id.in_(select(DeathEvent.battle_id)),~Battle.id.in_(specials)))
    db.execute(delete(WorldEvent).where(WorldEvent.payload["room"].as_string()==room_id,WorldEvent.kind.in_(["ENEMY_SPAWNED","ENEMY_COMBAT_STARTED","ENEMY_DAMAGED","ENEMY_DIED","ENEMY_REMOVED","COMBAT_STARTED","COMBAT_FINISHED"])))
