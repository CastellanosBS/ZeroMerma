"""Add recipe and cost governance schema.

Revision ID: 20260520_0022_recipes_costs
Revises: 20260519_0021_brand_scope
Create Date: 2026-05-20 09:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260520_0022_recipes_costs"
down_revision: str | None = "20260519_0021_brand_scope"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "product_kind",
            sa.String(length=32),
            server_default="FINISHED_GOOD",
            nullable=False,
        ),
    )
    op.add_column(
        "products",
        sa.Column("unit_of_measure", sa.String(length=32), server_default="piece", nullable=False),
    )
    op.add_column("products", sa.Column("standard_cost", sa.Numeric(12, 4), nullable=True))
    op.create_check_constraint(
        "ck_products_product_kind_valid",
        "products",
        "product_kind IN ('FINISHED_GOOD', 'RAW_MATERIAL')",
    )
    op.create_check_constraint(
        "ck_products_standard_cost_non_negative",
        "products",
        "standard_cost IS NULL OR standard_cost >= 0",
    )

    op.create_table(
        "recipes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_name", sa.String(length=120), nullable=True),
        sa.Column("yield_qty", sa.Numeric(12, 3), nullable=False),
        sa.Column("yield_uom", sa.String(length=32), server_default="piece", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("yield_qty > 0", name=op.f("ck_recipes_yield_qty_positive")),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_recipes_created_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_recipes_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recipes")),
    )
    op.create_index(op.f("ix_recipes_product_id"), "recipes", ["product_id"], unique=False)
    op.create_index(
        "ux_recipes_active_product",
        "recipes",
        ["product_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )

    op.create_table(
        "recipe_inputs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("input_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("display_order", sa.Integer(), server_default="1000", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_recipe_inputs_quantity_positive")),
        sa.ForeignKeyConstraint(
            ["input_product_id"],
            ["products.id"],
            name=op.f("fk_recipe_inputs_input_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name=op.f("fk_recipe_inputs_recipe_id_recipes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recipe_inputs")),
        sa.UniqueConstraint(
            "recipe_id", "input_product_id", name=op.f("uq_recipe_inputs_recipe_product")
        ),
    )
    op.create_index(
        op.f("ix_recipe_inputs_recipe_id"), "recipe_inputs", ["recipe_id"], unique=False
    )
    op.create_index(
        op.f("ix_recipe_inputs_input_product_id"),
        "recipe_inputs",
        ["input_product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_recipe_inputs_input_product_id"), table_name="recipe_inputs")
    op.drop_index(op.f("ix_recipe_inputs_recipe_id"), table_name="recipe_inputs")
    op.drop_table("recipe_inputs")

    op.drop_index("ux_recipes_active_product", table_name="recipes")
    op.drop_index(op.f("ix_recipes_product_id"), table_name="recipes")
    op.drop_table("recipes")

    op.drop_constraint("ck_products_standard_cost_non_negative", "products", type_="check")
    op.drop_constraint("ck_products_product_kind_valid", "products", type_="check")
    op.drop_column("products", "standard_cost")
    op.drop_column("products", "unit_of_measure")
    op.drop_column("products", "product_kind")
