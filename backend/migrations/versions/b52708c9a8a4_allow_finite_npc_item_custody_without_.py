"""allow finite npc item custody without owner"""
from alembic import op
import sqlalchemy as sa

revision = 'b52708c9a8a4'
down_revision = 'ac5689b8a309'
branch_labels = None
depends_on = None

def upgrade():
    op.drop_constraint('item_custody','items',type_='check')
    op.create_check_constraint('item_custody','items',"(location NOT IN ('auction','recovery','destroyed') OR (owner IS NULL AND NOT equipped)) AND (owner IS NOT NULL OR location IN ('auction','recovery','destroyed','npc'))")


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS(SELECT 1 FROM items WHERE location='npc')")).scalar():
        raise RuntimeError('NPC custody exists; preserve items')
    op.drop_constraint('item_custody','items',type_='check')
    op.create_check_constraint('item_custody','items',"(location NOT IN ('auction','recovery','destroyed') OR (owner IS NULL AND NOT equipped)) AND (owner IS NOT NULL OR location IN ('auction','recovery','destroyed'))")
