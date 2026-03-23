"""production_run

Revision ID: ac5d0cef60f7
Revises: 47d70ca76fae
Create Date: 2026-03-20 11:28:12.032310

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ac5d0cef60f7"
down_revision: Union[str, Sequence[str], None] = "47d70ca76fae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create production_run header table.

    Rationale:
      - We want a stable ref_id for inventory_movement rows produced by a production event.
      - We keep it minimal: branch + created_by + timestamps + note.
      - Movements (inputs/outputs) are stored in inventory_movement using ref_type/ref_id.
    """
    op.create_table(
        "production_run",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "branch_id",
            sa.BigInteger(),
            sa.ForeignKey("branch.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_by_id",
            sa.BigInteger(),
            sa.ForeignKey("user_account.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        comment="Production event header; details are stored as "
        "inventory_movement rows (PRODUCTION_INPUT/OUTPUT).",
    )

    op.create_index("ix_production_run_branch_id", "production_run", ["branch_id"])
    op.create_index("ix_production_run_created_by_id", "production_run", ["created_by_id"])
    op.create_index("ix_production_run_created_at", "production_run", ["created_at"])


def downgrade() -> None:
    """
    Drop production_run.
    """
    op.drop_index("ix_production_run_created_at", table_name="production_run")
    op.drop_index("ix_production_run_created_by_id", table_name="production_run")
    op.drop_index("ix_production_run_branch_id", table_name="production_run")
    op.drop_table("production_run")
