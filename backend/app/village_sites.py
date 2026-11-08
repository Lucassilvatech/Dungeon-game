"""Idempotent village service interiors. Never regenerates inventory, economy or instances."""

from copy import deepcopy
from collections import deque
from sqlalchemy import select
from . import models as m

SITES = {
    "merchant": {
        "room": "merchant_shop",
        "name": "Loja do Comerciante",
        "door": [25, 10],
        "building": [22, 5],
        "theme": "merchant",
    },
    "blacksmith": {
        "room": "blacksmith_workshop",
        "name": "Oficina do Ferreiro",
        "door": [39, 9],
        "building": [36, 4],
        "theme": "smith",
    },
    "alchemist": {
        "room": "alchemy_laboratory",
        "name": "Laboratório de Alquimia",
        "door": [38, 29],
        "building": [35, 24],
        "theme": "alchemy",
    },
    "barber": {
        "room": "barber_shop",
        "name": "Barbearia",
        "door": [17, 30],
        "building": [15, 26],
        "theme": "barber",
    },
}
SERVICES = [
    {
        "id": id,
        "name": {
            "merchant": "Comerciante",
            "blacksmith": "Ferreiro",
            "alchemist": "Alquimista",
            "barber": "Barbeiro",
        }[id],
        "room_id": s["room"],
        "x": 10,
        "y": 8,
        "sprite": "npc" if id == "barber" else id,
    }
    for id, s in SITES.items()
]


def interior(id):
    w, h = 22, 18
    walls = {
        (x, y) for x in range(w) for y in range(h) if x in (0, w - 1) or y in (0, h - 1)
    }

    # Interactive counter has a clear approach on either side; spawn and exit stay open.
    def fixture(kind, x, y, width, height):
        return dict(kind=kind, x=x, y=y, width=width, height=height, solid=True)

    decorations = [
        fixture("service_counter", 9, 6, 3, 2),
        {"kind": "rug", "x": 8, "y": 10, "width": 6, "height": 4, "solid": False},
        fixture("service_barrels", 3, 12, 2, 1),
    ]
    furnishings = {
        "merchant": [
            fixture("service_goods", 3, 2, 2, 3),
            fixture("service_goods", 17, 2, 2, 3),
        ],
        "blacksmith": [
            fixture("service_tools", 3, 2, 2, 2),
            fixture("service_forge", 15, 2, 3, 3),
            fixture("service_anvil", 15, 10, 2, 1),
        ],
        "alchemist": [
            fixture("service_potions", 3, 2, 2, 3),
            fixture("service_potions", 17, 2, 2, 3),
            fixture("service_alchemy", 15, 11, 3, 2),
        ],
        "barber": [
            fixture("service_goods", 3, 2, 2, 3),
            fixture("service_mirror", 16, 2, 2, 3),
            fixture("service_chair", 16, 10, 1, 2),
        ],
    }
    decorations.extend(furnishings[id])
    for d in decorations:
        if d.get("solid"):
            walls.update(
                (x, y)
                for x in range(d["x"], d["x"] + d.get("width", 1))
                for y in range(d["y"], d["y"] + d.get("height", 1))
            )
    return {
        "width": w,
        "height": h,
        "walls": [list(p) for p in sorted(walls)],
        "npc": None,
        "npcs": [],
        "monsters": {},
        "spawns": {},
        "portal": None,
        "resources": [],
        "decorations": decorations,
        "theme": "interior",
        "interior_theme": SITES[id]["theme"],
        "seed": 0,
        "layout_version": 4,
        "service_site_version": 1,
        "entry_point": [10, 14],
        "service_npcs": [next(n for n in SERVICES if n["id"] == id)],
    }


