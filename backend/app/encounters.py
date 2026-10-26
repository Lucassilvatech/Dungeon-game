"""Opt-in first-floor groups; legacy Battle remains each enemy's one-time reward receipt."""

from collections import deque
from sqlalchemy import select
from .models import CombatEncounter, EnemyInstance, Battle, Room
from .config import settings
from .clock import utc_now
from .rooms import current, event
from .balance import damage


def active(db, c):
    return db.scalar(
        select(CombatEncounter).where(
            CombatEncounter.character_id == c.id, CombatEncounter.status == "ACTIVE"
        )
    )


def get(db, c, id):
    from .game import fail

    g = db.scalar(
        select(CombatEncounter)
        .where(CombatEncounter.id == id, CombatEncounter.character_id == c.id)
        .with_for_update()
    )
    if not g:
        fail("Encontro inexistente", 404)
    return g


def members(db, g):
    return db.scalars(
        select(EnemyInstance)
        .where(EnemyInstance.id.in_(g.enemy_ids))
        .order_by(EnemyInstance.id)
    ).all()


def payload(db, g):
    from .enemies import payload as enemy_payload

    enemies = members(db, g)
    return {
        "id": g.id,
        "status": g.status,
        "turn": g.turn,
        "room_id": g.room_id,
        "selected_enemy_id": g.selected_enemy_id,
        "size": g.size,
        "enemies": [enemy_payload(e) for e in enemies],
        "turn_order": [{"actor": "player"}]
        + [{"actor": "enemy", "enemy_id": e.id} for e in enemies if e.state != "DEAD"],
        "current_actor": "player" if g.status == "ACTIVE" else None,
        "last_round": g.last_round,
        "damage_dealt": g.damage_dealt,
        "damage_received": g.damage_received,
    }


def state(db, c):
    g = active(db, c)
    return payload(db, g) if g else None


def path_distance(room, start, end):
    walls = {tuple(p) for p in room.data["walls"]}
    if room.data.get("npc"):
        walls.add(tuple(room.data["npc"]))
    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        position, d = queue.popleft()
        if position == end:
            return d
        if d >= settings.encounter_radius:
            continue
        for dx, dy in ((0, 1), (1, 0), (-1, 0), (0, -1)):
            q = position[0] + dx, position[1] + dy
            if (
                q not in seen
                and q not in walls
                and 0 < q[0] < room.data["width"] - 1
                and 0 < q[1] < room.data["height"] - 1
            ):
                seen.add(q)
                queue.append((q, d + 1))
    return None


def start(db, c, enemy_ids, request_id):
    from . import game
    from .enemies import instances

    old = db.scalar(
        select(CombatEncounter).where(
            CombatEncounter.character_id == c.id,
            CombatEncounter.request_id == request_id,
        )
    )
    if old:
        if old.enemy_ids != enemy_ids:
            game.fail("Chave de encontro já usada com outros alvos")
        return {**payload(db, old), "replayed": True}
    game.idle(db, c)
    room = current(db, c)
    if room.floor_id != 1 or room.kind not in ("COMMON", "COMBAT", "PROCEDURAL"):
        game.fail(
            "Grupos disponíveis apenas em regiões comuns e aventuras do primeiro andar"
        )
    if not 2 <= len(enemy_ids) <= settings.encounter_max_enemies or len(
        set(enemy_ids)
    ) != len(enemy_ids):
        game.fail("Escolha um grupo pequeno de alvos diferentes", 422)
    available = {e.id: e for e in instances(db, c)}
    if any(
        i not in available
        or available[i].state != "ALIVE"
        or available[i].category in ("boss", "unique")
        for i in enemy_ids
    ):
        game.fail("Alvo morto, protegido por regras próprias ou indisponível")
    lead = available[enemy_ids[0]]
    if abs(lead.x - c.x) + abs(lead.y - c.y) > 1:
        game.fail("Aproxime-se do primeiro alvo")
    if any(
        path_distance(room, (lead.x, lead.y), (available[i].x, available[i].y)) is None
        for i in enemy_ids[1:]
    ):
        game.fail("Alvos distantes demais ou sem caminho válido entre si")
    # All validation precedes mutation. Character lock serializes group and single starts.
    first = game.start_battle(db, c, str(lead.id))
    g = CombatEncounter(
        character_id=c.id,
        room_id=room.id,
        request_id=request_id,
        enemy_ids=enemy_ids,
        selected_enemy_id=lead.id,
        size=len(enemy_ids),
        last_round=[],
    )
    db.add(g)
    db.flush()
    db.get(Battle, first["id"]).encounter_id = g.id
    for id in enemy_ids[1:]:
        e = available[id]
        e.state = "IN_COMBAT"
        e.ai_state = "COMBAT"
        db.add(
            Battle(
                character_id=c.id,
                room_id=room.id,
                enemy_id=e.id,
                encounter_id=g.id,
                monster=e.species,
                hp=e.hp,
            )
        )
    db.flush()
    event(db, "ENCOUNTER_STARTED", c, encounter_id=g.id, size=g.size)
    return {
        **payload(db, g),
        "message": f"Encontro com {g.size} inimigos. Você age primeiro; sobreviventes respondem por ordem de identidade.",
    }


