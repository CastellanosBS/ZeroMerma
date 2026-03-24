"""cash_session_reconciliation_snapshot

Revision ID: b2a23b75d5a3
Revises: 335c336469da
Create Date: 2026-03-23 23:33:54.786150

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b2a23b75d5a3"
down_revision: Union[str, Sequence[str], None] = "335c336469da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Extend cash_session with persisted reconciliation fields.

    New columns:
    - expected_cash:
        System-calculated expected cash at close time.
    - reconciliation_snapshot:
        JSONB evidence captured when closing a session, including expected
        totals by payment method, counted totals, differences, and note.
    """
    op.add_column(
        "cash_session",
        sa.Column(
            "expected_cash",
            sa.Numeric(18, 2),
            nullable=True,
            comment="System-calculated expected cash at close time.",
        ),
    )

    op.add_column(
        "cash_session",
        sa.Column(
            "reconciliation_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment=("Persisted reconciliation evidence captured at cash-session close."),
        ),
    )


def downgrade() -> None:
    """
    Remove persisted reconciliation fields from cash_session.
    """
    op.drop_column("cash_session", "reconciliation_snapshot")
    op.drop_column("cash_session", "expected_cash")
