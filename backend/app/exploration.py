"""Exploration commands. Call with the character row locked by game.character."""

import secrets
from sqlalchemy import select
from .models import Room, RoomConnection, RoomState, WorldEvent, Raid, RaidMember
from .rooms import (
    RoomType,
    DomainEvent,
    current,
    discover,
    enter,
    template,
    atlas,
    event,
)
from .world import distance
from .config import settings
from . import game


def exit_room(db, c, exit_id):
    from .expeditions import guard_departure

    guard_departure(db, c)
    game.idle(db, c)
    edge = db.get(RoomConnection, exit_id)
    if not edge or edge.source != c.room_id:
        game.fail("Saída inexistente", 404)
    if distance((c.x, c.y), (edge.x, edge.y)) > 1:
        game.fail("Caminhe até a saída")
    target = db.get(Room, edge.target)
    if target.owner_id not in (None, c.id):
        game.fail("Sala privada", 403)
    enter(db, c, target)


def adventure(db, c, request_id):
    key = f"adventure:{c.id}:{request_id}"
    old = db.scalar(select(WorldEvent).where(WorldEvent.key == key))
    if old:
        return {"message": "Esta aventura já foi processada."}
    from .expeditions import guard_departure

    guard_departure(db, c)
    game.idle(db, c)
    if current(db, c).kind not in (
        RoomType.COMMON,
        RoomType.COMBAT,
        RoomType.PROCEDURAL,
        RoomType.CITY,
    ):
        game.fail("Aventure-se a partir da cidade ou das trilhas")
    key = f"adventure:{c.id}:{request_id}"
    old = db.scalar(select(WorldEvent).where(WorldEvent.key == key))
    if old:
        return {"message": "Esta aventura já foi processada."}
    if c.floor != 1:
        game.fail("Exploração do segundo andar ainda indisponível")
    secret = db.get(Room, "secret")
    found = db.get(RoomState, (c.id, secret.id))
    if not found and secrets.randbelow(1000000) < int(
        max(0, min(1, settings.secret_chance)) * 1000000
    ):
        discover(db, c, secret)
        event(db, DomainEvent.ADVENTURE_STARTED, c, key=key, result="secret")
        return {
            "message": f"Entrada descoberta: {secret.name}. Use Ir para masmorra. Conteúdo ainda desconhecido."
        }
    from uuid import uuid4
    from .layouts import THEMES

    room_id = f"proc:{c.id}:{uuid4().hex}"
    previous = db.scalar(
        select(Room)
        .where(Room.owner_id == c.id, Room.kind == RoomType.PROCEDURAL)
        .order_by(Room.id.desc())
        .limit(1)
    )
    # Different themes across consecutive expeditions, but reproducible from saved seed.
    recent = db.scalar(
        select(WorldEvent)
        .where(
            WorldEvent.kind == "ADVENTURE_STARTED",
            WorldEvent.payload["character"].as_integer() == c.id,
        )
        .order_by(WorldEvent.id.desc())
    )
    previous_id = recent.payload.get("result") if recent else None
    previous = (
        db.get(Room, previous_id)
        if previous_id and previous_id != "secret"
        else previous
    )
    for _ in range(100):
        seed = secrets.randbelow(2**31)
        data = template(seed)
        if not previous or previous.data.get("theme") != data["theme"]:
            break
    else:
        game.fail("Não foi possível gerar outra expedição; tente novamente")
    room = Room(
        id=room_id,
        floor_id=c.floor,
        name="Expedição · "
        + {
            "moss_stone": "Pedra e musgo",
            "wild_ruins": "Ruínas silvestres",
            "crystal_bones": "Gruta dos cristais",
            "abandoned_wood": "Entreposto esquecido",
        }[data["theme"]],
        kind=RoomType.PROCEDURAL,
        owner_id=c.id,
        seed=seed,
        data=data,
    )
    db.add(room)
    db.flush()
    db.add(RoomConnection(source=room.id, target="common_a", x=2, y=9))
    event(
        db,
        "ROOM_GENERATED",
        c,
        room.id,
        key=f"generated:{room.id}",
        seed=seed,
        theme=data["theme"],
    )
    event(db, DomainEvent.ADVENTURE_STARTED, c, key=key, result=room.id)
    enter(db, c, room)
    from .expeditions import register, sync

    record = register(db, c, room)
    from .procedural import configure_room

    configure_room(db, c, room, record)
    sync(db, c)
    return {
        "message": "Nova expedição criada. Seed e baixas são preservadas nesta instância."
    }


def secret_travel(db, c, room_id):
    from .expeditions import guard_departure

    guard_departure(db, c)
    game.idle(db, c)
    room = db.get(Room, room_id)
    if (
        not room
        or room.kind != RoomType.SECRET_DUNGEON
        or not db.get(RoomState, (c.id, room.id))
    ):
        game.fail("Destino desconhecido", 404)
    if c.room_id == room.id:
        game.fail("Saia da masmorra antes de iniciar outra tentativa")
    rs = db.get(RoomState, (c.id, room.id))
    if rs.visits:
        rs.generation += 1
    enter(db, c, room)


def leave_secret(db, c):
    game.idle(db, c)
    if current(db, c).kind != RoomType.SECRET_DUNGEON:
        game.fail("Você não está numa masmorra secreta")
    enter(db, c, db.get(Room, "city1"))


def raid_state(db, c):
    membership = db.scalar(
        select(RaidMember)
        .join(Raid)
        .where(RaidMember.character_id == c.id, Raid.status == "forming")
        .order_by(Raid.id.desc())
    )
    if not membership:
        return None
    raid = db.get(Raid, membership.raid_id)
    from .models import Character

    members = db.scalars(
        select(Character)
        .join(RaidMember, RaidMember.character_id == Character.id)
        .where(RaidMember.raid_id == raid.id)
    ).all()
    return {
        "id": raid.id,
        "invite": raid.invite,
        "status": raid.status,
        "leader_id": raid.leader_id,
        "participants": [{"id": m.id, "name": m.name} for m in members],
        "cooperative_combat": False,
    }


def create_raid(db, c):
    game.idle(db, c)
    if not db.get(RoomState, (c.id, "boss")):
        game.fail("Descubra o chefe primeiro")
    if raid_state(db, c):
        game.fail("Você já participa de uma raid")
    r = Raid(leader_id=c.id, invite=secrets.token_urlsafe(12))
    db.add(r)
    db.flush()
    db.add(RaidMember(raid_id=r.id, character_id=c.id))
    event(db, DomainEvent.RAID_CREATED, c, raid=r.id)
    db.flush()
    return raid_state(db, c)


def join_raid(db, c, invite):
    game.idle(db, c)
    if raid_state(db, c):
        game.fail("Você já participa de uma raid")
    r = db.scalar(select(Raid).where(Raid.invite == invite).with_for_update())
    if not r or r.status != "forming":
        game.fail("Convite indisponível", 404)
    members = db.scalars(select(RaidMember).where(RaidMember.raid_id == r.id)).all()
    if len(members) >= 4:
        game.fail("Raid completa")
    db.add(RaidMember(raid_id=r.id, character_id=c.id))
    event(db, DomainEvent.RAID_JOINED, c, raid=r.id)
    db.flush()
    return raid_state(db, c)


def leave_raid(db, c):
    state = raid_state(db, c)
    if not state:
        game.fail("Sem raid ativa")
    raid = db.scalar(select(Raid).where(Raid.id == state["id"]).with_for_update())
    if raid.leader_id == c.id:
        raid.status = "closed"
    else:
        db.delete(db.get(RaidMember, (raid.id, c.id)))
    return {"message": "Você saiu da raid."}
