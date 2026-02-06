# apps/backend/migrations/versions/4a87fc03a0ce_b2_2_product_inventory_movement.py
# PURPOSE:
#   - Create 'product' (minimal product master)
#   - Create 'inventory_movement' (immutable stock ledger)
#   - Add UNIQUE, CHECK, FKs, and helpful indexes
#
# NOTES:
#   - This migration assumes the admin core tables from B1.2 already exist:
#       branch(id), user_account(id)
#   - Set `down_revision` to the ID of the B1.2 migration in YOUR repo.

from __future__ import annotations

import sqlalchemy as sa  # SQLAlchemy types/defaults/etc.
from alembic import op  # Alembic operations (DDL)

# --- Alembic identifiers ---
revision = "4a87fc03a0ce"  # This file's unique revision id
down_revision = (
    "6358fce6b0b4_admin_core_tables"  # <-- CHANGE THIS to your B1.2 revision id
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Apply schema FORWARD:
      1) Create 'product'
      2) Create 'inventory_movement'
      3) Add constraints and indexes
    """

    # -------------------------------------------------------------------------
    # 1) PRODUCT TABLE
    # -------------------------------------------------------------------------
    op.create_table(
        "product",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "sku",
            sa.String(length=32),
            nullable=True,  # allow NULL; UNIQUE allows multiple NULLs in Postgres
        ),
        sa.Column(
            "name",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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
        comment="Minimal product master for inventory control",
    )

    # UNIQUE(product.sku)
    op.create_unique_constraint("uq_product_sku", "product", ["sku"])

    # -------------------------------------------------------------------------
    # 2) INVENTORY_MOVEMENT TABLE (immutable ledger)
    # -------------------------------------------------------------------------
    op.create_table(
        "inventory_movement",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        # Scope FKs (NOT NULL): every movement belongs to a branch and a product
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
        # Signed quantity (IN flows positive; OUT negative)
        sa.Column(
            "qty",
            sa.Numeric(18, 3),
            nullable=False,
        ),
        # Reason stored as short string; enforced by DB CHECK below
        sa.Column(
            "reason",
            sa.String(length=32),
            nullable=False,
        ),
        # Traceability to generating document (SALE/PURCHASE/etc.)
        sa.Column("ref_type", sa.String(length=32), nullable=True),
        sa.Column("ref_id", sa.BigInteger(), nullable=True),
        # Optional operator note
        sa.Column("note", sa.Text(), nullable=True),
        # Attribution (nullable; SET NULL on user deletion)
        sa.Column(
            "created_by_id",
            sa.BigInteger(),
            sa.ForeignKey("user_account.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Audit timestamps (DB-side defaults)
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
        comment="Inventory ledger: immutable movement (qty ±, reason, refs, audit)",
    )

    # CHECK(reason IN (...)) — keep list in sync with your MovementReason Enum
    op.create_check_constraint(
        "ck_inventory_movement_reason",
        "inventory_movement",
        "reason IN ("
        "'SALE','PURCHASE','ADJUSTMENT',"
        "'PRODUCTION_INPUT','PRODUCTION_OUTPUT',"
        "'TRANSFER_IN','TRANSFER_OUT','OPENING_BALANCE'"
        ")",
    )

    # Helpful indexes:
    #  - FK columns (joins/filters)
    #  - composite (branch_id, product_id) for stock aggregation
    #  - created_at for time-windowed history
    op.create_index(
        "ix_inventory_movement_branch_id",
        "inventory_movement",
        ["branch_id"],
    )
    op.create_index(
        "ix_inventory_movement_product_id",
        "inventory_movement",
        ["product_id"],
    )
    op.create_index(
        "ix_inventory_movement_created_by_id",
        "inventory_movement",
        ["created_by_id"],
    )
    op.create_index(
        "ix_inventory_movement_branch_product",
        "inventory_movement",
        ["branch_id", "product_id"],
    )
    op.create_index(
        "ix_inventory_movement_created_at",
        "inventory_movement",
        ["created_at"],
    )


def downgrade() -> None:
    """
    Revert schema BACKWARD:
      - Drop indexes/constraints explicitly created
      - Drop tables in dependency order (ledger before product)
    """
    # Drop indexes
    op.drop_index("ix_inventory_movement_created_at", table_name="inventory_movement")
    op.drop_index(
        "ix_inventory_movement_branch_product", table_name="inventory_movement"
    )
    op.drop_index(
        "ix_inventory_movement_created_by_id", table_name="inventory_movement"
    )
    op.drop_index("ix_inventory_movement_product_id", table_name="inventory_movement")
    op.drop_index("ix_inventory_movement_branch_id", table_name="inventory_movement")

    # Drop CHECK constraint
    op.drop_constraint(
        "ck_inventory_movement_reason", "inventory_movement", type_="check"
    )

    # Drop ledger first (depends on product/branch/user_account)
    op.drop_table("inventory_movement")

    # Drop product UNIQUE then table
    op.drop_constraint("uq_product_sku", "product", type_="unique")
    op.drop_table("product")
