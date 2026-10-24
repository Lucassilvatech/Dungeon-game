"""first floor enemy instances and inventory stacks"""
from alembic import op
import sqlalchemy as sa

revision = '11ac6a18a976'
down_revision = 'd348cc807194'
branch_labels = None
depends_on = None

# Frozen generation rules for upgrading existing v2 procedural instances.
"""Original first-floor content. Seed drives all geometry and decoration, never the client."""

from collections import deque
import random

ROOM_SIZES = {
    "CITY": (52, 36),
    "GUILD": (38, 28),
    "TRAINING": (32, 24),
    "COMMON": (34, 26),
    "COMBAT": (40, 28),
    "BOSS": (34, 26),
    "SECRET_DUNGEON": (34, 26),
}
ENEMY_DENSITY = {"COMMON": 3, "COMBAT": 6, "PROCEDURAL": 5}
THEMES = ["moss_stone", "wild_ruins", "crystal_bones", "abandoned_wood"]
DECORATIONS = {
    "moss_stone": ["rock", "moss", "torch", "statue"],
    "wild_ruins": ["tree", "bush", "flower", "ruin"],
    "crystal_bones": ["crystal", "bones", "rock", "torch"],
    "abandoned_wood": ["barrel", "crate", "shelf", "torch"],
    "interior": ["table", "chair", "shelf", "barrel", "banner"],
    "city": ["tree", "flower", "barrel", "bench", "well"],
}


def reachable(data):
    blocked = {tuple(p) for p in data["walls"]}
    seen = {(2, 2)}
    queue = deque(seen)
    while queue:
        x, y = queue.popleft()
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            p = (x + dx, y + dy)
            if (
                p in seen
                or p in blocked
                or not (0 < p[0] < data["width"] - 1 and 0 < p[1] < data["height"] - 1)
            ):
                continue
            seen.add(p)
            queue.append(p)
    return seen


