"""Add commercial discount governance schema.

Revision ID: 20260520_0023_discounts
Revises: 20260520_0022_recipes_costs
Create Date: 2026-05-20 15:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260520_0023_discounts"
down_revision: str | None = "20260520_0022_recipes_costs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "commercial_discounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("product_class_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("discount_type", sa.String(length=32), nullable=False),
        sa.Column("target_scope", sa.String(length=32), nullable=False),
        sa.Column("value", sa.Numeric(12, 4), nullable=False),
        sa.Column("currency_code", sa.String(length=3), server_default="MXN", nullable=False),
        sa.Column("valid_from_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority", sa.Integer(), server_default="1000", nullable=False),
        sa.Column("is_pos_eligible", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="INACTIVE", nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "discount_type IN ('PERCENTAGE', 'FIXED_AMOUNT')",
            name=op.f("ck_commercial_discounts_type_valid"),
        ),
        sa.CheckConstraint(
            "target_scope IN ('GLOBAL', 'PRODUCT', 'CLASS')",
            name=op.f("ck_commercial_discounts_scope_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED')",
            name=op.f("ck_commercial_discounts_status_valid"),
        ),
        sa.CheckConstraint("value > 0", name=op.f("ck_commercial_discounts_value_positive")),
        sa.CheckConstraint(
            "discount_type != 'PERCENTAGE' OR value <= 100",
            name=op.f("ck_commercial_discounts_percentage_range"),
        ),
        sa.CheckConstraint(
            "("
            "(target_scope = 'GLOBAL' AND product_id IS NULL AND product_class_id IS NULL)"
            " OR "
            "(target_scope = 'PRODUCT' AND product_id IS NOT NULL AND product_class_id IS NULL)"
            " OR "
            "(target_scope = 'CLASS' AND product_id IS NULL AND product_class_id IS NOT NULL)"
            ")",
            name=op.f("ck_commercial_discounts_target_shape"),
        ),
        sa.ForeignKeyConstraint(
            ["brand_id"],
            ["brands.id"],
            name=op.f("fk_commercial_discounts_brand_id_brands"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_commercial_discounts_created_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["product_class_id"],
            ["product_classes.id"],
            name=op.f("fk_commercial_discounts_product_class_id_product_classes"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_commercial_discounts_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_commercial_discounts")),
        sa.UniqueConstraint("code", name=op.f("uq_commercial_discounts_code")),
    )
    op.create_index(
        op.f("ix_commercial_discounts_brand_id"), "commercial_discounts", ["brand_id"], unique=False
    )
    op.create_index(
        op.f("ix_commercial_discounts_product_id"),
        "commercial_discounts",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_discounts_product_class_id"),
        "commercial_discounts",
        ["product_class_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_discounts_status"), "commercial_discounts", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_commercial_discounts_target_scope"),
        "commercial_discounts",
        ["target_scope"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_commercial_discounts_target_scope"), table_name="commercial_discounts")
    op.drop_index(op.f("ix_commercial_discounts_status"), table_name="commercial_discounts")
    op.drop_index(
        op.f("ix_commercial_discounts_product_class_id"), table_name="commercial_discounts"
    )
    op.drop_index(op.f("ix_commercial_discounts_product_id"), table_name="commercial_discounts")
    op.drop_index(op.f("ix_commercial_discounts_brand_id"), table_name="commercial_discounts")
    op.drop_table("commercial_discounts")
