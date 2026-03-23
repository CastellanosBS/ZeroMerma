"""product_price branch overrides

Revision ID: eee458f64e1a
Revises: ac5d0cef60f7
Create Date: 2026-03-20 14:30:09.573669

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "eee458f64e1a"
down_revision: Union[str, Sequence[str], None] = "ac5d0cef60f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create product_price table.

    This table stores branch-specific product sale prices (overrides).
    Effective price resolution:
        effective = COALESCE(product_price.price, product.sale_price)

    Notes:
      - Single active override per (branch_id, product_id) enforced by unique constraint.
      - Audit fields included for traceability.
    """
    op.create_table(
        "product_price",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "branch_id",
            sa.BigInteger(),
            sa.ForeignKey("branch.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.BigInteger(),
            sa.ForeignKey("product.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("price", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default=sa.text("'MXN'")),
        sa.Column(
            "created_by_id",
            sa.BigInteger(),
            sa.ForeignKey("user_account.id", ondelete="SET NULL"),
            nullable=True,
        ),
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
        comment="Branch-specific product sale price override (effective price policy).",
    )

    # One override per branch/product
    op.create_unique_constraint(
        "uq_product_price_branch_product", "product_price", ["branch_id", "product_id"]
    )

    # Non-negative price guardrail
    op.create_check_constraint(
        "ck_product_price_price_nonneg",
        "product_price",
        "price >= 0",
    )

    # Indexes for common queries
    op.create_index("ix_product_price_branch_id", "product_price", ["branch_id"])
    op.create_index("ix_product_price_product_id", "product_price", ["product_id"])
    op.create_index("ix_product_price_created_by_id", "product_price", ["created_by_id"])


def downgrade() -> None:
    """
    Drop product_price.
    """
    op.drop_index("ix_product_price_created_by_id", table_name="product_price")
    op.drop_index("ix_product_price_product_id", table_name="product_price")
    op.drop_index("ix_product_price_branch_id", table_name="product_price")
    op.drop_constraint("ck_product_price_price_nonneg", "product_price", type_="check")
    op.drop_constraint("uq_product_price_branch_product", "product_price", type_="unique")
    op.drop_table("product_price")
