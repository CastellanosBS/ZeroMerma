"""Add procurement metadata for admin input and consumable catalog.

Revision ID: 20260520_0031_inputs_supplies
Revises: 20260520_0030_admin_purchases
Create Date: 2026-05-20 23:35:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260520_0031_inputs_supplies"
down_revision: str | None = "20260520_0030_admin_purchases"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("is_inventory_tracked", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "products",
        sa.Column("is_purchasable", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "products",
        sa.Column("purchase_unit_of_measure", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("purchase_conversion_factor", sa.Numeric(12, 6), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("usage_type", sa.String(length=40), nullable=True, server_default="OTHER"),
    )
    op.add_column("products", sa.Column("minimum_stock", sa.Numeric(12, 3), nullable=True))
    op.add_column("products", sa.Column("reorder_point", sa.Numeric(12, 3), nullable=True))
    op.add_column(
        "products",
        sa.Column("preferred_order_quantity", sa.Numeric(12, 3), nullable=True),
    )
    op.add_column("products", sa.Column("procurement_notes", sa.Text(), nullable=True))
    op.create_check_constraint(
        op.f("ck_products_usage_type_valid"),
        "products",
        "usage_type IS NULL OR usage_type IN ("
        "'RECIPE_INPUT', "
        "'PRODUCTION_SUPPLY', "
        "'PACKAGING', "
        "'CLEANING_SANITATION', "
        "'OPERATIONAL_SUPPLY', "
        "'OTHER'"
        ")",
    )
    op.create_check_constraint(
        op.f("ck_products_purchase_conversion_positive"),
        "products",
        "purchase_conversion_factor IS NULL OR purchase_conversion_factor > 0",
    )
    op.create_check_constraint(
        op.f("ck_products_minimum_stock_non_negative"),
        "products",
        "minimum_stock IS NULL OR minimum_stock >= 0",
    )
    op.create_check_constraint(
        op.f("ck_products_reorder_point_non_negative"),
        "products",
        "reorder_point IS NULL OR reorder_point >= 0",
    )
    op.create_check_constraint(
        op.f("ck_products_preferred_order_qty_non_negative"),
        "products",
        "preferred_order_quantity IS NULL OR preferred_order_quantity >= 0",
    )
    op.alter_column("products", "is_inventory_tracked", server_default=None)
    op.alter_column("products", "is_purchasable", server_default=None)
    op.alter_column("products", "usage_type", server_default=None)

    op.add_column(
        "supplier_products",
        sa.Column("conversion_factor", sa.Numeric(12, 6), nullable=True),
    )
    op.create_check_constraint(
        op.f("ck_supplier_products_conversion_factor_positive"),
        "supplier_products",
        "conversion_factor IS NULL OR conversion_factor > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_supplier_products_conversion_factor_positive"),
        "supplier_products",
        type_="check",
    )
    op.drop_column("supplier_products", "conversion_factor")

    op.drop_constraint(
        op.f("ck_products_preferred_order_qty_non_negative"), "products", type_="check"
    )
    op.drop_constraint(op.f("ck_products_reorder_point_non_negative"), "products", type_="check")
    op.drop_constraint(op.f("ck_products_minimum_stock_non_negative"), "products", type_="check")
    op.drop_constraint(op.f("ck_products_purchase_conversion_positive"), "products", type_="check")
    op.drop_constraint(op.f("ck_products_usage_type_valid"), "products", type_="check")
    op.drop_column("products", "procurement_notes")
    op.drop_column("products", "preferred_order_quantity")
    op.drop_column("products", "reorder_point")
    op.drop_column("products", "minimum_stock")
    op.drop_column("products", "usage_type")
    op.drop_column("products", "purchase_conversion_factor")
    op.drop_column("products", "purchase_unit_of_measure")
    op.drop_column("products", "is_purchasable")
    op.drop_column("products", "is_inventory_tracked")
