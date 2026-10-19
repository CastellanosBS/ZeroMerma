"""Preserve expected actual-method totals even when a card count is absent."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261019_0046_close_counts"
down_revision: str | None = "20261019_0045_refund_obligations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "cash_session_close_payment_method_counts"
CONSTRAINT = "ck_cash_session_close_payment_method_counts_expected_non_negative"
COUNT_CONSTRAINT = "ck_cash_session_close_payment_method_counts_counted_non_negative"


def upgrade() -> None:
    op.alter_column(TABLE, "counted_amount", existing_type=sa.Numeric(12, 2), nullable=True)
    op.drop_constraint(COUNT_CONSTRAINT, TABLE, type_="check")
    op.create_check_constraint(
        COUNT_CONSTRAINT, TABLE, "payment_method_code = 'CARD' OR counted_amount >= 0"
    )
    op.drop_constraint(CONSTRAINT, TABLE, type_="check")
    op.create_check_constraint(
        CONSTRAINT,
        TABLE,
        "expected_amount IS NULL OR payment_method_code <> 'CASH' OR expected_amount >= 0",
    )


def downgrade() -> None:
    # A missing count must never become an invented zero to enable a downgrade.
    op.execute("""
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM cash_session_close_payment_method_counts
               WHERE counted_amount IS NULL OR counted_amount < 0 OR expected_amount < 0) THEN
        RAISE EXCEPTION 'Financial snapshots require roll-forward or verified restore';
    END IF;
END $$;
""")
    op.drop_constraint(CONSTRAINT, TABLE, type_="check")
    op.create_check_constraint(CONSTRAINT, TABLE, "expected_amount IS NULL OR expected_amount >= 0")
    op.drop_constraint(COUNT_CONSTRAINT, TABLE, type_="check")
    op.create_check_constraint(COUNT_CONSTRAINT, TABLE, "counted_amount >= 0")
    op.alter_column(TABLE, "counted_amount", existing_type=sa.Numeric(12, 2), nullable=False)
