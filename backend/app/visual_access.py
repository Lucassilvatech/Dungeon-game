"""One-way spatial repair: clear legacy decorative city collisions, never structural walls.
No characters, encounters, resources or financial records are changed.
"""

from copy import deepcopy

SCATTER = frozenset(
    {"tree", "flower", "barrel", "bench", "well", "bush", "rock", "crate"}
)


def repair_city_access(data):
    result = deepcopy(data)
    if not all(k in data for k in ("width", "height", "walls")):
        return result, []
    w, h = data["width"], data["height"]
    structural = {
        (x, y)
        for b in data.get("buildings", [])
        for x in range(b["x"], b["x"] + b["width"])
        for y in range(b["y"], b["y"] + b["height"])
    }
    walls = {tuple(p) for p in data["walls"]}
    removed = []
    for d in result.get("decorations", []):
        p = (d["x"], d["y"])
        if (
            d.get("solid")
            and d["kind"] in SCATTER
            and d.get("width", 1) == 1
            and d.get("height", 1) == 1
            and p in walls
            and p not in structural
            and 0 < p[0] < w - 1
            and 0 < p[1] < h - 1
        ):
            walls.remove(p)
            removed.append(list(p))
            d["solid"] = False
            d["visual_only"] = True
    result["walls"] = [list(p) for p in sorted(walls)]
    result["visual_access_version"] = 1
    return result, sorted(removed)
