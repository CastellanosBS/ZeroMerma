"""Add explicit cash close mode.

Revision ID: 20260518_0019_close_mode
Revises: 20260511_0018_user_surface
Create Date: 2026-05-18 20:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260518_0019_close_mode"
down_revision: str | None = "20260511_0018_user_surface"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cash_session_closes",
        sa.Column(
            "close_mode",
            sa.String(length=32),
            nullable=False,
            server_default="WITH_COUNT",
        ),
    )
    op.create_check_constraint(
        "ck_cash_session_closes_close_mode_valid",
        "cash_session_closes",
        "close_mode IN ('WITH_COUNT')",
    )
    op.alter_column("cash_session_closes", "close_mode", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "ck_cash_session_closes_close_mode_valid",
        "cash_session_closes",
        type_="check",
    )
    op.drop_column("cash_session_closes", "close_mode")
