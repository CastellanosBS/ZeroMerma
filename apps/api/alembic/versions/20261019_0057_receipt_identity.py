"""Add optional branch receipt identity without rewriting issued documents."""

import sqlalchemy as sa
from alembic import op

revision = "20261019_0057_receipt_identity"
down_revision = "20261019_0056_hardware"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("branches", sa.Column("receipt_commercial_name", sa.String(160), nullable=True))
    op.add_column(
        "branches", sa.Column("receipt_business_descriptor", sa.String(160), nullable=True)
    )


def downgrade() -> None:
    # Prevent a concurrent configuration write between the guard and column removal.
    op.execute("LOCK TABLE branches IN ACCESS EXCLUSIVE MODE")
    op.execute("""DO $$ BEGIN
        IF EXISTS (
            SELECT 1 FROM branches
            WHERE receipt_commercial_name IS NOT NULL
               OR receipt_business_descriptor IS NOT NULL
        ) THEN
            RAISE EXCEPTION 'Cannot discard configured receipt identity; restore or roll forward';
        END IF;
    END $$""")
    op.drop_column("branches", "receipt_business_descriptor")
    op.drop_column("branches", "receipt_commercial_name")
