"""Clear only old decorative city collisions; preserve all persistent gameplay/economy."""

from alembic import op
import sqlalchemy as sa
import hashlib
import json

revision = "65a7c9e21b04"
down_revision = "7167b684d5f7"
branch_labels = None
depends_on = None

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


def upgrade():
    db = op.get_bind()
    for row in list(
        db.execute(
            sa.text(
                "SELECT id,data FROM rooms WHERE kind='CITY' ORDER BY id FOR UPDATE"
            )
        )
    ):
        if row.data.get("visual_access_version") == 1 or not all(
            k in row.data for k in ("width", "height", "walls")
        ):
            continue
        updated, removed = repair_city_access(row.data)
        if not removed:
            continue
        db.execute(
            sa.text("UPDATE rooms SET data=CAST(:data AS json) WHERE id=:id"),
            {"id": row.id, "data": json.dumps(updated)},
        )
        key = "visual-access-v1:" + hashlib.sha256(row.id.encode()).hexdigest()[:24]
        payload = {
            "room": row.id,
            "removed_decorative_wall_tiles": removed,
            "reason": "Clear legacy scatter from village circulation; preserve structure and all persistent actors/economy",
        }
        db.execute(
            sa.text(
                "INSERT INTO world_events(key,kind,payload,processed) VALUES(:key,'VISUAL_ACCESS_REPAIRED',CAST(:payload AS json),true) ON CONFLICT(key) DO NOTHING"
            ),
            {"key": key, "payload": json.dumps(payload)},
        )


def downgrade():
    # Data-only accessibility fix is intentionally retained. Restoring obsolete
    # obstacles could trap characters who have since walked onto cleared cells.
    pass
