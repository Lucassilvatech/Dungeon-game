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
from .config import settings, runtime_setting
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
from .world import distance
from .enemies import instances, target, payload, EnemyState
from .balance import damage, ENEMIES, NAMES
from .inventory import add_item
from .models import EnemyInstance
from .clock import utc_now


def fail(message, code=409):
    raise HTTPException(code, message)


def character(db, account):
    c = db.scalar(
        select(Character).where(Character.account_id == account.id).with_for_update()
    )
    if not c:
        fail("Crie seu personagem primeiro", 404)
    from .expeditions import resume

    resume(db, c)
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
        .where(Item.owner == c.id, Item.location == "inventory")
    ).all()
    return [
        dict(
            id=i.id,
            name=d.name,
            definition=d.id,
            protected=not d.death_transferable or d.id == "sword",
            kind=d.kind,
            power=d.power,
            quantity=i.quantity,
            equipped=i.equipped,
            location=i.location,
            stackable=d.stackable,
            max_stack_size=d.max_stack_size,
            description=d.description,
        )
        for i, d in rows
    ]


def snapshot(db, c, wander=False):
    from .expeditions import state as expedition_state

    expedition = expedition_state(db, c)
    from .deaths import latest
    from .models import Auction
    from sqlalchemy import func

    reserved = db.scalar(
        select(func.coalesce(func.sum(Auction.highest_bid), 0)).where(
            Auction.highest_bidder_id == c.id, Auction.status.in_(["OPEN", "CLOSED"])
        )
    )
    b = active(db, c)
    enemies = instances(db, c, wander=wander)
    room, data = room_payload(db, c)
    data["enemies"] = [payload(e) for e in enemies]
    data["monsters"] = {
        e.spawn_key: [e.x, e.y] for e in enemies if e.state != EnemyState.DEAD
    }
    data["enemy_names"] = {
        e.spawn_key: NAMES.get(e.species, e.species)
        for e in enemies
        if e.state != EnemyState.DEAD
    }
    from .exploration import raid_state

    from .fast_travel import destinations

    records = pending(db, c)
    summary = reward_summary_from(records)
    db.flush()
    return {
        "guild_rewards": summary,
        "reward_records": [battle_data(row) for row in records],
        "fast_destinations": destinations(db, c),
        "guild_treasury": str(db.get(Treasury, 1).balance),
        "character": {
            k: getattr(c, k)
            for k in (
                "id",
                "name",
                "level",
                "xp",
                "hp",
                "energy",
                "unspent_attribute_points",
                "attribute_point_debt",
                "strength",
                "defense",
                "coins",
                "floor",
                "x",
                "y",
                "room_id",
                "adventure_streak",
            )
        },
        "next_boss_chance": __import__("app.procedural", fromlist=["chance"]).chance(
            c.adventure_streak
        ),
        "attributes": __import__("app.attributes", fromlist=["effective"]).effective(
            db, c
        ),
        "death": latest(db, c),
        "coins_exact": str(c.coins),
        "reserved_gold": str(int(reserved)),
        "inventory": inventory(db, c),
        "expedition": expedition,
        "battle": battle_data(b) if b else None,
        "unlocked_floor": (
            2 if db.scalar(select(WorldEvent).where(WorldEvent.key == "floor:2")) else 1
        ),
        "map": data,
        "room": room,
        "atlas": atlas(db, c),
        "raid": raid_state(db, c),
        "events": [
            dict(id=e.id, kind=e.kind, payload=e.payload)
            for e in reversed(
                db.scalars(
                    select(WorldEvent)
                    .where(WorldEvent.payload["character"].as_integer() == c.id)
                    .order_by(WorldEvent.id.desc())
                    .limit(32)
                ).all()
            )
        ],
    }


def battle_data(b):
    return {
        k: getattr(b, k)
        for k in (
            "id",
            "enemy_id",
            "monster",
            "hp",
            "turn",
            "status",
            "claimed",
            "reward_amount",
        )
    }


