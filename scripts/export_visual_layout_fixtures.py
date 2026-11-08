"""Export real deterministic layout templates for independent frontend placement audit.
No database writes or runtime state; CLI output is a test fixture only.
"""

import argparse
import json
from pathlib import Path
from app.layouts import generate
from app.rooms import EDGES
from app.recovery_site import patch
from app.village_sites import SITES, interior, patch_city

parser = argparse.ArgumentParser()
parser.add_argument("output")
args = parser.parse_args()
fixtures = []
for kind in [
    "CITY",
    "GUILD",
    "TRAINING",
    "COMMON",
    "COMBAT",
    "PROCEDURAL",
    "BOSS",
    "SECRET_DUNGEON",
    "BUILDING_INTERIOR",
    "SPECIAL",
]:
    for seed in range(25):
        data = generate(kind, seed)
        room_id = {
            "CITY": "city1",
            "GUILD": "guild",
            "TRAINING": "training",
            "COMMON": "common_a",
            "COMBAT": "combat",
            "BOSS": "boss",
            "SECRET_DUNGEON": "secret",
        }.get(kind, kind.lower() + str(seed))
        exits = [
            {"x": p[0], "y": p[1], "id": i + 1}
            for i, (a, b, p, q) in enumerate(EDGES)
            if a == room_id
        ] + [
            {"x": q[0], "y": q[1], "id": 100 + i}
            for i, (a, b, p, q) in enumerate(EDGES)
            if b == room_id
        ]
        if kind == "CITY":
            data = patch(data)
            data = patch_city(data)
            exits += [
                {
                    "id": 200 + i,
                    "x": site["door"][0],
                    "y": site["door"][1],
                    "target_id": site["room"],
                }
                for i, site in enumerate(SITES.values())
            ]
        data.update(
            gather_nodes=[
                {"x": x, "y": y, "definition": "herb", "remaining": 1, "enabled": True}
                for x, y in data.get("resources", [])
            ],
            lunar_resources=[],
        )
        fixtures.append(
            {
                "room": {
                    "id": room_id,
                    "kind": kind,
                    "exits": exits,
                    "safe": kind in ("CITY", "GUILD"),
                },
                "map": data,
            }
        )
for id, site in SITES.items():
    fixtures.append(
        {
            "room": {
                "id": site["room"],
                "kind": "BUILDING_INTERIOR",
                "safe": True,
                "exits": [{"id": 300, "x": 10, "y": 15}],
            },
            "map": interior(id),
        }
    )
Path(args.output).write_text(json.dumps(fixtures))
print(f"Exported {len(fixtures)} real templates including all four service interiors")
