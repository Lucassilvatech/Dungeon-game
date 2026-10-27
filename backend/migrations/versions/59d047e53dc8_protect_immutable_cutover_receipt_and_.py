"""protect immutable cutover receipt and funded asset weights"""

from alembic import op
import sqlalchemy as sa

revision = "59d047e53dc8"
down_revision = "b52708c9a8a4"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "CREATE TRIGGER immutable_cutover_receipt BEFORE UPDATE OR DELETE ON lunar_cutovers FOR EACH ROW EXECUTE FUNCTION lunar_immutable_history()"
    )
    op.execute(
        """CREATE FUNCTION protect_lunar_weights() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF (NEW.weight_mg IS DISTINCT FROM OLD.weight_mg OR NEW.kind IS DISTINCT FROM OLD.kind) AND EXISTS(SELECT 1 FROM lunar_entries) THEN
            RAISE EXCEPTION 'Funded asset weights are frozen';
        END IF;
        RETURN NEW;
    END $$"""
    )
    op.execute(
        "CREATE TRIGGER immutable_funded_asset BEFORE UPDATE ON lunar_assets FOR EACH ROW EXECUTE FUNCTION protect_lunar_weights()"
    )


def downgrade():
    op.execute("DROP TRIGGER immutable_funded_asset ON lunar_assets")
    op.execute("DROP FUNCTION protect_lunar_weights()")
    op.execute("DROP TRIGGER immutable_cutover_receipt ON lunar_cutovers")
