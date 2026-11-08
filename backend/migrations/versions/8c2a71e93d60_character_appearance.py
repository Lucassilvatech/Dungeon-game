"""Add independent cosmetic appearance; preserve all legacy characters and equipment."""

from alembic import op
import sqlalchemy as sa

revision = "8c2a71e93d60"
down_revision = "65a7c9e21b04"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "character_appearances",
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("choices", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("revision >= 1", name="appearance_revision_positive"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.PrimaryKeyConstraint("character_id"),
    )


def downgrade():
    op.drop_table("character_appearances")
