from fastapi import HTTPException
from sqlalchemy import select
from .models import (
    Character,
    Battle,
    Item,
    ItemDefinition,
    Treasury,
    Ledger,
    WorldEvent,
)
from .config import settings
from .rooms import (
    RoomType,
    DomainEvent,
    current,
    discover,
    enter,
    room_payload,
    atlas,
    event,
)
from .models import Room, RoomState
from .world import WALLS, WIDTH, HEIGHT, NPC, MONSTERS, PORTAL, distance, map_data


def fail(message, code=409):
    raise HTTPException(code, message)


def character(db, account):
    c = db.scalar(
        select(Character).where(Character.account_id == account.id).with_for_update()
    )
    if not c:
        fail("Crie seu personagem primeiro", 404)
    return c


def active(db, c):
    return db.scalar(
        select(Battle).where(Battle.character_id == c.id, Battle.status == "active")
    )


def idle(db, c):
    if active(db, c):
        fail("Termine o combate primeiro")


def inventory(db, c):
    rows = db.execute(
        select(Item, ItemDefinition)
        .join(ItemDefinition, Item.definition == ItemDefinition.id)
        .where(Item.owner == c.id)
    ).all()
    return [
        dict(
            id=i.id,
            name=d.name,
            kind=d.kind,
            quantity=i.quantity,
            equipped=i.equipped,
            location=i.location,
        )
        for i, d in rows
    ]


def snapshot(db, c):
    b = active(db, c)
    room, data = room_payload(db, c)
    from .exploration import raid_state

    db.flush()
    return {
        "character": {
            k: getattr(c, k)
            for k in (
                "id",
                "name",
                "level",
                "xp",
                "hp",
                "energy",
                "strength",
                "defense",
                "coins",
                "floor",
                "x",
                "y",
                "room_id",
            )
        },
        "inventory": inventory(db, c),
        "battle": battle_data(b) if b else None,
        "unlocked_floor": (
            2 if db.scalar(select(WorldEvent).where(WorldEvent.key == "floor:2")) else 1
        ),
        "map": data,
        "room": room,
        "atlas": atlas(db, c),
        "raid": raid_state(db, c),
    }


def battle_data(b):
    return {
        k: getattr(b, k)
        for k in ("id", "monster", "hp", "turn", "status", "claimed", "reward_amount")
    }


def move(db, c, dx, dy):
    idle(db, c)
    if abs(dx) + abs(dy) != 1:
        fail("Movimento deve ter exatamente uma casa", 422)
    target = (c.x + dx, c.y + dy)
    data = current(db, c).data
    blocked = {tuple(p) for p in data["walls"]} | {
        tuple(p) for p in data["monsters"].values()
    }
    if data.get("npc"):
        blocked.add(tuple(data["npc"]))
    if (
        not (0 <= target[0] < data["width"] and 0 <= target[1] < data["height"])
        or target in blocked
    ):
        fail("Passagem bloqueada")
    c.x, c.y = target


def interact(db, c):
    idle(db, c)
    npc = current(db, c).data.get("npc")
    if not npc or distance((c.x, c.y), npc) > 1:
        fail("Aproxime-se da curandeira")
    c.hp = 30 + (c.level - 1) * 5
    c.energy = 10
    return {
        "message": "Bem-vindo à Torre! Sua vida e energia foram restauradas. Derrote monstros e reivindique as recompensas da Guilda."
    }


def travel(db, c, floor):
    idle(db, c)
    portal = current(db, c).data.get("portal")
    if not portal or distance((c.x, c.y), portal) > 1:
        fail("Aproxime-se do portal")
    if floor not in (1, 2) or (
        floor == 2
        and not db.scalar(select(WorldEvent).where(WorldEvent.key == "floor:2"))
    ):
        fail("Andar bloqueado")
    enter(db, c, db.get(Room, f"city{floor}"))
    c.x = 23
    c.y = 3


def start_battle(db, c, monster):
    idle(db, c)
    room = current(db, c)
    monsters = room.data["monsters"]
    if room.kind in (RoomType.CITY, RoomType.GUILD):
        fail("Cidade e Guilda são zonas seguras")
    if monster not in monsters:
        fail("Monstro inexistente", 404)
    if distance((c.x, c.y), monsters[monster]) > 1:
        fail("Aproxime-se do monstro")
    hp = room.data.get("enemy_hp", 40 if monster == "boss" else 12)
    b = Battle(character_id=c.id, monster=monster, hp=hp, room_id=room.id)
    rs = discover(db, c, room)
    rs.codex = {**rs.codex, monster: {"name": monster, "seen": True, "defeated": False}}
    event(db, DomainEvent.COMBAT_STARTED, c, monster=monster)
    db.add(b)
    db.flush()
    return battle_data(b)


