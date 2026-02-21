"""sale and sale_item

Revision ID: 2c2dece83ed7
Revises: 3b8be8896d7f
Create Date: 2026-02-20 15:02:46.313375

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2c2dece83ed7"
down_revision: Union[str, Sequence[str], None] = "3b8be8896d7f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Apply schema FORWARD:
      1) Create sale (header)
      2) Create sale_item (lines)
      3) Add indexes for common access patterns
    """

    # -------------------------------------------------------------------------
    # 1) sale table (header)
    # -------------------------------------------------------------------------
    op.create_table(
        "sale",
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
        # POS flow anchor: must belong to an existing cash_session
        sa.Column(
            "cash_session_id",
            sa.BigInteger(),
            sa.ForeignKey("cash_session.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # Audit: who created the sale
        sa.Column(
            "created_by_id",
            sa.BigInteger(),
            sa.ForeignKey("user_account.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # Timestamp of sale creation (DB server time)
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Totals as NUMERIC to avoid floating rounding errors in DB
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "tax", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("total", sa.Numeric(18, 2), nullable=False),
        # Status (string for simplicity; we will harden with CHECK later)
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'OPEN'"),
        ),
        # Updated_at (optional, but matches your project’s standard)
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        comment="POS sale header (branch/session/totals/status/audit)",
    )

    # Indexes for sale
    op.create_index("ix_sale_branch_id", "sale", ["branch_id"])
    op.create_index("ix_sale_cash_session_id", "sale", ["cash_session_id"])
    op.create_index("ix_sale_created_by_id", "sale", ["created_by_id"])
    op.create_index("ix_sale_created_at", "sale", ["created_at"])
    op.create_index("ix_sale_status", "sale", ["status"])

    # -------------------------------------------------------------------------
    # 2) sale_item table (lines)
    # -------------------------------------------------------------------------
    op.create_table(
        "sale_item",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
        # Parent sale (CASCADE: deleting a sale deletes its lines)
        sa.Column(
            "sale_id",
            sa.BigInteger(),
            sa.ForeignKey("sale.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Product (RESTRICT: cannot delete product while referenced by history)
        sa.Column(
            "product_id",
            sa.BigInteger(),
            sa.ForeignKey("product.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # Qty can be fractional (e.g., weight-based), keep precision 3 decimals
        sa.Column("qty", sa.Numeric(18, 3), nullable=False),
        # Snapshot pricing at time of sale
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        # Backend computed: qty * unit_price, stored for audit and performance
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
        comment="POS sale line items (product/qty/price snapshot)",
    )

    # Indexes for sale_item
    op.create_index("ix_sale_item_sale_id", "sale_item", ["sale_id"])
    op.create_index("ix_sale_item_product_id", "sale_item", ["product_id"])


def downgrade() -> None:
    """
    Revert schema BACKWARD:
      - Drop indexes first
      - Drop sale_item then sale (dependency order)
    """

    # sale_item indexes
    op.drop_index("ix_sale_item_product_id", table_name="sale_item")
    op.drop_index("ix_sale_item_sale_id", table_name="sale_item")

    # Drop sale_item table first (depends on sale)
    op.drop_table("sale_item")

    # sale indexes
    op.drop_index("ix_sale_status", table_name="sale")
    op.drop_index("ix_sale_created_at", table_name="sale")
    op.drop_index("ix_sale_created_by_id", table_name="sale")
    op.drop_index("ix_sale_cash_session_id", table_name="sale")
    op.drop_index("ix_sale_branch_id", table_name="sale")

    # Drop sale table
    op.drop_table("sale")
