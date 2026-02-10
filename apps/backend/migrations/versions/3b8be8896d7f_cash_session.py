"""cash_session

Revision ID: 3b8be8896d7f
Revises: 8e1d77af65e2
Create Date: 2026-02-09 18:08:19.158531

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3b8be8896d7f"
down_revision: Union[str, Sequence[str], None] = "8e1d77af65e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Apply schema FORWARD:
      - Create cash_session table
      - Add indexes
      - Add a Postgres partial unique index to ensure 1 OPEN session per branch
    """

    # ---------------------------------------------------------------------
    # 1) Create the cash_session table
    # ---------------------------------------------------------------------
    op.create_table(
        "cash_session",
        # Primary key
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
        # Scope: branch
        sa.Column(
            "branch_id",
            sa.BigInteger(),
            sa.ForeignKey("branch.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # Audit: who opened/closed
        sa.Column(
            "opened_by_id",
            sa.BigInteger(),
            sa.ForeignKey("user_account.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "closed_by_id",
            sa.BigInteger(),
            sa.ForeignKey("user_account.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Session timing
        sa.Column(
            "opened_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "closed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        # Money (use NUMERIC to avoid float issues)
        sa.Column("opening_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("closing_amount", sa.Numeric(18, 2), nullable=True),
        # Status stored as short string
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'OPEN'"),
        ),
        # Standard audit timestamps
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
        comment="POS cash/register session per branch; at most one OPEN per branch",
    )

    # ---------------------------------------------------------------------
    # 2) Helpful indexes for common queries (branch lookup, audit)
    # ---------------------------------------------------------------------
    op.create_index("ix_cash_session_branch_id", "cash_session", ["branch_id"])
    op.create_index("ix_cash_session_opened_by_id", "cash_session", ["opened_by_id"])
    op.create_index("ix_cash_session_closed_by_id", "cash_session", ["closed_by_id"])
    op.create_index("ix_cash_session_opened_at", "cash_session", ["opened_at"])
    op.create_index("ix_cash_session_status", "cash_session", ["status"])

    # ---------------------------------------------------------------------
    # 3) Invariant: only ONE OPEN session per branch
    #    Implemented as a Postgres partial unique index:
    #      UNIQUE(branch_id) WHERE status='OPEN'
    # ---------------------------------------------------------------------
    op.execute(
        """
        CREATE UNIQUE INDEX uq_cash_session_one_open_per_branch
        ON cash_session (branch_id)
        WHERE status = 'OPEN';
        """
    )


def downgrade() -> None:
    """
    Revert schema BACKWARD:
      - Drop the partial unique index
      - Drop other indexes
      - Drop cash_session table
    """

    # Drop the Postgres partial unique index first
    op.execute("DROP INDEX IF EXISTS uq_cash_session_one_open_per_branch;")

    # Drop regular indexes
    op.drop_index("ix_cash_session_status", table_name="cash_session")
    op.drop_index("ix_cash_session_opened_at", table_name="cash_session")
    op.drop_index("ix_cash_session_closed_by_id", table_name="cash_session")
    op.drop_index("ix_cash_session_opened_by_id", table_name="cash_session")
    op.drop_index("ix_cash_session_branch_id", table_name="cash_session")

    # Drop table
    op.drop_table("cash_session")
