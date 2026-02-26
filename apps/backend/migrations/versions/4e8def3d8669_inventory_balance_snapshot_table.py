"""inventory_balance snapshot table

Revision ID: 4e8def3d8669
Revises: 8ca11fd794ee
Create Date: 2026-02-26 13:29:51.326327

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4e8def3d8669"
down_revision: Union[str, Sequence[str], None] = "8ca11fd794ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create inventory_balance snapshot table.

    Why:
      - inventory_movement is a ledger (audit history).
      - inventory_balance is a snapshot (fast operational stock).
      - Concurrency-safe stock decrement can be implemented as:
          UPDATE inventory_balance
          SET on_hand = on_hand - :qty
          WHERE branch_id=:b AND product_id=:p AND on_hand >= :qty
          RETURNING on_hand;
    """

    op.create_table(
        "inventory_balance",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
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
        # 3 decimals matches your ledger qty NUMERIC(18,3)
        sa.Column("on_hand", sa.Numeric(18, 3), nullable=False, server_default="0"),
        sa.Column("reserved", sa.Numeric(18, 3), nullable=False, server_default="0"),
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
        comment="Snapshot inventory by (branch, product) for fast reads and atomic decrements",
    )

    # Unique pair: exactly one row per (branch_id, product_id)
    op.create_index(
        "uq_inventory_balance_branch_product",
        "inventory_balance",
        ["branch_id", "product_id"],
        unique=True,
    )

    # Helpful lookup index (even though unique index covers it, this is optional)
    # We'll skip extra indexes to avoid redundancy.

    # Non-negative constraints (prevents corrupt states)
    op.create_check_constraint(
        "ck_inventory_balance_on_hand_nonneg",
        "inventory_balance",
        "on_hand >= 0",
    )
    op.create_check_constraint(
        "ck_inventory_balance_reserved_nonneg",
        "inventory_balance",
        "reserved >= 0",
    )


def downgrade() -> None:
    """
    Drop inventory_balance table and constraints/indexes.
    """
    op.drop_constraint(
        "ck_inventory_balance_reserved_nonneg", "inventory_balance", type_="check"
    )
    op.drop_constraint(
        "ck_inventory_balance_on_hand_nonneg", "inventory_balance", type_="check"
    )
    op.drop_index("uq_inventory_balance_branch_product", table_name="inventory_balance")
    op.drop_table("inventory_balance")
