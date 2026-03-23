"""add_receipt_snapshot_to_sale

Revision ID: 49e9c4957813
Revises: 75edb599eaf2
Create Date: 2026-03-23 10:00:48.276407

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "49e9c4957813"
down_revision: Union[str, Sequence[str], None] = "75edb599eaf2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sale",
        sa.Column(
            "receipt_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Persisted printable receipt payload captured at checkout time.",
        ),
    )


def downgrade() -> None:
    op.drop_column("sale", "receipt_snapshot")
