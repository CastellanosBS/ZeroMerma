"""Add empty-counter flag to cash closes.

Revision ID: 20260518_0020_counter_empty
Revises: 20260518_0019_close_mode
Create Date: 2026-05-18 20:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260518_0020_counter_empty"
down_revision: str | None = "20260518_0019_close_mode"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cash_session_closes",
        sa.Column(
            "counter_empty_confirmed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.drop_constraint(
        "ck_cash_session_closes_close_mode_valid",
        "cash_session_closes",
        type_="check",
    )
    op.execute(
        "UPDATE cash_session_closes SET close_mode = 'WITH_COUNT' WHERE close_mode <> 'WITH_COUNT'"
    )
    op.create_check_constraint(
        "ck_cash_session_closes_close_mode_valid",
        "cash_session_closes",
        "close_mode IN ('WITH_COUNT')",
    )
    op.alter_column("cash_session_closes", "counter_empty_confirmed", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "ck_cash_session_closes_close_mode_valid",
        "cash_session_closes",
        type_="check",
    )
    op.create_check_constraint(
        "ck_cash_session_closes_close_mode_valid",
        "cash_session_closes",
        "close_mode IN ('WITH_COUNT')",
    )
    op.drop_column("cash_session_closes", "counter_empty_confirmed")