def select_target(db, c, id, target_id, turn):
    from .game import fail

    g = get(db, c, id)
    if g.status != "ACTIVE" or g.turn != turn:
        fail("Turno já processado ou encontro encerrado")
    if not any(e.id == target_id and e.state == "IN_COMBAT" for e in members(db, g)):
        fail("Alvo indisponível")
    g.selected_enemy_id = target_id
    return payload(db, g)


def close(db, c, status, death_battle_id=None):
    g = active(db, c)
    if not g:
        return None
    g.status = status
    g.finished_at = utc_now()
    for b in db.scalars(
        select(Battle).where(Battle.encounter_id == g.id, Battle.status == "active")
    ):
        b.status = (
            "lost"
            if b.id == death_battle_id
            else "fled" if status == "FLED" else "interrupted"
        )
        b.claimed = b.id != death_battle_id
        e = db.get(EnemyInstance, b.enemy_id)
        if e and e.state != "DEAD":
            e.state = "ALIVE"
            e.ai_state = "IDLE"
            e.hp = e.max_hp
    event(
        db,
        "ENCOUNTER_FINISHED",
        c,
        encounter_id=g.id,
        status=status,
        turns=g.turn,
        damage_dealt=g.damage_dealt,
        damage_received=g.damage_received,
    )
    return g


def action(db, c, id, turn, target_id, action):
    from . import game
    from .attributes import effective

    g = get(db, c, id)
    if g.status != "ACTIVE" or g.turn != turn:
        game.fail("Turno já processado ou encontro encerrado")
    enemies = members(db, g)
    target = next(
        (e for e in enemies if e.id == target_id and e.state == "IN_COMBAT"), None
    )
    if not target:
        game.fail("Alvo indisponível")
    b = db.scalar(
        select(Battle).where(
            Battle.encounter_id == g.id,
            Battle.enemy_id == target_id,
            Battle.status == "active",
        )
    )
    if not b:
        game.fail("Participante inconsistente")
    g.selected_enemy_id = target.id
    before = target.hp
    result = game.action(
        db, c, b.id, b.turn, action, _encounter=True, counter=False, synchronize=False
    )
    dealt = before - target.hp
    g.damage_dealt += dealt
    g.turn += 1
    round = [
        {
            "actor": "player",
            "target_id": target.id,
            "damage": dealt,
            "hp_after": target.hp,
        }
    ]
    defense = effective(db, c)["defense"]["effective"]
    for enemy in enemies:
        if enemy.state == "DEAD":
            continue
        incoming = damage(enemy.attack, defense, enemy.level, guard=action == "defend")
        actual = min(c.hp, incoming)
        c.hp -= actual
        g.damage_received += actual
        round.append(
            {"actor": "enemy", "enemy_id": enemy.id, "damage": actual, "hp_after": c.hp}
        )
        if c.hp == 0:
            death_battle = db.scalar(
                select(Battle).where(
                    Battle.encounter_id == g.id,
                    Battle.enemy_id == enemy.id,
                    Battle.status == "active",
                )
            )
            g.last_round = round
            close(db, c, "LOST", death_battle.id)
            c.adventure_streak = 0
            from .deaths import resolve

            if resolve(db, c, death_battle) is None:
                from .rooms import enter

                enter(db, c, db.get(Room, "city1"))
                c.hp = 30 + (c.level - 1) * 5
                c.energy = 10
            db.flush()
            return {
                "status": "lost",
                "enemy_id": target.id,
                "damage": dealt,
                "encounter": payload(db, g),
            }
    g.last_round = round
    survivors = [e for e in enemies if e.state != "DEAD"]
    if not survivors:
        close(db, c, "WON")
    elif target.state == "DEAD":
        g.selected_enemy_id = survivors[0].id
    db.flush()
    from .expeditions import sync

    sync(db, c)
    return {
        "status": "won" if g.status == "WON" else "active",
        "enemy_id": target.id,
        "damage": dealt,
        "encounter": payload(db, g),
    }
