"""Finite personal first-floor resource nodes, no timer respawn or direct money grant."""

from sqlalchemy import select
from .models import (
    ResourceNode,
    RoomState,
    RoomConnection,
    ItemDefinition,
    WorldEvent,
    Item,
)
from .rooms import current, event
from .config import settings
from .inventory import add_item, ensure_collection_capacity
from .world import distance

REGIONS = {"common_a": ("herb", 3), "common_b": ("ore", 2)}


def nodes(db, c):
    room = current(db, c)
    if room.id not in REGIONS:
        return []
    from .rooms import discover

    generation = discover(db, c, room).generation
    rows = db.scalars(
        select(ResourceNode)
        .where(
            ResourceNode.character_id == c.id,
            ResourceNode.room_id == room.id,
            ResourceNode.generation == generation,
        )
        .order_by(ResourceNode.id)
    ).all()
    known = {n.node_key for n in rows}
    definition, stock = REGIONS[room.id]
    blocked = {tuple(p) for p in room.data["walls"]} | {
        (s["x"], s["y"]) for s in room.data.get("spawns", {}).values()
    }
    if room.data.get("npc"):
        blocked.add(tuple(room.data["npc"]))
    blocked |= {
        (e.x, e.y)
        for e in db.scalars(
            select(RoomConnection).where(RoomConnection.source == room.id)
        )
    }
    points = [p for p in room.data.get("resources", []) if tuple(p) not in blocked][:2]
    for index, (x, y) in enumerate(points):
        key = f"{definition}:{index}"
        if key in known:
            continue
        n = ResourceNode(
            character_id=c.id,
            room_id=room.id,
            generation=generation,
            node_key=key,
            definition=definition,
            x=x,
            y=y,
            capacity=stock,
            remaining=stock,
            enabled=True,
        )
        db.add(n)
        rows.append(n)
    db.flush()
    return rows


def payload(db, n):
    return {
        "id": n.id,
        "name": db.get(ItemDefinition, n.definition).name,
        "definition": n.definition,
        "x": n.x,
        "y": n.y,
        "remaining": n.remaining,
        "capacity": n.capacity,
        "enabled": n.enabled,
        "respawn": "Sem reposição automática; revisão administrativa auditada apenas.",
    }


def state(db, c):
    return [payload(db, n) for n in nodes(db, c)]


def collect(db, c, node_id, request_id):
    from .game import idle, fail

    key = f"gather:{c.id}:{request_id}"
    old = db.scalar(select(WorldEvent).where(WorldEvent.key == key))
    if old:
        if old.payload["node_id"] != node_id:
            fail("Chave de coleta já usada com outro ponto")
        return {**old.payload, "replayed": True}
    idle(db, c)
    node = db.scalar(
        select(ResourceNode)
        .where(ResourceNode.id == node_id, ResourceNode.character_id == c.id)
        .with_for_update()
    )
    if not node:
        fail("Ponto de coleta inexistente", 404)
    room = current(db, c)
    rs = db.get(RoomState, (c.id, room.id))
    if node.room_id != room.id or not rs or node.generation != rs.generation:
        fail("Ponto fora da sua região atual")
    if not node.enabled or node.remaining <= 0:
        fail("Ponto esgotado ou indisponível")
    if distance((c.x, c.y), (node.x, node.y)) > 1:
        fail("Aproxime-se do recurso")
    d = db.get(ItemDefinition, node.definition)
    ensure_collection_capacity(db, c, d, 1, settings.collection_slots)
    add_item(db, c, d.id, 1, key)
    node.remaining -= 1
    from .observability import add

    add(db, c, resources_gathered=1)
    from .contracts import progress

    progress(db, c, "collect", d.id, 1)
    result = {
        "node_id": node.id,
        "definition": d.id,
        "quantity": 1,
        "remaining": node.remaining,
        "message": f"{d.name} coletado. Estoque restante: {node.remaining}.",
    }
    event(db, "RESOURCE_COLLECTED", c, key=key, **result)
    return result
