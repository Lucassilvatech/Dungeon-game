"""Add finite Guild pricing/history/receipts without touching any physical balance."""

from alembic import op
import sqlalchemy as sa

revision = "d91e2ab604c7"
down_revision = "ca343e37b4ca"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SELECT pg_advisory_xact_lock(7312027)")
    op.execute("SELECT pg_advisory_xact_lock(7312030)")
    op.drop_constraint("npc_stocks_sale_weight_mg_check", "npc_stocks", type_="check")
    op.create_check_constraint(
        "npc_stocks_sale_weight_mg_check", "npc_stocks", "sale_weight_mg >= 0"
    )
    op.create_table(
        "guild_item_policies",
        sa.Column(
            "definition_id",
            sa.String(30),
            sa.ForeignKey("item_definitions.id"),
            primary_key=True,
        ),
        sa.Column("buy_price_units", sa.Numeric(scale=0), nullable=False),
        sa.Column("sell_price_units", sa.Numeric(scale=0), nullable=False),
        sa.Column("buy_enabled", sa.Boolean(), nullable=False),
        sa.Column("sell_enabled", sa.Boolean(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.String(80), nullable=False),
        sa.CheckConstraint(
            "buy_price_units >= 0 AND sell_price_units >= 0 AND revision >= 1"
        ),
    )
    # Preserve the old buy valuation. Enable legacy sale prices only when every
    # Guild stack agrees on a whole-unit price; ambiguous sale remains disabled.
    op.execute("""INSERT INTO guild_item_policies
        SELECT d.id, greatest(coalesce(d.base_value,0),0), CASE WHEN coalesce(s.valid,false) THEN s.price ELSE 0 END,
               coalesce(d.base_value,0)>0 AND d.death_transferable AND d.id<>'sword',
               coalesce(s.valid,false) AND d.death_transferable AND d.id<>'sword',
               1, CURRENT_TIMESTAMP, 'migration:d91e2ab604c7'
        FROM item_definitions d LEFT JOIN (
            SELECT i.definition,
                min(n.sale_weight_mg / (i.quantity*1000)) AS price,
                count(DISTINCT n.sale_weight_mg / (i.quantity*1000))=1
                AND bool_and(mod(n.sale_weight_mg,i.quantity*1000)=0 AND n.sale_weight_mg>0) AS valid
            FROM npc_stocks n JOIN items i ON i.id=n.item_id
            WHERE n.account_id='guild' AND i.location='npc' AND i.owner IS NULL
            GROUP BY i.definition
        ) s ON s.definition=d.id""")
    op.create_table(
        "guild_price_history",
        sa.Column(
            "request_id",
            sa.String(36),
            sa.ForeignKey("admin_operations.id"),
            primary_key=True,
        ),
        sa.Column("policy_key", sa.String(80), nullable=False),
        sa.Column("before", sa.JSON(), nullable=False),
        sa.Column("after", sa.JSON(), nullable=False),
        sa.Column(
            "actor_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False
        ),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_guild_price_history_policy_key", "guild_price_history", ["policy_key"]
    )
    op.create_table(
        "guild_trade_receipts",
        sa.Column("key", sa.String(160), primary_key=True),
        sa.Column(
            "character_id", sa.Integer(), sa.ForeignKey("characters.id"), nullable=False
        ),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_guild_trade_receipts_character_id", "guild_trade_receipts", ["character_id"]
    )
    op.execute(
        """CREATE FUNCTION protect_guild_history() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Guild commercial history is append-only'; END; $$"""
    )
    for table in ("guild_price_history", "guild_trade_receipts"):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION protect_guild_history()"
        )


def downgrade():
    raise RuntimeError(
        "Preserve commercial receipts/history; restore a reviewed backup instead"
    )
