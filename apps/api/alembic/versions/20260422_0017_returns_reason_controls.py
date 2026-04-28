"""Add return reason fields.

Revision ID: 20260422_0017_returns_reason
Revises: 20260417_0016_order_cancel
Create Date: 2026-04-22 11:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260422_0017_returns_reason"
down_revision: str | None = "20260417_0016_order_cancel"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sale_returns",
        sa.Column(
            "reason_code",
            sa.String(length=40),
            nullable=False,
            server_default=sa.text("'OTHER'"),
        ),
    )
    op.add_column(
        "sale_returns",
        sa.Column(
            "reason_name",
            sa.String(length=120),
            nullable=False,
            server_default=sa.text("'Otro'"),
        ),
    )
    op.alter_column("sale_returns", "reason_code", server_default=None)
    op.alter_column("sale_returns", "reason_name", server_default=None)


def downgrade() -> None:
    op.drop_column("sale_returns", "reason_name")
    op.drop_column("sale_returns", "reason_code")