def action(db, c, battle_id, turn, action):
    b = db.get(Battle, battle_id)
    if not b or b.character_id != c.id:
        fail("Combate inexistente", 404)
    if b.status != "active" or b.turn != turn:
        fail("Turno já processado ou combate encerrado")
    if action not in ("attack", "skill", "defend"):
        fail("Ação inválida", 422)
    if action == "skill" and c.energy < 2:
        fail("Energia insuficiente")
    sword = db.scalar(
        select(Item).where(
            Item.owner == c.id, Item.equipped == True, Item.location == "inventory"
        )
    )
    damage = c.strength + (3 if sword else 0)
    if action == "skill":
        c.energy -= 2
        damage += 5
    if action != "defend":
        b.hp = max(0, b.hp - damage)
    b.turn += 1
    room = db.get(Room, b.room_id) if b.room_id else current(db, c)
    training = b.monster == "dummy"
    secret = room.kind == RoomType.SECRET_DUNGEON
    if b.hp == 0:
        b.status = "won"
        rs = discover(db, c, room)
        first = not rs.completed
        rs.codex = {
            **rs.codex,
            b.monster: {"name": b.monster, "seen": True, "defeated": True},
        }
        if training:
            b.claimed = True
            b.reward_amount = 0
        elif secret:
            b.reward_amount = (
                settings.secret_first_reward if first else settings.secret_repeat_reward
            )
            c.xp += 100 if first else 0
            rs.completed = True
            if first:
                event(
                    db,
                    DomainEvent.SECRET_DUNGEON_COMPLETED,
                    c,
                    key=f"secret-done:{c.id}:{room.id}",
                )
        else:
            c.xp += 30 if b.monster == "slime" else 100
        event(db, DomainEvent.COMBAT_FINISHED, c, battle=b.id, result="won")
        while c.xp >= c.level * 50:
            c.xp -= c.level * 50
            c.level += 1
            c.strength += 1
            c.hp = 30 + (c.level - 1) * 5
        if not training and (not secret or first):
            db.add(Item(owner=c.id, definition="crystal", quantity=1))
        if b.monster == "boss":
            rs.completed = True
            event(db, DomainEvent.FLOOR_BOSS_DEFEATED, c, key=f"boss-defeated:{c.id}")
            # Lock a singleton before testing the unique event, serializing global unlock.
            db.scalar(select(Treasury).where(Treasury.id == 1).with_for_update())
            if not db.scalar(select(WorldEvent).where(WorldEvent.key == "floor:2")):
                db.add(
                    WorldEvent(
                        key="floor:2",
                        kind="FLOOR_UNLOCKED",
                        payload={"floor": 2, "character": c.id},
                        processed=True,
                    )
                )
    else:
        incoming = max(
            0 if training else 1,
            (
                0
                if training
                else room.data.get("enemy_attack", 8 if b.monster == "boss" else 5)
            )
            - c.defense
            - (3 if action == "defend" else 0),
        )
        c.hp = max(0, c.hp - incoming)
        if c.hp == 0:
            b.status = "lost"
            event(db, DomainEvent.COMBAT_FINISHED, c, battle=b.id, result="lost")
            enter(db, c, db.get(Room, "city1"))
            c.hp = 30 + (c.level - 1) * 5
            c.energy = 10
    db.flush()
    return battle_data(b)


def claim(db, c, battle_id):
    npc = current(db, c).data.get("npc")
    if not npc or distance((c.x, c.y), npc) > 1:
        fail("Aproxime-se da Guilda (curandeira)")
    b = db.get(Battle, battle_id)
    if not b or b.character_id != c.id or b.status != "won" or b.claimed:
        fail("Recompensa indisponível")
    treasury = db.scalar(select(Treasury).where(Treasury.id == 1).with_for_update())
    amount = (
        b.reward_amount
        if b.reward_amount is not None
        else (settings.boss_reward if b.monster == "boss" else settings.monster_reward)
    )
    if amount < 0 or treasury.balance < amount:
        fail("Tesouro sem orçamento; solicite depois")
    treasury.balance -= amount
    c.coins += amount
    b.claimed = True
    db.add(
        Ledger(
            reference=f"battle:{b.id}",
            source="treasury",
            destination=f"character:{c.id}",
            amount=amount,
        )
    )
    return {"paid": amount}


def equip(db, c, item_id):
    idle(db, c)
    item = db.get(Item, item_id)
    if not item or item.owner != c.id or item.location != "inventory":
        fail("Item indisponível", 404)
    definition = db.get(ItemDefinition, item.definition)
    if definition.kind != "weapon":
        fail("Item não equipável")
    for old in db.scalars(
        select(Item).where(Item.owner == c.id, Item.equipped == True)
    ):
        old.equipped = False
    item.equipped = True