def move(db, c, dx, dy):
    idle(db, c)
    if abs(dx) + abs(dy) != 1:
        fail("Movimento deve ter exatamente uma casa", 422)
    target = (c.x + dx, c.y + dy)
    data = current(db, c).data
    blocked = {tuple(p) for p in data["walls"]} | {
        (e.x, e.y) for e in instances(db, c) if e.state != EnemyState.DEAD
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
    if current(db, c).id == "auction_hall":
        npc = current(db, c).data.get("npc")
        if not npc or distance((c.x, c.y), npc) > 1:
            fail("Aproxime-se do leiloeiro")
        return {
            "message": "Leiloeiro: consulte espólios, detalhes e histórico de lances.",
            "open_auctions": True,
        }
    if current(db, c).id == "recovery_hall":
        npc = current(db, c).data.get("npc")
        if not npc or distance((c.x, c.y), npc) > 1:
            fail("Aproxime-se do Guardião de Recuperação")
        return {
            "message": "Recuperação pessoal: adicional de 100%, total de 200% do valor-base.",
            "open_recovery": True,
        }
    receptionist(db, c)
    return {
        "message": "Recepcionista da Guilda: seus registros estão prontos para conferência.",
        "rewards": reward_summary(db, c),
    }


def rest(db, c):
    idle(db, c)
    if current(db, c).kind not in (RoomType.CITY, RoomType.GUILD):
        fail("Descanse na cidade ou na Guilda")
    c.hp = 30 + (c.level - 1) * 5
    c.energy = 10
    return {"message": "Você descansou em segurança. Vida e energia restauradas."}


def travel(db, c, floor):
    from .expeditions import guard_departure

    guard_departure(db, c)
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
    if room.kind in (RoomType.CITY, RoomType.GUILD):
        fail("Cidade e Guilda são zonas seguras")
    if room.kind == RoomType.PROCEDURAL:
        from .models import Expedition

        expedition = db.scalar(
            select(Expedition).where(
                Expedition.room_id == room.id, Expedition.character_id == c.id
            )
        )
        if not expedition or expedition.status != "ACTIVE":
            fail("Expedição encerrada")
    e = target(db, c, monster)
    if not e:
        fail("Monstro inexistente", 404)
    if e.state != EnemyState.ALIVE:
        fail("Inimigo morto ou indisponível")
    if distance((c.x, c.y), (e.x, e.y)) > 1:
        fail("Aproxime-se do monstro")
    e.state = EnemyState.IN_COMBAT
    e.ai_state = "COMBAT"
    b = Battle(
        character_id=c.id, monster=e.species, hp=e.hp, room_id=room.id, enemy_id=e.id
    )
    db.add(b)
    db.flush()
    rs = discover(db, c, room)
    rs.codex = {
        **rs.codex,
        e.species: {
            "name": NAMES.get(e.species, e.species),
            "seen": True,
            "defeated": rs.codex.get(e.species, {}).get("defeated", False),
        },
    }
    event(db, "ENEMY_COMBAT_STARTED", c, enemy_id=e.id, battle=b.id)
    event(
        db, DomainEvent.COMBAT_STARTED, c, monster=e.species, enemy_id=e.id, battle=b.id
    )
    return battle_data(b)


def action(db, c, battle_id, turn, action):
    b = db.get(Battle, battle_id)
    if not b or b.character_id != c.id:
        fail("Combate inexistente", 404)
    if b.status != "active" or b.turn != turn:
        fail("Turno já processado ou combate encerrado")
    if not b.enemy_id:
        instances(db, c)
        db.flush()
        db.refresh(b)
    e = db.scalar(
        select(EnemyInstance).where(EnemyInstance.id == b.enemy_id).with_for_update()
    )
    if not e or e.character_id != c.id or e.state != EnemyState.IN_COMBAT:
        fail("Inimigo indisponível")
    if action not in ("attack", "skill", "defend"):
        fail("Ação inválida", 422)
    if action == "skill" and c.energy < 2:
        fail("Energia insuficiente")
    from .attributes import effective

    stats = effective(db, c)
    if action == "skill":
        c.energy -= 2
    dealt = (
        0
        if action == "defend"
        else damage(
            stats["strength"]["effective"], e.defense, c.level, skill=action == "skill"
        )
    )
    e.hp = max(0, e.hp - dealt)
    b.hp = e.hp
    b.turn += 1
    event(db, "ENEMY_DAMAGED", c, enemy_id=e.id, damage=dealt, hp=e.hp, battle=b.id)
    room = db.get(Room, b.room_id)
    training = e.species == "dummy"
    secret = room.kind == RoomType.SECRET_DUNGEON
    if e.hp == 0:
        # The entire DYING -> DEAD transition and all effects commit atomically.
        e.state = EnemyState.DYING
        e.death_at = utc_now()
        e.ai_state = "DEAD"
        b.status = "won"
        event(
            db,
            "ENEMY_DIED",
            c,
            key=f"death:{e.id}",
            enemy_id=e.id,
            species=e.species,
            battle=b.id,
        )
        rs = discover(db, c, room)
        first = not rs.completed
        rs.codex = {
            **rs.codex,
            e.species: {
                "name": NAMES.get(e.species, e.species),
                "seen": True,
                "defeated": True,
            },
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
            b.reward_amount = (
                runtime_setting(db, "boss_reward")
                if e.category == "boss"
                else runtime_setting(db, "monster_reward")
            )
            c.xp += e.xp_reward
        from .attributes import gain_levels

        gain_levels(db, c)
        if not training and (not secret or first):
            event(
                db,
                "ITEM_DROPPED",
                c,
                key=f"drop:{e.id}",
                enemy_id=e.id,
                definition="crystal",
                quantity=1,
            )
            add_item(db, c, "crystal", 1, f"enemy:{e.id}")
        if not training:
            event(
                db,
                "GUILD_REWARD_REGISTERED",
                c,
                key=f"register:{e.id}",
                enemy_id=e.id,
                battle=b.id,
                amount=b.reward_amount,
            )
        if e.species == "boss":
            rs.completed = True
            event(db, DomainEvent.FLOOR_BOSS_DEFEATED, c, key=f"boss-defeated:{c.id}")
            # Retain the pre-existing compatibility event; no new upper-floor content.
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
        e.state = EnemyState.DEAD
        event(db, "ENEMY_REMOVED", c, key=f"remove:{e.id}", enemy_id=e.id)
        event(
            db, DomainEvent.COMBAT_FINISHED, c, battle=b.id, result="won", enemy_id=e.id
        )
    else:
        incoming = (
            0
            if training
            else damage(
                e.attack,
                stats["defense"]["effective"],
                e.level,
                guard=action == "defend",
            )
        )
        c.hp = max(0, c.hp - incoming)
        if c.hp == 0:
            c.adventure_streak = 0
            b.status = "lost"
            e.state = EnemyState.ALIVE
            e.hp = e.max_hp
            e.ai_state = "IDLE"
            event(
                db,
                DomainEvent.COMBAT_FINISHED,
                c,
                battle=b.id,
                result="lost",
                enemy_id=e.id,
            )
            from .deaths import resolve

            death = resolve(db, c, b)
            if death is None:
                enter(db, c, db.get(Room, "city1"))
                c.hp = 30 + (c.level - 1) * 5
                c.energy = 10
    db.flush()
    from .expeditions import sync

    sync(db, c)
    return {**battle_data(b), "damage": dealt}


def receptionist(db, c):
    room = current(db, c)
    npc = room.data.get("npc")
    if room.id != "guild" or not npc or distance((c.x, c.y), npc) > 1:
        fail("Aproxime-se da recepcionista na Guilda")


def pending(db, c):
    return db.scalars(
        select(Battle)
        .where(
            Battle.character_id == c.id, Battle.status == "won", Battle.claimed == False
        )
        .order_by(Battle.id)
        .with_for_update()
    ).all()


def reward_value(b):
    return (
        b.reward_amount
        if b.reward_amount is not None
        else (settings.boss_reward if b.monster == "boss" else settings.monster_reward)
    )


def reward_summary(db, c):
    return reward_summary_from(pending(db, c))


def reward_summary_from(rows):
    groups = {}
    for b in rows:
        name = NAMES.get(b.monster, b.monster)
        groups[name] = groups.get(name, 0) + 1
    return {
        "count": len(rows),
        "total": sum(reward_value(b) for b in rows),
        "groups": groups,
    }


def pay(db, c, rows):
    if not rows:
        fail("Nenhuma recompensa pendente")
    total = sum(reward_value(b) for b in rows)
    treasury = db.scalar(select(Treasury).where(Treasury.id == 1).with_for_update())
    if total < 0 or treasury.balance < total:
        fail("Tesouro sem orçamento; solicite depois")
    treasury.balance -= total
    for b in rows:
        b.claimed = True
        from .economy import credit_player_gold

        credit_player_gold(db, c, reward_value(b), "treasury", f"battle:{b.id}")
        event(
            db,
            "GUILD_REWARD_CLAIMED",
            c,
            key=f"claim:{b.id}",
            battle=b.id,
            enemy_id=b.enemy_id,
            amount=reward_value(b),
        )
    from .procedural_retention import prune

    for room_id in {b.room_id for b in rows}:
        prune(db, c, room_id)
    return {
        "paid": total,
        "message": f"Recepcionista: {total} moedas pagas por {len(rows)} registros.",
    }


def claim(db, c, battle_id):
    receptionist(db, c)
    b = db.get(Battle, battle_id)
    if not b or b.character_id != c.id or b.status != "won" or b.claimed:
        fail("Recompensa indisponível")
    return pay(db, c, [b])


def claim_all(db, c):
    idle(db, c)
    receptionist(db, c)
    return pay(db, c, pending(db, c))


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


def unequip(db, c, item_id):
    idle(db, c)
    item = db.get(Item, item_id)
    if not item or item.owner != c.id or item.location != "inventory":
        fail("Item indisponível", 404)
    item.equipped = False
