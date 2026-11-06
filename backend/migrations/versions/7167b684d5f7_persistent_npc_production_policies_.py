"""persistent npc production policies recipes and market revisions"""

from alembic import op
import sqlalchemy as sa

revision = "7167b684d5f7"
down_revision = "e06a9c24f8bd"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SELECT pg_advisory_xact_lock(7312027)")
    op.execute("SELECT pg_advisory_xact_lock(7312030)")
    op.create_table(
        "market_revisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("actor", sa.String(length=80), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "npc_profiles",
        sa.Column("id", sa.String(length=24), nullable=False),
        sa.Column("account_id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("production_enabled", sa.Boolean(), nullable=False),
        sa.Column("purchase_enabled", sa.Boolean(), nullable=False),
        sa.Column("sale_enabled", sa.Boolean(), nullable=False),
        sa.Column("fixed_margin", sa.Numeric(), nullable=False),
        sa.Column("factors", sa.JSON(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("last_cycle", sa.Numeric(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("fixed_margin >= 0 AND revision > 0 AND last_cycle >= -1"),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["lunar_accounts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id"),
    )
    op.create_table(
        "npc_inventory_policies",
        sa.Column("npc_id", sa.String(length=24), nullable=False),
        sa.Column("definition_id", sa.String(length=30), nullable=False),
        sa.Column("capacity", sa.Numeric(), nullable=False),
        sa.Column("reorder_point", sa.Numeric(), nullable=False),
        sa.Column("order_quantity", sa.Numeric(), nullable=False),
        sa.Column("target_stock", sa.Numeric(), nullable=False),
        sa.Column("minimum_lot_size", sa.Numeric(), nullable=False),
        sa.Column("order_step", sa.Numeric(), nullable=False),
        sa.Column("production_enabled", sa.Boolean(), nullable=False),
        sa.Column("buy_enabled", sa.Boolean(), nullable=False),
        sa.Column("sell_enabled", sa.Boolean(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "capacity >= 0 AND reorder_point >= 0 AND reorder_point <= capacity AND target_stock >= 0 AND target_stock <= capacity AND order_quantity > 0 AND minimum_lot_size > 0 AND order_step > 0 AND revision > 0"
        ),
        sa.ForeignKeyConstraint(
            ["definition_id"],
            ["item_definitions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["npc_id"],
            ["npc_profiles.id"],
        ),
        sa.PrimaryKeyConstraint("npc_id", "definition_id"),
    )
    op.create_table(
        "npc_recipes",
        sa.Column("result_id", sa.String(length=30), nullable=False),
        sa.Column("npc_id", sa.String(length=24), nullable=False),
        sa.Column("ingredients", sa.JSON(), nullable=False),
        sa.Column("factor_key", sa.String(length=24), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["npc_id"],
            ["npc_profiles.id"],
        ),
        sa.ForeignKeyConstraint(
            ["result_id"],
            ["item_definitions.id"],
        ),
        sa.PrimaryKeyConstraint("result_id"),
    )
    op.add_column(
        "item_definitions",
        sa.Column("equipment_slot", sa.String(length=20), nullable=True),
    )
    op.execute(
        """CREATE FUNCTION npc_history_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'NPC economic history is immutable'; END $$"""
    )
    op.execute(
        "CREATE TRIGGER market_revision_immutable BEFORE UPDATE OR DELETE ON market_revisions FOR EACH ROW EXECUTE FUNCTION npc_history_immutable()"
    )
    op.execute(
        """CREATE TRIGGER npc_event_immutable BEFORE UPDATE OR DELETE ON world_events
    FOR EACH ROW WHEN (OLD.kind IN ('NPC_INITIAL_STOCK','NPC_PRODUCTION','NPC_PURCHASE','NPC_SALE','NPC_RESTOCK_REQUEST','MARKET_PRICE_UPDATE','RECIPE_PRICE_RECALCULATED','NPC_CONFIG_UPDATED','NPC_INVENTORY_ADJUSTED'))
    EXECUTE FUNCTION npc_history_immutable()"""
    )
    # ### end Alembic commands ###


def downgrade():
    raise RuntimeError(
        "Preserve NPC inventory, market revisions and audited history; restore a reviewed backup"
    )
