"""product category + product v2

Revision ID: 47d70ca76fae
Revises: 4e8def3d8669
Create Date: 2026-03-19 15:34:14.504615


product category + product v2

WHY THIS MIGRATION EXISTS
-------------------------
We are moving from a "minimal Product master" to a more realistic catalog model:
- ProductCategory: groups products (e.g., DONUTS, DRINKS, INGREDIENTS).
- Product v2 fields:
  * category_id: optional FK for now (backward-compatible).
  * uom: unit of measure (PCS/KG/L/...), with a CHECK constraint.
  * is_input: marks raw materials/ingredients vs sellable finished goods.
  * sale_price: optional selling price snapshot (catalog-level).
  * standard_cost: optional standard cost (catalog-level).

BACKWARD COMPATIBILITY STRATEGY
-------------------------------
This migration is intentionally non-breaking:
- category_id is nullable for now.
- uom and is_input have server defaults so existing INSERTs keep working.
- We are not changing existing columns/types/defaults in product.

NEXT STEP (planned)
-------------------
After schema lands, we will:
- extend dev_seed to create categories + populate the new product fields,
- add catalog endpoints (Phase 6.2),
- optionally enforce category_id NOT NULL once the app always provides it.

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "47d70ca76fae"
down_revision: Union[str, Sequence[str], None] = "4e8def3d8669"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # (1) Create product_category table
    # -------------------------------------------------------------------------
    op.create_table(
        "product_category",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
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
        comment="Product grouping for catalog (e.g., DONUTS, DRINKS, INGREDIENTS).",
    )

    # Unique code (stable identifier used by UI/config/seed)
    op.create_unique_constraint(
        "uq_product_category_code", "product_category", ["code"]
    )

    # -------------------------------------------------------------------------
    # (2) Extend product table (Product v2 fields)
    # -------------------------------------------------------------------------
    # NOTE: category_id is nullable for now to keep backward compatibility.
    op.add_column("product", sa.Column("category_id", sa.BigInteger(), nullable=True))

    # Unit of measure:
    # - Must be NOT NULL for data quality.
    # - Has a server_default so old inserts don't break.
    op.add_column(
        "product",
        sa.Column(
            "uom", sa.String(length=16), nullable=False, server_default=sa.text("'PCS'")
        ),
    )

    # Is input (ingredient/raw material) vs finished sellable product.
    op.add_column(
        "product",
        sa.Column(
            "is_input", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )

    # Optional catalog-level pricing/costing fields.
    op.add_column("product", sa.Column("sale_price", sa.Numeric(18, 2), nullable=True))
    op.add_column(
        "product", sa.Column("standard_cost", sa.Numeric(18, 2), nullable=True)
    )

    # FK: category_id -> product_category.id
    op.create_foreign_key(
        "fk_product_category_id_product_category",
        source_table="product",
        referent_table="product_category",
        local_cols=["category_id"],
        remote_cols=["id"],
        ondelete="RESTRICT",
    )

    # Index: speeds up filtering products by category
    op.create_index("ix_product_category_id", "product", ["category_id"])

    # CHECK constraint for uom:
    # Keep the set small and explicit; we can expand later if needed.
    op.create_check_constraint(
        "ck_product_uom_allowed",
        "product",
        "uom IN ('PCS', 'KG', 'G', 'L', 'ML')",
    )

    # -------------------------------------------------------------------------
    # (3) Clean up server defaults (optional policy)
    # -------------------------------------------------------------------------
    # We KEEP server defaults for uom/is_input to preserve backward compatibility.
    # Once all code paths explicitly set these fields, we may remove defaults.


def downgrade() -> None:
    # Reverse operations in dependency-safe order.

    # Drop constraints/indexes that depend on columns
    op.drop_constraint("ck_product_uom_allowed", "product", type_="check")
    op.drop_index("ix_product_category_id", table_name="product")
    op.drop_constraint(
        "fk_product_category_id_product_category", "product", type_="foreignkey"
    )

    # Drop added columns
    op.drop_column("product", "standard_cost")
    op.drop_column("product", "sale_price")
    op.drop_column("product", "is_input")
    op.drop_column("product", "uom")
    op.drop_column("product", "category_id")

    # Drop product_category table
    op.drop_constraint("uq_product_category_code", "product_category", type_="unique")
    op.drop_table("product_category")
