"""Add user default application surface.

Revision ID: 20260511_0018_user_surface
Revises: 20260422_0017_returns_reason
Create Date: 2026-05-11 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260511_0018_user_surface"
down_revision: str | None = "20260422_0017_returns_reason"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "default_surface",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'POS'"),
        ),
    )
    op.create_check_constraint(
        "ck_users_default_surface_valid",
        "users",
        "default_surface IN ('POS', 'BACKOFFICE')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_default_surface_valid", "users", type_="check")
    op.drop_column("users", "default_surface")
