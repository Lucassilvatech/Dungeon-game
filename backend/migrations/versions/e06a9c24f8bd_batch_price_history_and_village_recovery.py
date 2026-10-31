"""Extend price-history identity for batches; relocate recovery without deleting state."""

from alembic import op
import sqlalchemy as sa
import json

revision = "e06a9c24f8bd"
down_revision = "d91e2ab604c7"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SELECT pg_advisory_xact_lock(7312027)")
    op.execute("SELECT pg_advisory_xact_lock(7312030)")
    # Retain every existing request/policy pair and row. No foreign keys point to
    # this former single-column primary key; the parent AdminOperation FK stays.
    op.drop_constraint(
        "guild_price_history_pkey", "guild_price_history", type_="primary"
    )
    op.create_primary_key(
        "guild_price_history_pkey", "guild_price_history", ["request_id", "policy_key"]
    )
    db = op.get_bind()
    data = db.execute(
        sa.text("SELECT data FROM rooms WHERE id='city1' FOR UPDATE")
    ).scalar()
    if data:
        if data.get("npc") and data.get("npc_role") != "recovery":
            raise RuntimeError(
                "Custom city NPC: review before installing recovery tent"
            )
        data = {
            **data,
            "npc": [5, 30],
            "npc_name": "Figura encapuzada",
            "npc_role": "recovery",
            "recovery_site_version": 1,
            "decorations": [
                *[
                    d
                    for d in data.get("decorations", [])
                    if d.get("kind") != "recovery_tent"
                ],
                {"kind": "recovery_tent", "x": 3, "y": 27, "width": 5, "height": 5},
            ],
        }
        db.execute(
            sa.text("UPDATE rooms SET data=CAST(:data AS json) WHERE id='city1'"),
            {"data": json.dumps(data)},
        )
    if db.execute(
        sa.text(
            "SELECT count(*) FROM characters c JOIN battles b ON b.character_id=c.id AND b.status='active' WHERE c.room_id='recovery_hall'"
        )
    ).scalar():
        raise RuntimeError(
            "Unexpected active combat in old recovery service; resolve before relocation"
        )
    # Retain old connections/room/visits as archived records, never delete IDs.
    for row in db.execute(
        sa.text("SELECT id,data FROM rooms WHERE id='recovery_hall'")
    ):
        archived = {
            **row.data,
            "archived_recovery_hall": True,
            "relocated_to": "city1",
            "npc": None,
            "npc_role": "archived",
        }
        db.execute(
            sa.text("UPDATE rooms SET data=CAST(:data AS json) WHERE id=:id"),
            {"data": json.dumps(archived), "id": row.id},
        )
    # Links are retained as rows; runtime filters these historical edges.
    moved = list(
        db.execute(
            sa.text(
                "SELECT id,room_id,x,y FROM characters WHERE room_id='recovery_hall' OR (room_id='city1' AND x=5 AND y=30) FOR UPDATE"
            )
        )
    )
    for c in moved:
        db.execute(
            sa.text(
                "UPDATE characters SET room_id='city1',floor=1,x=5,y=31 WHERE id=:id"
            ),
            {"id": c.id},
        )
        db.execute(
            sa.text(
                "INSERT INTO world_events(key,kind,payload,processed) VALUES(:key,'RECOVERY_SERVICE_RELOCATED',CAST(:payload AS json),true)"
            ),
            {
                "key": f"recovery-relocation-v1:{c.id}",
                "payload": json.dumps(
                    {
                        "character": c.id,
                        "from": c.room_id,
                        "before": [c.x, c.y],
                        "to": "city1",
                        "position": [5, 31],
                    }
                ),
            },
        )


def downgrade():
    raise RuntimeError(
        "Preserve batch audit history and recovery relocation; restore a reviewed backup"
    )
