"""payment table

Revision ID: 8ca11fd794ee
Revises: 2c2dece83ed7
Create Date: 2026-02-20 19:23:39.477153

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8ca11fd794ee"
down_revision: Union[str, Sequence[str], None] = "2c2dece83ed7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Apply schema FORWARD:
      - Create payment table
      - Add indexes
      - Add a CHECK constraint on method (MVP list)
    """

    # -------------------------------------------------------------------------
    # 1) payment table
    # -------------------------------------------------------------------------
    op.create_table(
        "payment",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
        # FK to sale: payments belong to a sale.
        # CASCADE: if a sale is deleted in dev/test, its payments are removed too.
        sa.Column(
            "sale_id",
            sa.BigInteger(),
            sa.ForeignKey("sale.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Payment method: string for MVP
        sa.Column("method", sa.String(length=16), nullable=False),
        # Amount: NUMERIC for currency precision
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        # Optional external reference (card auth code, transfer id, etc.)
        sa.Column("reference", sa.String(length=64), nullable=True),
        # Timestamp: DB server time
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        comment="Payment records for a sale (immutable ledger)",
    )

    # -------------------------------------------------------------------------
    # 2) Indexes
    # -------------------------------------------------------------------------
    op.create_index("ix_payment_sale_id", "payment", ["sale_id"])
    op.create_index("ix_payment_created_at", "payment", ["created_at"])
    op.create_index("ix_payment_method", "payment", ["method"])

    # -------------------------------------------------------------------------
    # 3) CHECK constraint for method values (low-risk hardening)
    # -------------------------------------------------------------------------
    op.create_check_constraint(
        "ck_payment_method",
        "payment",
        "method IN ('CASH','CARD','TRANSFER','OTHER')",
    )


def downgrade() -> None:
    """
    Revert schema BACKWARD:
      - Drop constraint
      - Drop indexes
      - Drop payment table
    """

    op.drop_constraint("ck_payment_method", "payment", type_="check")

    op.drop_index("ix_payment_method", table_name="payment")
    op.drop_index("ix_payment_created_at", table_name="payment")
    op.drop_index("ix_payment_sale_id", table_name="payment")

    op.drop_table("payment")
