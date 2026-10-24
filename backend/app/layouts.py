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
