"""Add administrative branch profile fields.

Revision ID: 20260520_0024_branch_admin
Revises: 20260520_0023_discounts
Create Date: 2026-05-20 16:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260520_0024_branch_admin"
down_revision: str | None = "20260520_0023_discounts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("branches", sa.Column("address_line", sa.String(length=240), nullable=True))
    op.add_column("branches", sa.Column("city", sa.String(length=120), nullable=True))
    op.add_column("branches", sa.Column("state", sa.String(length=120), nullable=True))
    op.add_column("branches", sa.Column("country", sa.String(length=120), nullable=True))
    op.add_column("branches", sa.Column("postal_code", sa.String(length=32), nullable=True))
    op.add_column("branches", sa.Column("phone", sa.String(length=40), nullable=True))
    op.add_column("branches", sa.Column("contact_email", sa.String(length=320), nullable=True))
    op.add_column("branches", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("branches", "notes")
    op.drop_column("branches", "contact_email")
    op.drop_column("branches", "phone")
    op.drop_column("branches", "postal_code")
    op.drop_column("branches", "country")
    op.drop_column("branches", "state")
    op.drop_column("branches", "city")
    op.drop_column("branches", "address_line")