def nearest_free(data, position):
    walls = {tuple(p) for p in data["walls"]}
    forbidden = walls | {tuple(data["npc"])} if data.get("npc") else walls
    forbidden |= {(n["x"], n["y"]) for n in data.get("service_npcs", [])}
    queue = deque([position])
    seen = {position}
    while queue:
        p = queue.popleft()
        if (
            p not in forbidden
            and 0 < p[0] < data["width"] - 1
            and 0 < p[1] < data["height"] - 1
        ):
            return p
        for dx, dy in [(0, 1), (1, 0), (-1, 0), (0, -1)]:
            q = (p[0] + dx, p[1] + dy)
            if (
                q not in seen
                and 0 <= q[0] < data["width"]
                and 0 <= q[1] < data["height"]
            ):
                seen.add(q)
                queue.append(q)
    raise RuntimeError("A vila não possui ponto livre")


def patch_city(data):
    data = deepcopy(data)
    if data.get("service_site_version") != 1:
        # Reuse the three pre-existing house footprints. No world regeneration.
        for id, s in SITES.items():
            existing = next(
                (
                    b
                    for b in data.get("buildings", [])
                    if [b["x"], b["y"]] == s["building"]
                ),
                None,
            )
            if id != "barber" and not existing:
                raise RuntimeError(
                    "Layout de vila personalizado; revise a entrada de " + id
                )
            if existing:
                existing.update(name=s["name"], service_id=id)
        if not any(b.get("service_id") == "barber" for b in data["buildings"]):
            b = {
                "x": 15,
                "y": 26,
                "width": 5,
                "height": 4,
                "name": "Barbearia",
                "service_id": "barber",
            }
            footprint = {(x, y) for x in range(15, 20) for y in range(26, 30)}
            if footprint & {tuple(p) for p in data["walls"]}:
                raise RuntimeError(
                    "Área da barbearia ocupada por geometria personalizada"
                )
            data["buildings"].append(b)
            data["walls"] = [
                list(p) for p in sorted({tuple(p) for p in data["walls"]} | footprint)
            ]
        data["service_npcs"] = [
            n for n in data.get("service_npcs", []) if n["id"] not in SITES
        ]
        data["service_site_version"] = 1
    return data


def seed(db):
    city = db.get(m.Room, "city1")
    if not city:
        return
    for id, s in SITES.items():
        room = db.get(m.Room, s["room"])
        if not room:
            db.add(
                m.Room(
                    id=s["room"],
                    floor_id=1,
                    name=s["name"],
                    kind="BUILDING_INTERIOR",
                    seed=0,
                    danger_tier=0,
                    data=interior(id),
                )
            )
        elif room.data.get("service_site_version") != 1:
            raise RuntimeError(
                "Interior personalizado conflita com a instalação de " + s["room"]
            )
    db.flush()
    if city.data.get("service_site_version") != 1:
        data = patch_city(city.data)
        city.data = data
        # A saved character under the new small shop is moved only to nearest free tile.
        relocated = []
        for c in db.scalars(
            select(m.Character).where(m.Character.room_id == city.id).with_for_update()
        ):
            if not (15 <= c.x < 20 and 26 <= c.y < 30):
                continue
            before = (c.x, c.y)
            after = nearest_free(data, before)
            if after != before:
                c.x, c.y = after
                relocated.append(
                    {"character": c.id, "before": list(before), "after": list(after)}
                )
        db.add(
            m.WorldEvent(
                key="village-service-interiors:v1",
                kind="VILLAGE_SERVICES_RELOCATED",
                processed=True,
                payload={
                    "rooms": {id: s["room"] for id, s in SITES.items()},
                    "relocated_characters": relocated,
                    "inventory_changed": False,
                    "money_created": "0",
                },
            )
        )
    for id, s in SITES.items():
        for source, target, p in [
            ("city1", s["room"], s["door"]),
            (s["room"], "city1", [10, 15]),
        ]:
            if not db.scalar(
                select(m.RoomConnection).where(
                    m.RoomConnection.source == source, m.RoomConnection.target == target
                )
            ):
                db.add(m.RoomConnection(source=source, target=target, x=p[0], y=p[1]))
    db.flush()