def generate(kind, seed=0, theme_index=None):
    rng = random.Random(seed)
    procedural = kind == "PROCEDURAL"
    if procedural:
        w, h = rng.choice([(32, 24), (36, 28), (40, 26), (44, 30)])
        theme = (
            THEMES[theme_index % len(THEMES)]
            if theme_index is not None
            else rng.choice(THEMES)
        )
    else:
        w, h = ROOM_SIZES.get(kind, (34, 26))
        theme = (
            "city"
            if kind == "CITY"
            else "interior" if kind in ("GUILD", "TRAINING") else THEMES[seed % 4]
        )
    walls = {
        (x, y) for x in range(w) for y in range(h) if x in (0, w - 1) or y in (0, h - 1)
    }
    d = dict(
        width=w,
        height=h,
        walls=[],
        npc=[17, 7] if kind == "GUILD" else None,
        npc_name="Recepcionista da Guilda",
        monsters={},
        spawns={},
        portal=None,
        theme=theme,
        resources=[],
        decorations=[],
        difficulty=1,
        layout_version=3,
        template=f"{theme}:{w}x{h}",
        seed=seed,
    )
    # Keep the former first-map area open so saved positions remain traversable.
    if kind in ("COMMON", "COMBAT", "PROCEDURAL"):
        walls.add((3, 3))
        d["decorations"].append({"kind": "rock", "x": 3, "y": 3, "solid": True})
    if kind == "CITY":
        d["buildings"] = [
            dict(x=7, y=3, width=6, height=4, name="Guilda"),
            dict(x=22, y=5, width=7, height=5, name="Mercado · futuro"),
            dict(x=36, y=4, width=6, height=5, name="Ferreiro · futuro"),
            dict(x=35, y=24, width=6, height=5, name="Casa dos viajantes"),
        ]
        for b in d["buildings"]:
            walls |= {
                (x, y)
                for x in range(b["x"], b["x"] + b["width"])
                for y in range(b["y"], b["y"] + b["height"])
            }
        d["npcs"] = [
            {"id": "traveler", "name": "Viajante", "x": 16, "y": 12, "walk": True},
            {"id": "merchant", "name": "Moradora", "x": 29, "y": 14, "walk": False},
        ]
    if kind == "GUILD":
        d["decorations"] += [
            {
                "kind": "counter",
                "x": 14,
                "y": 8,
                "width": 8,
                "height": 2,
                "solid": True,
            },
            {"kind": "board", "x": 23, "y": 4, "width": 4, "height": 2, "solid": False},
            {"kind": "rug", "x": 13, "y": 11, "width": 10, "height": 7, "solid": False},
        ]
        walls |= {(x, y) for x in range(14, 22) for y in (8, 9)}
        d["decorations"] += [
            {"kind": "table", "x": x, "y": y, "width": 3, "height": 2, "solid": False}
            for x, y in [(6, 14), (25, 14), (6, 21), (25, 21)]
        ]
        d["decorations"] += [
            {"kind": "chair", "x": x, "y": y, "solid": False}
            for x, y in [(7, 13), (7, 16), (26, 13), (26, 16), (7, 20), (26, 23)]
        ]
        d["decorations"] += [
            {"kind": "shelf", "x": x, "y": 3, "solid": False} for x in [3, 5, 29, 31]
        ]
        d["npcs"] = [
            {"id": "scout", "name": "Batedora", "x": 8, "y": 16, "walk": False},
            {"id": "visitor", "name": "Aventureiro", "x": 27, "y": 18, "walk": True},
        ]
    reserved = {
        (2, 2),
        (2, 9),
        (w - 2, h // 2),
        (9, 7),
        (w - 3, 10),
        (17, 6),
        (17, 7),
        (12, 8),
        (5, 6),
        (10, 6),
        (10, 7),
    }
    # Scattered single obstacles cannot seal a corridor; disconnected results are removed.
    count = (w * h) // 25
    for _ in range(count):
        x, y = rng.randrange(2, w - 2), rng.randrange(2, h - 2)
        if (x, y) in reserved or (x < 16 and y < 12):
            continue
        if any(abs(x - px) + abs(y - py) < 2 for px, py in reserved):
            continue
        solid = rng.random() < 0.4
        decor = {
            "kind": rng.choice(DECORATIONS.get(theme, DECORATIONS["wild_ruins"])),
            "x": x,
            "y": y,
            "solid": solid,
        }
        d["decorations"].append(decor)
        if solid:
            walls.add((x, y))
    d["walls"] = [list(p) for p in sorted(walls)]
    reach = reachable(d)
    # Remove any accidentally enclosed free pocket from the playable area.
    for x in range(1, w - 1):
        for y in range(1, h - 1):
            if (x, y) not in reach:
                walls.add((x, y))
    d["walls"] = [list(p) for p in sorted(walls)]
    if kind not in ("CITY", "GUILD"):
        if kind == "BOSS":
            spawns = {"boss": ((12, 8), "boss")}
        elif kind == "SECRET_DUNGEON":
            spawns = {"warden": ((10, 7), "warden")}
            d.update(
                recommended_level=8,
                difficulty="PERIGOSA",
                enemy_level=8,
                enemy_hp=90,
                enemy_attack=14,
            )
        elif kind == "TRAINING":
            spawns = {"dummy": ((10, 6), "dummy")}
        else:
            n = ENEMY_DENSITY.get(kind, 5) + (rng.randrange(3) if procedural else 0)
            spawns = {"slime": ((5, 6), "slime")}
            # Place roaming monsters far enough apart, with a reachable adjacent tile.
            candidates = [
                p for p in sorted(reach) if p[0] > 8 and p[1] > 4 and p not in reserved
            ]
            rng.shuffle(candidates)
            for p in candidates:
                if len(spawns) >= n:
                    break
                if any(
                    abs(p[0] - q[0]) + abs(p[1] - q[1]) < 5 for q, _ in spawns.values()
                ):
                    continue
                species = "goblin" if len(spawns) % 2 else "slime"
                spawns[f"{species}_{len(spawns)}"] = (p, species)
        for key, (p, species) in spawns.items():
            d["monsters"][key] = list(p)
            d["spawns"][key] = {"species": species, "x": p[0], "y": p[1]}
        if kind == "BOSS":
            d.update(recommended_level=3, difficulty="EXTREMA", recommended_group=4)
    d["resources"] = [
        list(p)
        for p in sorted(reach)
        if p[0] > 8 and (p[0] * 17 + p[1] * 11 + seed) % 113 == 0
    ][:6]
    return d

CONTENT = {'city1': {'width': 52, 'height': 36, 'walls': [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4], [0, 5], [0, 6], [0, 7], [0, 8], [0, 9], [0, 10], [0, 11], [0, 12], [0, 13], [0, 14], [0, 15], [0, 16], [0, 17], [0, 18], [0, 19], [0, 20], [0, 21], [0, 22], [0, 23], [0, 24], [0, 25], [0, 26], [0, 27], [0, 28], [0, 29], [0, 30], [0, 31], [0, 32], [0, 33], [0, 34], [0, 35], [1, 0], [1, 35], [2, 0], [2, 35], [3, 0], [3, 19], [3, 35], [4, 0], [4, 35], [5, 0], [5, 31], [5, 35], [6, 0], [6, 35], [7, 0], [7, 3], [7, 4], [7, 5], [7, 6], [7, 35], [8, 0], [8, 3], [8, 4], [8, 5], [8, 6], [8, 18], [8, 35], [9, 0], [9, 3], [9, 4], [9, 5], [9, 6], [9, 18], [9, 35], [10, 0], [10, 3], [10, 4], [10, 5], [10, 6], [10, 35], [11, 0], [11, 3], [11, 4], [11, 5], [11, 6], [11, 35], [12, 0], [12, 3], [12, 4], [12, 5], [12, 6], [12, 35], [13, 0], [13, 35], [14, 0], [14, 16], [14, 35], [15, 0], [15, 35], [16, 0], [16, 35], [17, 0], [17, 35], [18, 0], [18, 35], [19, 0], [19, 3], [19, 35], [20, 0], [20, 35], [21, 0], [21, 35], [22, 0], [22, 2], [22, 5], [22, 6], [22, 7], [22, 8], [22, 9], [22, 35], [23, 0], [23, 5], [23, 6], [23, 7], [23, 8], [23, 9], [23, 35], [24, 0], [24, 5], [24, 6], [24, 7], [24, 8], [24, 9], [24, 29], [24, 35], [25, 0], [25, 5], [25, 6], [25, 7], [25, 8], [25, 9], [25, 12], [25, 35], [26, 0], [26, 5], [26, 6], [26, 7], [26, 8], [26, 9], [26, 28], [26, 35], [27, 0], [27, 5], [27, 6], [27, 7], [27, 8], [27, 9], [27, 35], [28, 0], [28, 4], [28, 5], [28, 6], [28, 7], [28, 8], [28, 9], [28, 35], [29, 0], [29, 35], [30, 0], [30, 35], [31, 0], [31, 7], [31, 35], [32, 0], [32, 35], [33, 0], [33, 35], [34, 0], [34, 10], [34, 33], [34, 35], [35, 0], [35, 18], [35, 24], [35, 25], [35, 26], [35, 27], [35, 28], [35, 35], [36, 0], [36, 4], [36, 5], [36, 6], [36, 7], [36, 8], [36, 19], [36, 24], [36, 25], [36, 26], [36, 27], [36, 28], [36, 30], [36, 35], [37, 0], [37, 4], [37, 5], [37, 6], [37, 7], [37, 8], [37, 24], [37, 25], [37, 26], [37, 27], [37, 28], [37, 35], [38, 0], [38, 4], [38, 5], [38, 6], [38, 7], [38, 8], [38, 24], [38, 25], [38, 26], [38, 27], [38, 28], [38, 35], [39, 0], [39, 4], [39, 5], [39, 6], [39, 7], [39, 8], [39, 24], [39, 25], [39, 26], [39, 27], [39, 28], [39, 35], [40, 0], [40, 3], [40, 4], [40, 5], [40, 6], [40, 7], [40, 8], [40, 9], [40, 24], [40, 25], [40, 26], [40, 27], [40, 28], [40, 35], [41, 0], [41, 4], [41, 5], [41, 6], [41, 7], [41, 8], [41, 35], [42, 0], [42, 6], [42, 7], [42, 35], [43, 0], [43, 21], [43, 24], [43, 35], [44, 0], [44, 13], [44, 18], [44, 35], [45, 0], [45, 8], [45, 35], [46, 0], [46, 13], [46, 16], [46, 27], [46, 35], [47, 0], [47, 11], [47, 28], [47, 35], [48, 0], [48, 35], [49, 0], [49, 35], [50, 0], [50, 35], [51, 0], [51, 1], [51, 2], [51, 3], [51, 4], [51, 5], [51, 6], [51, 7], [51, 8], [51, 9], [51, 10], [51, 11], [51, 12], [51, 13], [51, 14], [51, 15], [51, 16], [51, 17], [51, 18], [51, 19], [51, 20], [51, 21], [51, 22], [51, 23], [51, 24], [51, 25], [51, 26], [51, 27], [51, 28], [51, 29], [51, 30], [51, 31], [51, 32], [51, 33], [51, 34], [51, 35]], 'npc': None, 'npc_name': 'Recepcionista da Guilda', 'monsters': {}, 'spawns': {}, 'portal': None, 'theme': 'city', 'resources': [[12, 2], [13, 21], [18, 3], [19, 22], [24, 4], [25, 23]], 'decorations': [{'kind': 'well', 'x': 26, 'y': 28, 'solid': True}, {'kind': 'barrel', 'x': 33, 'y': 27, 'solid': False}, {'kind': 'flower', 'x': 32, 'y': 24, 'solid': False}, {'kind': 'tree', 'x': 34, 'y': 10, 'solid': True}, {'kind': 'well', 'x': 41, 'y': 18, 'solid': False}, {'kind': 'tree', 'x': 47, 'y': 11, 'solid': True}, {'kind': 'tree', 'x': 45, 'y': 23, 'solid': False}, {'kind': 'flower', 'x': 24, 'y': 29, 'solid': True}, {'kind': 'well', 'x': 37, 'y': 32, 'solid': False}, {'kind': 'well', 'x': 18, 'y': 5, 'solid': False}, {'kind': 'tree', 'x': 48, 'y': 27, 'solid': False}, {'kind': 'barrel', 'x': 41, 'y': 33, 'solid': False}, {'kind': 'tree', 'x': 17, 'y': 22, 'solid': False}, {'kind': 'flower', 'x': 14, 'y': 16, 'solid': True}, {'kind': 'barrel', 'x': 36, 'y': 30, 'solid': True}, {'kind': 'well', 'x': 34, 'y': 33, 'solid': True}, {'kind': 'well', 'x': 20, 'y': 9, 'solid': False}, {'kind': 'well', 'x': 15, 'y': 20, 'solid': False}, {'kind': 'barrel', 'x': 26, 'y': 22, 'solid': False}, {'kind': 'tree', 'x': 13, 'y': 14, 'solid': False}, {'kind': 'tree', 'x': 41, 'y': 18, 'solid': False}, {'kind': 'tree', 'x': 45, 'y': 10, 'solid': False}, {'kind': 'well', 'x': 7, 'y': 27, 'solid': False}, {'kind': 'well', 'x': 19, 'y': 17, 'solid': False}, {'kind': 'barrel', 'x': 28, 'y': 19, 'solid': False}, {'kind': 'bench', 'x': 7, 'y': 22, 'solid': False}, {'kind': 'flower', 'x': 39, 'y': 23, 'solid': False}, {'kind': 'flower', 'x': 3, 'y': 19, 'solid': True}, {'kind': 'tree', 'x': 25, 'y': 12, 'solid': True}, {'kind': 'well', 'x': 46, 'y': 16, 'solid': True}, {'kind': 'flower', 'x': 42, 'y': 6, 'solid': True}, {'kind': 'barrel', 'x': 40, 'y': 9, 'solid': True}, {'kind': 'flower', 'x': 40, 'y': 3, 'solid': True}, {'kind': 'tree', 'x': 47, 'y': 9, 'solid': False}, {'kind': 'well', 'x': 45, 'y': 3, 'solid': False}, {'kind': 'tree', 'x': 8, 'y': 18, 'solid': True}, {'kind': 'flower', 'x': 43, 'y': 21, 'solid': True}, {'kind': 'tree', 'x': 5, 'y': 31, 'solid': True}, {'kind': 'barrel', 'x': 46, 'y': 27, 'solid': True}, {'kind': 'well', 'x': 48, 'y': 32, 'solid': False}, {'kind': 'tree', 'x': 12, 'y': 15, 'solid': False}, {'kind': 'barrel', 'x': 45, 'y': 12, 'solid': False}, {'kind': 'bench', 'x': 35, 'y': 18, 'solid': True}, {'kind': 'bench', 'x': 44, 'y': 13, 'solid': True}, {'kind': 'bench', 'x': 38, 'y': 21, 'solid': False}, {'kind': 'tree', 'x': 44, 'y': 18, 'solid': True}, {'kind': 'tree', 'x': 31, 'y': 7, 'solid': True}, {'kind': 'bench', 'x': 36, 'y': 19, 'solid': True}, {'kind': 'well', 'x': 24, 'y': 20, 'solid': False}, {'kind': 'bench', 'x': 42, 'y': 10, 'solid': False}, {'kind': 'tree', 'x': 49, 'y': 28, 'solid': False}, {'kind': 'flower', 'x': 2, 'y': 14, 'solid': False}, {'kind': 'bench', 'x': 17, 'y': 16, 'solid': False}, {'kind': 'well', 'x': 47, 'y': 28, 'solid': True}, {'kind': 'tree', 'x': 28, 'y': 4, 'solid': True}, {'kind': 'bench', 'x': 18, 'y': 12, 'solid': False}, {'kind': 'bench', 'x': 37, 'y': 2, 'solid': False}, {'kind': 'tree', 'x': 22, 'y': 21, 'solid': False}, {'kind': 'tree', 'x': 28, 'y': 14, 'solid': False}, {'kind': 'bench', 'x': 2, 'y': 27, 'solid': False}, {'kind': 'tree', 'x': 22, 'y': 2, 'solid': True}, {'kind': 'well', 'x': 45, 'y': 8, 'solid': True}, {'kind': 'barrel', 'x': 43, 'y': 14, 'solid': False}, {'kind': 'bench', 'x': 46, 'y': 13, 'solid': True}, {'kind': 'bench', 'x': 42, 'y': 7, 'solid': True}, {'kind': 'well', 'x': 9, 'y': 18, 'solid': True}, {'kind': 'flower', 'x': 43, 'y': 24, 'solid': True}, {'kind': 'flower', 'x': 19, 'y': 3, 'solid': True}, {'kind': 'barrel', 'x': 45, 'y': 18, 'solid': False}, {'kind': 'well', 'x': 38, 'y': 4, 'solid': False}], 'difficulty': 1, 'layout_version': 3, 'template': 'city:52x36', 'seed': 0, 'buildings': [{'x': 7, 'y': 3, 'width': 6, 'height': 4, 'name': 'Guilda'}, {'x': 22, 'y': 5, 'width': 7, 'height': 5, 'name': 'Mercado · futuro'}, {'x': 36, 'y': 4, 'width': 6, 'height': 5, 'name': 'Ferreiro · futuro'}, {'x': 35, 'y': 24, 'width': 6, 'height': 5, 'name': 'Casa dos viajantes'}], 'npcs': [{'id': 'traveler', 'name': 'Viajante', 'x': 16, 'y': 12, 'walk': True}, {'id': 'merchant', 'name': 'Moradora', 'x': 29, 'y': 14, 'walk': False}]}, 'guild': {'width': 38, 'height': 28, 'walls': [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4], [0, 5], [0, 6], [0, 7], [0, 8], [0, 9], [0, 10], [0, 11], [0, 12], [0, 13], [0, 14], [0, 15], [0, 16], [0, 17], [0, 18], [0, 19], [0, 20], [0, 21], [0, 22], [0, 23], [0, 24], [0, 25], [0, 26], [0, 27], [1, 0], [1, 27], [2, 0], [2, 27], [3, 0], [3, 27], [4, 0], [4, 21], [4, 27], [5, 0], [5, 27], [6, 0], [6, 27], [7, 0], [7, 27], [8, 0], [8, 25], [8, 27], [9, 0], [9, 14], [9, 17], [9, 22], [9, 27], [10, 0], [10, 27], [11, 0], [11, 27], [12, 0], [12, 27], [13, 0], [13, 27], [14, 0], [14, 8], [14, 9], [14, 27], [15, 0], [15, 8], [15, 9], [15, 27], [16, 0], [16, 8], [16, 9], [16, 27], [17, 0], [17, 8], [17, 9], [17, 27], [18, 0], [18, 4], [18, 8], [18, 9], [18, 27], [19, 0], [19, 8], [19, 9], [19, 27], [20, 0], [20, 8], [20, 9], [20, 24], [20, 27], [21, 0], [21, 8], [21, 9], [21, 27], [22, 0], [22, 20], [22, 27], [23, 0], [23, 27], [24, 0], [24, 4], [24, 27], [25, 0], [25, 27], [26, 0], [26, 15], [26, 27], [27, 0], [27, 27], [28, 0], [28, 20], [28, 27], [29, 0], [29, 3], [29, 27], [30, 0], [30, 4], [30, 27], [31, 0], [31, 27], [32, 0], [32, 4], [32, 19], [32, 27], [33, 0], [33, 12], [33, 27], [34, 0], [34, 6], [34, 17], [34, 27], [35, 0], [35, 27], [36, 0], [36, 27], [37, 0], [37, 1], [37, 2], [37, 3], [37, 4], [37, 5], [37, 6], [37, 7], [37, 8], [37, 9], [37, 10], [37, 11], [37, 12], [37, 13], [37, 14], [37, 15], [37, 16], [37, 17], [37, 18], [37, 19], [37, 20], [37, 21], [37, 22], [37, 23], [37, 24], [37, 25], [37, 26], [37, 27]], 'npc': [17, 7], 'npc_name': 'Recepcionista da Guilda', 'monsters': {}, 'spawns': {}, 'portal': None, 'theme': 'interior', 'resources': [[12, 2], [13, 21], [18, 3], [19, 22], [25, 23], [30, 5]], 'decorations': [{'kind': 'counter', 'x': 14, 'y': 8, 'width': 8, 'height': 2, 'solid': True}, {'kind': 'board', 'x': 23, 'y': 4, 'width': 4, 'height': 2, 'solid': False}, {'kind': 'rug', 'x': 13, 'y': 11, 'width': 10, 'height': 7, 'solid': False}, {'kind': 'table', 'x': 6, 'y': 14, 'width': 3, 'height': 2, 'solid': False}, {'kind': 'table', 'x': 25, 'y': 14, 'width': 3, 'height': 2, 'solid': False}, {'kind': 'table', 'x': 6, 'y': 21, 'width': 3, 'height': 2, 'solid': False}, {'kind': 'table', 'x': 25, 'y': 21, 'width': 3, 'height': 2, 'solid': False}, {'kind': 'chair', 'x': 7, 'y': 13, 'solid': False}, {'kind': 'chair', 'x': 7, 'y': 16, 'solid': False}, {'kind': 'chair', 'x': 26, 'y': 13, 'solid': False}, {'kind': 'chair', 'x': 26, 'y': 16, 'solid': False}, {'kind': 'chair', 'x': 7, 'y': 20, 'solid': False}, {'kind': 'chair', 'x': 26, 'y': 23, 'solid': False}, {'kind': 'shelf', 'x': 3, 'y': 3, 'solid': False}, {'kind': 'shelf', 'x': 5, 'y': 3, 'solid': False}, {'kind': 'shelf', 'x': 29, 'y': 3, 'solid': False}, {'kind': 'shelf', 'x': 31, 'y': 3, 'solid': False}, {'kind': 'banner', 'x': 26, 'y': 15, 'solid': True}, {'kind': 'shelf', 'x': 33, 'y': 14, 'solid': False}, {'kind': 'chair', 'x': 32, 'y': 13, 'solid': False}, {'kind': 'table', 'x': 34, 'y': 6, 'solid': True}, {'kind': 'banner', 'x': 18, 'y': 19, 'solid': False}, {'kind': 'shelf', 'x': 8, 'y': 25, 'solid': True}, {'kind': 'barrel', 'x': 32, 'y': 19, 'solid': True}, {'kind': 'chair', 'x': 22, 'y': 21, 'solid': False}, {'kind': 'shelf', 'x': 32, 'y': 16, 'solid': False}, {'kind': 'table', 'x': 5, 'y': 19, 'solid': False}, {'kind': 'table', 'x': 27, 'y': 24, 'solid': False}, {'kind': 'shelf', 'x': 33, 'y': 12, 'solid': True}, {'kind': 'chair', 'x': 16, 'y': 9, 'solid': False}, {'kind': 'shelf', 'x': 30, 'y': 4, 'solid': True}, {'kind': 'banner', 'x': 34, 'y': 17, 'solid': True}, {'kind': 'shelf', 'x': 20, 'y': 24, 'solid': True}, {'kind': 'shelf', 'x': 15, 'y': 21, 'solid': False}, {'kind': 'barrel', 'x': 30, 'y': 4, 'solid': False}, {'kind': 'chair', 'x': 22, 'y': 20, 'solid': True}, {'kind': 'shelf', 'x': 4, 'y': 21, 'solid': False}, {'kind': 'chair', 'x': 32, 'y': 4, 'solid': True}, {'kind': 'banner', 'x': 7, 'y': 24, 'solid': False}, {'kind': 'banner', 'x': 27, 'y': 24, 'solid': False}, {'kind': 'barrel', 'x': 28, 'y': 20, 'solid': True}, {'kind': 'table', 'x': 24, 'y': 4, 'solid': True}, {'kind': 'chair', 'x': 33, 'y': 20, 'solid': False}, {'kind': 'table', 'x': 17, 'y': 2, 'solid': False}, {'kind': 'shelf', 'x': 16, 'y': 13, 'solid': False}, {'kind': 'chair', 'x': 29, 'y': 3, 'solid': True}, {'kind': 'banner', 'x': 16, 'y': 3, 'solid': False}, {'kind': 'banner', 'x': 9, 'y': 22, 'solid': True}, {'kind': 'table', 'x': 9, 'y': 14, 'solid': True}, {'kind': 'chair', 'x': 4, 'y': 21, 'solid': True}, {'kind': 'table', 'x': 9, 'y': 17, 'solid': True}, {'kind': 'table', 'x': 3, 'y': 19, 'solid': False}, {'kind': 'shelf', 'x': 18, 'y': 4, 'solid': True}], 'difficulty': 1, 'layout_version': 3, 'template': 'interior:38x28', 'seed': 0, 'npcs': [{'id': 'scout', 'name': 'Batedora', 'x': 8, 'y': 16, 'walk': False}, {'id': 'visitor', 'name': 'Aventureiro', 'x': 27, 'y': 18, 'walk': True}]}, 'training': {'width': 32, 'height': 24, 'walls': [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4], [0, 5], [0, 6], [0, 7], [0, 8], [0, 9], [0, 10], [0, 11], [0, 12], [0, 13], [0, 14], [0, 15], [0, 16], [0, 17], [0, 18], [0, 19], [0, 20], [0, 21], [0, 22], [0, 23], [1, 0], [1, 23], [2, 0], [2, 23], [3, 0], [3, 23], [4, 0], [4, 23], [5, 0], [5, 23], [6, 0], [6, 23], [7, 0], [7, 23], [8, 0], [8, 20], [8, 23], [9, 0], [9, 23], [10, 0], [10, 23], [11, 0], [11, 23], [12, 0], [12, 19], [12, 23], [13, 0], [13, 23], [14, 0], [14, 23], [15, 0], [15, 23], [16, 0], [16, 23], [17, 0], [17, 4], [17, 19], [17, 23], [18, 0], [18, 23], [19, 0], [19, 20], [19, 23], [20, 0], [20, 23], [21, 0], [21, 14], [21, 23], [22, 0], [22, 23], [23, 0], [23, 23], [24, 0], [24, 23], [25, 0], [25, 23], [26, 0], [26, 23], [27, 0], [27, 23], [28, 0], [28, 23], [29, 0], [29, 23], [30, 0], [30, 23], [31, 0], [31, 1], [31, 2], [31, 3], [31, 4], [31, 5], [31, 6], [31, 7], [31, 8], [31, 9], [31, 10], [31, 11], [31, 12], [31, 13], [31, 14], [31, 15], [31, 16], [31, 17], [31, 18], [31, 19], [31, 20], [31, 21], [31, 22], [31, 23]], 'npc': None, 'npc_name': 'Recepcionista da Guilda', 'monsters': {'dummy': [10, 6]}, 'spawns': {'dummy': {'species': 'dummy', 'x': 10, 'y': 6}}, 'portal': None, 'theme': 'interior', 'resources': [[12, 2], [13, 21], [18, 3], [19, 22], [24, 4], [30, 5]], 'decorations': [{'kind': 'barrel', 'x': 29, 'y': 14, 'solid': False}, {'kind': 'shelf', 'x': 18, 'y': 17, 'solid': False}, {'kind': 'chair', 'x': 17, 'y': 13, 'solid': False}, {'kind': 'shelf', 'x': 26, 'y': 5, 'solid': False}, {'kind': 'shelf', 'x': 19, 'y': 21, 'solid': False}, {'kind': 'barrel', 'x': 17, 'y': 19, 'solid': True}, {'kind': 'chair', 'x': 12, 'y': 21, 'solid': False}, {'kind': 'banner', 'x': 19, 'y': 17, 'solid': False}, {'kind': 'table', 'x': 27, 'y': 19, 'solid': False}, {'kind': 'table', 'x': 25, 'y': 14, 'solid': False}, {'kind': 'shelf', 'x': 21, 'y': 17, 'solid': False}, {'kind': 'table', 'x': 9, 'y': 12, 'solid': False}, {'kind': 'chair', 'x': 8, 'y': 20, 'solid': True}, {'kind': 'table', 'x': 27, 'y': 19, 'solid': False}, {'kind': 'barrel', 'x': 12, 'y': 18, 'solid': False}, {'kind': 'banner', 'x': 19, 'y': 11, 'solid': False}, {'kind': 'banner', 'x': 12, 'y': 19, 'solid': True}, {'kind': 'table', 'x': 19, 'y': 20, 'solid': True}, {'kind': 'chair', 'x': 21, 'y': 14, 'solid': True}, {'kind': 'shelf', 'x': 3, 'y': 21, 'solid': False}, {'kind': 'chair', 'x': 17, 'y': 4, 'solid': True}], 'difficulty': 1, 'layout_version': 3, 'template': 'interior:32x24', 'seed': 0}, 'common_a': {'width': 34, 'height': 26, 'walls': [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4], [0, 5], [0, 6], [0, 7], [0, 8], [0, 9], [0, 10], [0, 11], [0, 12], [0, 13], [0, 14], [0, 15], [0, 16], [0, 17], [0, 18], [0, 19], [0, 20], [0, 21], [0, 22], [0, 23], [0, 24], [0, 25], [1, 0], [1, 25], [2, 0], [2, 25], [3, 0], [3, 3], [3, 25], [4, 0], [4, 25], [5, 0], [5, 25], [6, 0], [6, 25], [7, 0], [7, 25], [8, 0], [8, 25], [9, 0], [9, 25], [10, 0], [10, 25], [11, 0], [11, 25], [12, 0], [12, 25], [13, 0], [13, 25], [14, 0], [14, 25], [15, 0], [15, 13], [15, 23], [15, 25], [16, 0], [16, 25], [17, 0], [17, 25], [18, 0], [18, 23], [18, 25], [19, 0], [19, 9], [19, 19], [19, 25], [20, 0], [20, 25], [21, 0], [21, 25], [22, 0], [22, 7], [22, 19], [22, 25], [23, 0], [23, 25], [24, 0], [24, 16], [24, 25], [25, 0], [25, 25], [26, 0], [26, 25], [27, 0], [27, 8], [27, 25], [28, 0], [28, 25], [29, 0], [29, 20], [29, 25], [30, 0], [30, 25], [31, 0], [31, 25], [32, 0], [32, 25], [33, 0], [33, 1], [33, 2], [33, 3], [33, 4], [33, 5], [33, 6], [33, 7], [33, 8], [33, 9], [33, 10], [33, 11], [33, 12], [33, 13], [33, 14], [33, 15], [33, 16], [33, 17], [33, 18], [33, 19], [33, 20], [33, 21], [33, 22], [33, 23], [33, 24], [33, 25]], 'npc': None, 'npc_name': 'Recepcionista da Guilda', 'monsters': {'slime': [5, 6], 'goblin_1': [31, 19], 'slime_2': [10, 22]}, 'spawns': {'slime': {'species': 'slime', 'x': 5, 'y': 6}, 'goblin_1': {'species': 'goblin', 'x': 31, 'y': 19}, 'slime_2': {'species': 'slime', 'x': 10, 'y': 22}}, 'portal': None, 'theme': 'wild_ruins', 'resources': [[10, 5], [11, 24], [16, 6], [28, 8]], 'decorations': [{'kind': 'rock', 'x': 3, 'y': 3, 'solid': True}, {'kind': 'tree', 'x': 6, 'y': 20, 'solid': False}, {'kind': 'ruin', 'x': 17, 'y': 16, 'solid': False}, {'kind': 'tree', 'x': 27, 'y': 8, 'solid': True}, {'kind': 'tree', 'x': 30, 'y': 14, 'solid': False}, {'kind': 'bush', 'x': 24, 'y': 16, 'solid': True}, {'kind': 'tree', 'x': 20, 'y': 5, 'solid': False}, {'kind': 'ruin', 'x': 22, 'y': 19, 'solid': True}, {'kind': 'tree', 'x': 23, 'y': 8, 'solid': False}, {'kind': 'ruin', 'x': 18, 'y': 9, 'solid': False}, {'kind': 'bush', 'x': 19, 'y': 9, 'solid': True}, {'kind': 'tree', 'x': 26, 'y': 16, 'solid': False}, {'kind': 'tree', 'x': 15, 'y': 19, 'solid': False}, {'kind': 'flower', 'x': 7, 'y': 22, 'solid': False}, {'kind': 'ruin', 'x': 5, 'y': 12, 'solid': False}, {'kind': 'flower', 'x': 18, 'y': 23, 'solid': True}, {'kind': 'ruin', 'x': 20, 'y': 17, 'solid': False}, {'kind': 'ruin', 'x': 20, 'y': 3, 'solid': False}, {'kind': 'flower', 'x': 15, 'y': 23, 'solid': True}, {'kind': 'tree', 'x': 4, 'y': 16, 'solid': False}, {'kind': 'ruin', 'x': 26, 'y': 7, 'solid': False}, {'kind': 'ruin', 'x': 13, 'y': 17, 'solid': False}, {'kind': 'ruin', 'x': 24, 'y': 21, 'solid': False}, {'kind': 'bush', 'x': 22, 'y': 7, 'solid': True}, {'kind': 'flower', 'x': 19, 'y': 19, 'solid': True}, {'kind': 'flower', 'x': 29, 'y': 20, 'solid': True}, {'kind': 'tree', 'x': 23, 'y': 19, 'solid': False}, {'kind': 'bush', 'x': 14, 'y': 18, 'solid': False}, {'kind': 'bush', 'x': 17, 'y': 13, 'solid': False}, {'kind': 'flower', 'x': 18, 'y': 15, 'solid': False}, {'kind': 'flower', 'x': 15, 'y': 13, 'solid': True}], 'difficulty': 1, 'layout_version': 3, 'template': 'wild_ruins:34x26', 'seed': 1}, 'common_b': {'width': 34, 'height': 26, 'walls': [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4], [0, 5], [0, 6], [0, 7], [0, 8], [0, 9], [0, 10], [0, 11], [0, 12], [0, 13], [0, 14], [0, 15], [0, 16], [0, 17], [0, 18], [0, 19], [0, 20], [0, 21], [0, 22], [0, 23], [0, 24], [0, 25], [1, 0], [1, 25], [2, 0], [2, 25], [3, 0], [3, 3], [3, 13], [3, 25], [4, 0], [4, 25], [5, 0], [5, 25], [6, 0], [6, 25], [7, 0], [7, 12], [7, 25], [8, 0], [8, 25], [9, 0], [9, 25], [10, 0], [10, 20], [10, 21], [10, 25], [11, 0], [11, 25], [12, 0], [12, 25], [13, 0], [13, 25], [14, 0], [14, 20], [14, 25], [15, 0], [15, 25], [16, 0], [16, 25], [17, 0], [17, 18], [17, 23], [17, 25], [18, 0], [18, 25], [19, 0], [19, 7], [19, 25], [20, 0], [20, 23], [20, 25], [21, 0], [21, 25], [22, 0], [22, 18], [22, 25], [23, 0], [23, 2], [23, 25], [24, 0], [24, 25], [25, 0], [25, 2], [25, 5], [25, 25], [26, 0], [26, 17], [26, 18], [26, 25], [27, 0], [27, 20], [27, 25], [28, 0], [28, 25], [29, 0], [29, 2], [29, 3], [29, 25], [30, 0], [30, 25], [31, 0], [31, 25], [32, 0], [32, 25], [33, 0], [33, 1], [33, 2], [33, 3], [33, 4], [33, 5], [33, 6], [33, 7], [33, 8], [33, 9], [33, 10], [33, 11], [33, 12], [33, 13], [33, 14], [33, 15], [33, 16], [33, 17], [33, 18], [33, 19], [33, 20], [33, 21], [33, 22], [33, 23], [33, 24], [33, 25]], 'npc': None, 'npc_name': 'Recepcionista da Guilda', 'monsters': {'slime': [5, 6], 'goblin_1': [27, 16], 'slime_2': [20, 17]}, 'spawns': {'slime': {'species': 'slime', 'x': 5, 'y': 6}, 'goblin_1': {'species': 'goblin', 'x': 27, 'y': 16}, 'slime_2': {'species': 'slime', 'x': 20, 'y': 17}}, 'portal': None, 'theme': 'crystal_bones', 'resources': [[14, 9], [20, 10], [26, 11], [32, 12]], 'decorations': [{'kind': 'rock', 'x': 3, 'y': 3, 'solid': True}, {'kind': 'rock', 'x': 29, 'y': 3, 'solid': True}, {'kind': 'rock', 'x': 28, 'y': 7, 'solid': False}, {'kind': 'crystal', 'x': 10, 'y': 21, 'solid': True}, {'kind': 'torch', 'x': 20, 'y': 23, 'solid': True}, {'kind': 'rock', 'x': 22, 'y': 14, 'solid': False}, {'kind': 'crystal', 'x': 19, 'y': 16, 'solid': False}, {'kind': 'rock', 'x': 29, 'y': 2, 'solid': True}, {'kind': 'bones', 'x': 31, 'y': 14, 'solid': False}, {'kind': 'crystal', 'x': 19, 'y': 7, 'solid': True}, {'kind': 'rock', 'x': 7, 'y': 12, 'solid': True}, {'kind': 'torch', 'x': 18, 'y': 23, 'solid': False}, {'kind': 'rock', 'x': 27, 'y': 15, 'solid': False}, {'kind': 'torch', 'x': 27, 'y': 20, 'solid': True}, {'kind': 'torch', 'x': 7, 'y': 14, 'solid': False}, {'kind': 'rock', 'x': 22, 'y': 18, 'solid': True}, {'kind': 'rock', 'x': 31, 'y': 17, 'solid': False}, {'kind': 'torch', 'x': 23, 'y': 16, 'solid': False}, {'kind': 'torch', 'x': 13, 'y': 20, 'solid': False}, {'kind': 'rock', 'x': 17, 'y': 23, 'solid': True}, {'kind': 'rock', 'x': 28, 'y': 7, 'solid': False}, {'kind': 'torch', 'x': 26, 'y': 17, 'solid': True}, {'kind': 'crystal', 'x': 17, 'y': 18, 'solid': True}, {'kind': 'bones', 'x': 27, 'y': 12, 'solid': False}, {'kind': 'crystal', 'x': 25, 'y': 5, 'solid': True}, {'kind': 'crystal', 'x': 10, 'y': 20, 'solid': True}, {'kind': 'rock', 'x': 26, 'y': 18, 'solid': True}, {'kind': 'crystal', 'x': 30, 'y': 3, 'solid': False}, {'kind': 'bones', 'x': 3, 'y': 13, 'solid': True}, {'kind': 'crystal', 'x': 23, 'y': 2, 'solid': True}, {'kind': 'bones', 'x': 25, 'y': 2, 'solid': True}, {'kind': 'crystal', 'x': 28, 'y': 7, 'solid': False}, {'kind': 'bones', 'x': 14, 'y': 20, 'solid': True}], 'difficulty': 1, 'layout_version': 3, 'template': 'crystal_bones:34x26', 'seed': 2}, 'combat': {'width': 40, 'height': 28, 'walls': [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4], [0, 5], [0, 6], [0, 7], [0, 8], [0, 9], [0, 10], [0, 11], [0, 12], [0, 13], [0, 14], [0, 15], [0, 16], [0, 17], [0, 18], [0, 19], [0, 20], [0, 21], [0, 22], [0, 23], [0, 24], [0, 25], [0, 26], [0, 27], [1, 0], [1, 27], [2, 0], [2, 27], [3, 0], [3, 3], [3, 27], [4, 0], [4, 12], [4, 27], [5, 0], [5, 27], [6, 0], [6, 27], [7, 0], [7, 27], [8, 0], [8, 27], [9, 0], [9, 27], [10, 0], [10, 13], [10, 27], [11, 0], [11, 18], [11, 27], [12, 0], [12, 27], [13, 0], [13, 27], [14, 0], [14, 27], [15, 0], [15, 27], [16, 0], [16, 27], [17, 0], [17, 27], [18, 0], [18, 27], [19, 0], [19, 27], [20, 0], [20, 5], [20, 27], [21, 0], [21, 27], [22, 0], [22, 2], [22, 7], [22, 27], [23, 0], [23, 27], [24, 0], [24, 27], [25, 0], [25, 21], [25, 27], [26, 0], [26, 27], [27, 0], [27, 27], [28, 0], [28, 27], [29, 0], [29, 27], [30, 0], [30, 27], [31, 0], [31, 27], [32, 0], [32, 27], [33, 0], [33, 8], [33, 27], [34, 0], [34, 27], [35, 0], [35, 27], [36, 0], [36, 27], [37, 0], [37, 12], [37, 27], [38, 0], [38, 27], [39, 0], [39, 1], [39, 2], [39, 3], [39, 4], [39, 5], [39, 6], [39, 7], [39, 8], [39, 9], [39, 10], [39, 11], [39, 12], [39, 13], [39, 14], [39, 15], [39, 16], [39, 17], [39, 18], [39, 19], [39, 20], [39, 21], [39, 22], [39, 23], [39, 24], [39, 25], [39, 26], [39, 27]], 'npc': None, 'npc_name': 'Recepcionista da Guilda', 'monsters': {'slime': [5, 6], 'goblin_1': [21, 12], 'slime_2': [27, 13], 'goblin_3': [14, 25], 'slime_4': [32, 17], 'goblin_5': [26, 7]}, 'spawns': {'slime': {'species': 'slime', 'x': 5, 'y': 6}, 'goblin_1': {'species': 'goblin', 'x': 21, 'y': 12}, 'slime_2': {'species': 'slime', 'x': 27, 'y': 13}, 'goblin_3': {'species': 'goblin', 'x': 14, 'y': 25}, 'slime_4': {'species': 'slime', 'x': 32, 'y': 17}, 'goblin_5': {'species': 'goblin', 'x': 26, 'y': 7}}, 'portal': None, 'theme': 'abandoned_wood', 'resources': [[12, 12], [18, 13], [24, 14], [30, 15], [36, 16]], 'decorations': [{'kind': 'rock', 'x': 3, 'y': 3, 'solid': True}, {'kind': 'shelf', 'x': 17, 'y': 20, 'solid': False}, {'kind': 'barrel', 'x': 32, 'y': 22, 'solid': False}, {'kind': 'crate', 'x': 32, 'y': 10, 'solid': False}, {'kind': 'torch', 'x': 32, 'y': 19, 'solid': False}, {'kind': 'crate', 'x': 27, 'y': 22, 'solid': False}, {'kind': 'barrel', 'x': 11, 'y': 18, 'solid': True}, {'kind': 'torch', 'x': 32, 'y': 21, 'solid': False}, {'kind': 'torch', 'x': 29, 'y': 14, 'solid': False}, {'kind': 'crate', 'x': 10, 'y': 13, 'solid': True}, {'kind': 'torch', 'x': 33, 'y': 8, 'solid': True}, {'kind': 'torch', 'x': 21, 'y': 15, 'solid': False}, {'kind': 'crate', 'x': 24, 'y': 19, 'solid': False}, {'kind': 'barrel', 'x': 23, 'y': 23, 'solid': False}, {'kind': 'crate', 'x': 19, 'y': 21, 'solid': False}, {'kind': 'barrel', 'x': 22, 'y': 19, 'solid': False}, {'kind': 'shelf', 'x': 15, 'y': 22, 'solid': False}, {'kind': 'torch', 'x': 20, 'y': 5, 'solid': True}, {'kind': 'torch', 'x': 7, 'y': 13, 'solid': False}, {'kind': 'barrel', 'x': 20, 'y': 15, 'solid': False}, {'kind': 'barrel', 'x': 4, 'y': 21, 'solid': False}, {'kind': 'shelf', 'x': 26, 'y': 24, 'solid': False}, {'kind': 'shelf', 'x': 34, 'y': 9, 'solid': False}, {'kind': 'crate', 'x': 8, 'y': 21, 'solid': False}, {'kind': 'crate', 'x': 28, 'y': 11, 'solid': False}, {'kind': 'crate', 'x': 4, 'y': 12, 'solid': True}, {'kind': 'torch', 'x': 26, 'y': 14, 'solid': False}, {'kind': 'shelf', 'x': 37, 'y': 5, 'solid': False}, {'kind': 'crate', 'x': 29, 'y': 22, 'solid': False}, {'kind': 'shelf', 'x': 21, 'y': 15, 'solid': False}, {'kind': 'torch', 'x': 37, 'y': 12, 'solid': True}, {'kind': 'crate', 'x': 22, 'y': 2, 'solid': True}, {'kind': 'torch', 'x': 5, 'y': 22, 'solid': False}, {'kind': 'shelf', 'x': 24, 'y': 23, 'solid': False}, {'kind': 'barrel', 'x': 33, 'y': 2, 'solid': False}, {'kind': 'shelf', 'x': 25, 'y': 10, 'solid': False}, {'kind': 'shelf', 'x': 22, 'y': 7, 'solid': True}, {'kind': 'torch', 'x': 25, 'y': 21, 'solid': True}], 'difficulty': 1, 'layout_version': 3, 'template': 'abandoned_wood:40x28', 'seed': 3}, 'boss': {'width': 34, 'height': 26, 'walls': [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4], [0, 5], [0, 6], [0, 7], [0, 8], [0, 9], [0, 10], [0, 11], [0, 12], [0, 13], [0, 14], [0, 15], [0, 16], [0, 17], [0, 18], [0, 19], [0, 20], [0, 21], [0, 22], [0, 23], [0, 24], [0, 25], [1, 0], [1, 25], [2, 0], [2, 25], [3, 0], [3, 25], [4, 0], [4, 25], [5, 0], [5, 25], [6, 0], [6, 25], [7, 0], [7, 25], [8, 0], [8, 20], [8, 25], [9, 0], [9, 25], [10, 0], [10, 25], [11, 0], [11, 25], [12, 0], [12, 20], [12, 25], [13, 0], [13, 25], [14, 0], [14, 25], [15, 0], [15, 25], [16, 0], [16, 25], [17, 0], [17, 4], [17, 19], [17, 25], [18, 0], [18, 25], [19, 0], [19, 25], [20, 0], [20, 22], [20, 25], [21, 0], [21, 25], [22, 0], [22, 25], [23, 0], [23, 25], [24, 0], [24, 25], [25, 0], [25, 25], [26, 0], [26, 25], [27, 0], [27, 25], [28, 0], [28, 19], [28, 25], [29, 0], [29, 25], [30, 0], [30, 25], [31, 0], [31, 25], [32, 0], [32, 25], [33, 0], [33, 1], [33, 2], [33, 3], [33, 4], [33, 5], [33, 6], [33, 7], [33, 8], [33, 9], [33, 10], [33, 11], [33, 12], [33, 13], [33, 14], [33, 15], [33, 16], [33, 17], [33, 18], [33, 19], [33, 20], [33, 21], [33, 22], [33, 23], [33, 24], [33, 25]], 'npc': None, 'npc_name': 'Recepcionista da Guilda', 'monsters': {'boss': [12, 8]}, 'spawns': {'boss': {'species': 'boss', 'x': 12, 'y': 8}}, 'portal': None, 'theme': 'moss_stone', 'resources': [[12, 2], [13, 21], [18, 3], [19, 22], [24, 4], [25, 23]], 'decorations': [{'kind': 'statue', 'x': 29, 'y': 14, 'solid': False}, {'kind': 'torch', 'x': 18, 'y': 17, 'solid': False}, {'kind': 'moss', 'x': 17, 'y': 13, 'solid': False}, {'kind': 'torch', 'x': 26, 'y': 5, 'solid': False}, {'kind': 'moss', 'x': 31, 'y': 19, 'solid': False}, {'kind': 'torch', 'x': 25, 'y': 4, 'solid': False}, {'kind': 'statue', 'x': 17, 'y': 19, 'solid': True}, {'kind': 'moss', 'x': 12, 'y': 21, 'solid': False}, {'kind': 'torch', 'x': 19, 'y': 17, 'solid': False}, {'kind': 'rock', 'x': 3, 'y': 19, 'solid': False}, {'kind': 'rock', 'x': 25, 'y': 14, 'solid': False}, {'kind': 'torch', 'x': 21, 'y': 17, 'solid': False}, {'kind': 'rock', 'x': 9, 'y': 12, 'solid': False}, {'kind': 'moss', 'x': 8, 'y': 20, 'solid': True}, {'kind': 'rock', 'x': 27, 'y': 19, 'solid': False}, {'kind': 'statue', 'x': 12, 'y': 18, 'solid': False}, {'kind': 'torch', 'x': 19, 'y': 11, 'solid': False}, {'kind': 'torch', 'x': 28, 'y': 19, 'solid': True}, {'kind': 'statue', 'x': 16, 'y': 4, 'solid': False}, {'kind': 'moss', 'x': 12, 'y': 20, 'solid': True}, {'kind': 'torch', 'x': 3, 'y': 21, 'solid': False}, {'kind': 'moss', 'x': 17, 'y': 4, 'solid': True}, {'kind': 'rock', 'x': 30, 'y': 6, 'solid': False}, {'kind': 'torch', 'x': 30, 'y': 19, 'solid': False}, {'kind': 'statue', 'x': 18, 'y': 9, 'solid': False}, {'kind': 'torch', 'x': 20, 'y': 10, 'solid': False}, {'kind': 'statue', 'x': 4, 'y': 12, 'solid': False}, {'kind': 'moss', 'x': 20, 'y': 22, 'solid': True}], 'difficulty': 'EXTREMA', 'layout_version': 3, 'template': 'moss_stone:34x26', 'seed': 0, 'recommended_level': 3, 'recommended_group': 4}, 'secret': {'width': 34, 'height': 26, 'walls': [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4], [0, 5], [0, 6], [0, 7], [0, 8], [0, 9], [0, 10], [0, 11], [0, 12], [0, 13], [0, 14], [0, 15], [0, 16], [0, 17], [0, 18], [0, 19], [0, 20], [0, 21], [0, 22], [0, 23], [0, 24], [0, 25], [1, 0], [1, 25], [2, 0], [2, 25], [3, 0], [3, 13], [3, 25], [4, 0], [4, 25], [5, 0], [5, 25], [6, 0], [6, 25], [7, 0], [7, 12], [7, 25], [8, 0], [8, 25], [9, 0], [9, 25], [10, 0], [10, 20], [10, 21], [10, 25], [11, 0], [11, 25], [12, 0], [12, 25], [13, 0], [13, 25], [14, 0], [14, 20], [14, 25], [15, 0], [15, 25], [16, 0], [16, 25], [17, 0], [17, 18], [17, 23], [17, 25], [18, 0], [18, 25], [19, 0], [19, 7], [19, 25], [20, 0], [20, 23], [20, 25], [21, 0], [21, 25], [22, 0], [22, 18], [22, 25], [23, 0], [23, 2], [23, 25], [24, 0], [24, 25], [25, 0], [25, 2], [25, 5], [25, 25], [26, 0], [26, 17], [26, 18], [26, 25], [27, 0], [27, 20], [27, 25], [28, 0], [28, 25], [29, 0], [29, 2], [29, 3], [29, 25], [30, 0], [30, 25], [31, 0], [31, 25], [32, 0], [32, 25], [33, 0], [33, 1], [33, 2], [33, 3], [33, 4], [33, 5], [33, 6], [33, 7], [33, 8], [33, 9], [33, 10], [33, 11], [33, 12], [33, 13], [33, 14], [33, 15], [33, 16], [33, 17], [33, 18], [33, 19], [33, 20], [33, 21], [33, 22], [33, 23], [33, 24], [33, 25]], 'npc': None, 'npc_name': 'Recepcionista da Guilda', 'monsters': {'warden': [10, 7]}, 'spawns': {'warden': {'species': 'warden', 'x': 10, 'y': 7}}, 'portal': None, 'theme': 'crystal_bones', 'resources': [[14, 9], [20, 10], [26, 11], [32, 12]], 'decorations': [{'kind': 'rock', 'x': 29, 'y': 3, 'solid': True}, {'kind': 'rock', 'x': 28, 'y': 7, 'solid': False}, {'kind': 'crystal', 'x': 10, 'y': 21, 'solid': True}, {'kind': 'torch', 'x': 20, 'y': 23, 'solid': True}, {'kind': 'rock', 'x': 22, 'y': 14, 'solid': False}, {'kind': 'crystal', 'x': 19, 'y': 16, 'solid': False}, {'kind': 'rock', 'x': 29, 'y': 2, 'solid': True}, {'kind': 'bones', 'x': 31, 'y': 14, 'solid': False}, {'kind': 'crystal', 'x': 19, 'y': 7, 'solid': True}, {'kind': 'rock', 'x': 7, 'y': 12, 'solid': True}, {'kind': 'torch', 'x': 18, 'y': 23, 'solid': False}, {'kind': 'rock', 'x': 27, 'y': 15, 'solid': False}, {'kind': 'torch', 'x': 27, 'y': 20, 'solid': True}, {'kind': 'torch', 'x': 7, 'y': 14, 'solid': False}, {'kind': 'rock', 'x': 22, 'y': 18, 'solid': True}, {'kind': 'rock', 'x': 31, 'y': 17, 'solid': False}, {'kind': 'torch', 'x': 23, 'y': 16, 'solid': False}, {'kind': 'torch', 'x': 13, 'y': 20, 'solid': False}, {'kind': 'rock', 'x': 17, 'y': 23, 'solid': True}, {'kind': 'rock', 'x': 28, 'y': 7, 'solid': False}, {'kind': 'torch', 'x': 26, 'y': 17, 'solid': True}, {'kind': 'crystal', 'x': 17, 'y': 18, 'solid': True}, {'kind': 'bones', 'x': 27, 'y': 12, 'solid': False}, {'kind': 'crystal', 'x': 25, 'y': 5, 'solid': True}, {'kind': 'crystal', 'x': 10, 'y': 20, 'solid': True}, {'kind': 'rock', 'x': 26, 'y': 18, 'solid': True}, {'kind': 'crystal', 'x': 30, 'y': 3, 'solid': False}, {'kind': 'bones', 'x': 3, 'y': 13, 'solid': True}, {'kind': 'crystal', 'x': 23, 'y': 2, 'solid': True}, {'kind': 'bones', 'x': 25, 'y': 2, 'solid': True}, {'kind': 'crystal', 'x': 28, 'y': 7, 'solid': False}, {'kind': 'bones', 'x': 14, 'y': 20, 'solid': True}], 'difficulty': 'PERIGOSA', 'layout_version': 3, 'template': 'crystal_bones:34x26', 'seed': 2, 'recommended_level': 8, 'enemy_level': 8, 'enemy_hp': 90, 'enemy_attack': 14}}

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('enemy_instances',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('character_id', sa.Integer(), nullable=False),
    sa.Column('room_id', sa.String(length=80), nullable=False),
    sa.Column('generation', sa.Integer(), nullable=False),
    sa.Column('spawn_key', sa.String(length=40), nullable=False),
    sa.Column('species', sa.String(length=20), nullable=False),
    sa.Column('state', sa.String(length=20), nullable=False),
    sa.Column('hp', sa.Integer(), nullable=False),
    sa.Column('max_hp', sa.Integer(), nullable=False),
    sa.Column('level', sa.Integer(), nullable=False),
    sa.Column('attack', sa.Integer(), nullable=False),
    sa.Column('defense', sa.Integer(), nullable=False),
    sa.Column('x', sa.Integer(), nullable=False),
    sa.Column('y', sa.Integer(), nullable=False),
    sa.Column('home_x', sa.Integer(), nullable=False),
    sa.Column('home_y', sa.Integer(), nullable=False),
    sa.Column('ai_state', sa.String(length=20), nullable=False),
    sa.Column('moved_at', sa.DateTime(), nullable=False),
    sa.Column('death_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("state IN ('ALIVE','IN_COMBAT','DYING','DEAD')"),
    sa.CheckConstraint('hp >= 0 AND max_hp > 0'),
    sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ),
    sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('character_id', 'room_id', 'generation', 'spawn_key')
    )
    op.create_index(op.f('ix_enemy_instances_character_id'), 'enemy_instances', ['character_id'], unique=False)
    op.add_column('battles', sa.Column('enemy_id', sa.Integer(), nullable=True))
    op.create_index('uq_enemy_victory', 'battles', ['enemy_id'], unique=True, postgresql_where=sa.text("status = 'won' AND enemy_id IS NOT NULL"))
    op.create_foreign_key(None, 'battles', 'enemy_instances', ['enemy_id'], ['id'])
    op.add_column('item_definitions', sa.Column('stackable', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('item_definitions', sa.Column('max_stack_size', sa.Integer(), server_default='1', nullable=False))
    op.add_column('item_definitions', sa.Column('description', sa.String(length=200), server_default='', nullable=False))
    op.add_column('room_states', sa.Column('generation', sa.Integer(), server_default='0', nullable=False))
    # ### end Alembic commands ###

    op.create_check_constraint('ck_definition_stack','item_definitions','max_stack_size > 0')
    conn=op.get_bind()
    conn.execute(sa.text("UPDATE item_definitions SET stackable=true,max_stack_size=99 WHERE kind IN ('material','consumable','resource')"))
    conn.execute(sa.text("UPDATE item_definitions SET description='Material obtido em expedições; empilhável até 99.' WHERE id='crystal'"))
    conn.execute(sa.text("UPDATE item_definitions SET description='Equipamento individual. Ataque +3.' WHERE id='sword'"))
    # Consolidate only compatible inventory materials, preserving quantities and equipment IDs.
    groups=conn.execute(sa.text("SELECT DISTINCT owner,definition,location FROM items JOIN item_definitions ON definition=item_definitions.id WHERE stackable=true AND equipped=false AND location='inventory'" )).mappings().all()
    for group in groups:
        params=dict(group)
        rows=conn.execute(sa.text("SELECT id,quantity FROM items WHERE owner=:owner AND definition=:definition AND location=:location AND equipped=false ORDER BY id"),params).mappings().all()
        cap=conn.execute(sa.text("SELECT max_stack_size FROM item_definitions WHERE id=:definition"),params).scalar_one()
        total=sum(row['quantity'] for row in rows)
        for row in rows:
            if total:
                amount=min(cap,total);total-=amount
                conn.execute(sa.text("UPDATE items SET quantity=:q WHERE id=:id"),{'q':amount,'id':row['id']})
            else:conn.execute(sa.text("DELETE FROM items WHERE id=:id"),{'id':row['id']})
        while total:
            amount=min(cap,total);total-=amount
            conn.execute(sa.text("INSERT INTO items(owner,definition,location,equipped,quantity) VALUES (:owner,:definition,:location,false,:q)"),{**params,'q':amount})
    rooms=sa.table('rooms',sa.column('id',sa.String),sa.column('data',sa.JSON))
    for room_id,data in CONTENT.items():
        occupied=conn.execute(sa.text("SELECT x,y FROM characters WHERE room_id=:room"),{'room':room_id}).all()
        safe={(x+dx,y+dy) for x,y in occupied for dx,dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]}
        data={**data,'walls':[p for p in data['walls'] if tuple(p) not in safe]}
        conn.execute(rooms.update().where(rooms.c.id==room_id).values(data=data))
    for row in conn.execute(sa.text("SELECT id,seed FROM rooms WHERE kind='PROCEDURAL' AND floor_id=1")).mappings().all():
        data=generate('PROCEDURAL',row['seed'])
        occupied=conn.execute(sa.text("SELECT x,y FROM characters WHERE room_id=:id"),dict(row)).all()
        safe={(x+dx,y+dy) for x,y in occupied for dx,dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]}
        data['walls']=[p for p in data['walls'] if tuple(p) not in safe]
        conn.execute(rooms.update().where(rooms.c.id==row['id']).values(data=data))
    for src,dst,x,y in [('city1','common_a',50,18),('guild','training',35,10),('common_a','common_b',32,13),('common_b','combat',32,13),('combat','boss',38,14)]:
        conn.execute(sa.text("UPDATE room_connections SET x=:x,y=:y WHERE source=:src AND target=:dst"),dict(src=src,dst=dst,x=x,y=y))

def downgrade():
    # Content, quantities and deaths are retained; never undo player progress.
    op.drop_constraint("ck_definition_stack","item_definitions",type_="check")
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('room_states', 'generation')
    op.drop_column('item_definitions', 'description')
    op.drop_column('item_definitions', 'max_stack_size')
    op.drop_column('item_definitions', 'stackable')
    op.drop_constraint(None, 'battles', type_='foreignkey')
    op.drop_index('uq_enemy_victory', table_name='battles', postgresql_where=sa.text("status = 'won' AND enemy_id IS NOT NULL"))
    op.drop_column('battles', 'enemy_id')
    op.drop_index(op.f('ix_enemy_instances_character_id'), table_name='enemy_instances')
    op.drop_table('enemy_instances')
    # ### end Alembic commands ###
