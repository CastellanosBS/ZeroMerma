"""Create Phase 2A POS catalog and sales schema.

Revision ID: 0003_phase_2a_pos_sales
Revises: 0002_phase_1a_core_identity_cash
Create Date: 2026-04-08 01:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_phase_2a_pos_sales"
down_revision: str | None = "0002_phase_1a_core_identity_cash"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_classes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("quick_name", sa.String(length=80), nullable=True),
        sa.Column("search_aliases", sa.Text(), nullable=True),
        sa.Column("capture_mode_default", sa.String(length=32), nullable=False),
        sa.Column("class_capture_unit_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column(
            "currency_code", sa.String(length=3), nullable=False, server_default=sa.text("'MXN'")
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_sellable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "capture_mode_default IN ('CLASS_CAPTURE', 'PRODUCT_DIRECT')",
            name="ck_product_classes_capture_mode_valid",
        ),
        sa.CheckConstraint(
            "class_capture_unit_price IS NULL OR class_capture_unit_price >= 0",
            name="ck_product_classes_class_capture_unit_price_non_negative",
        ),
        sa.CheckConstraint(
            "("
            "(capture_mode_default = 'CLASS_CAPTURE' AND class_capture_unit_price IS NOT NULL)"
            " OR "
            "(capture_mode_default = 'PRODUCT_DIRECT' AND class_capture_unit_price IS NULL)"
            ")",
            name="ck_product_classes_capture_mode_price_shape",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_classes")),
        sa.UniqueConstraint("code", name=op.f("uq_product_classes_code")),
    )
    op.create_index(
        "ix_product_classes_pos_lookup",
        "product_classes",
        ["is_active", "is_sellable", "capture_mode_default", "name"],
        unique=False,
    )

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_class_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("quick_name", sa.String(length=80), nullable=True),
        sa.Column("search_aliases", sa.Text(), nullable=True),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "currency_code", sa.String(length=3), nullable=False, server_default=sa.text("'MXN'")
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_sellable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("unit_price >= 0", name="ck_products_unit_price_non_negative"),
        sa.ForeignKeyConstraint(["product_class_id"], ["product_classes.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        sa.UniqueConstraint("code", name=op.f("uq_products_code")),
    )
    op.create_index(
        "ix_products_class_lookup",
        "products",
        ["product_class_id", "is_active", "is_sellable", "name"],
        unique=False,
    )

    op.create_table(
        "sales",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workstation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cash_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "currency_code", sa.String(length=3), nullable=False, server_default=sa.text("'MXN'")
        ),
        sa.Column("subtotal_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("change_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('CONFIRMED')", name="ck_sales_status_valid"),
        sa.CheckConstraint("subtotal_amount >= 0", name="ck_sales_subtotal_amount_non_negative"),
        sa.CheckConstraint("total_amount >= 0", name="ck_sales_total_amount_non_negative"),
        sa.CheckConstraint("paid_amount >= 0", name="ck_sales_paid_amount_non_negative"),
        sa.CheckConstraint("change_amount >= 0", name="ck_sales_change_amount_non_negative"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cash_session_id"], ["cash_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operator_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workstation_id"], ["workstations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sales")),
    )
    op.create_index(
        "ix_sales_branch_confirmed_at", "sales", ["branch_id", "confirmed_at"], unique=False
    )
    op.create_index("ix_sales_cash_session_id", "sales", ["cash_session_id"], unique=False)
    op.create_index("ix_sales_workstation_id", "sales", ["workstation_id"], unique=False)

    op.create_table(
        "sale_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("capture_mode", sa.String(length=32), nullable=False),
        sa.Column("product_class_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("catalog_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("catalog_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("line_total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("physical_attribution_status", sa.String(length=40), nullable=False),
        sa.CheckConstraint(
            "capture_mode IN ('CLASS_CAPTURE', 'PRODUCT_DIRECT')",
            name="ck_sale_lines_capture_mode_valid",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_sale_lines_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_sale_lines_unit_price_non_negative"),
        sa.CheckConstraint(
            "line_total_amount >= 0",
            name="ck_sale_lines_total_amount_non_negative",
        ),
        sa.CheckConstraint(
            "physical_attribution_status IN ('PENDING_RECONCILIATION', 'DIRECT_ASSIGNED')",
            name="ck_sale_lines_physical_attribution_status_valid",
        ),
        sa.CheckConstraint(
            "("
            "(capture_mode = 'CLASS_CAPTURE' AND product_class_id IS NOT NULL "
            "AND product_id IS NULL)"
            " OR "
            "(capture_mode = 'PRODUCT_DIRECT' AND product_class_id IS NULL "
            "AND product_id IS NOT NULL)"
            ")",
            name="ck_sale_lines_reference_shape",
        ),
        sa.ForeignKeyConstraint(["product_class_id"], ["product_classes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sale_lines")),
        sa.UniqueConstraint("sale_id", "sequence", name="uq_sale_lines_sale_sequence"),
    )
    op.create_index("ix_sale_lines_sale_id", "sale_lines", ["sale_id"], unique=False)

    op.create_table(
        "sale_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("payment_method_code", sa.String(length=40), nullable=False),
        sa.Column("tendered_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("applied_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("change_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "currency_code", sa.String(length=3), nullable=False, server_default=sa.text("'MXN'")
        ),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "tendered_amount >= 0",
            name="ck_sale_payments_tendered_amount_non_negative",
        ),
        sa.CheckConstraint(
            "applied_amount >= 0",
            name="ck_sale_payments_applied_amount_non_negative",
        ),
        sa.CheckConstraint(
            "change_amount >= 0", name="ck_sale_payments_change_amount_non_negative"
        ),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sale_payments")),
        sa.UniqueConstraint("sale_id", "sequence", name="uq_sale_payments_sale_sequence"),
    )
    op.create_index("ix_sale_payments_sale_id", "sale_payments", ["sale_id"], unique=False)

    op.create_table(
        "cash_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cash_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workstation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("movement_type", sa.String(length=40), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("payment_method_code", sa.String(length=40), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "currency_code", sa.String(length=3), nullable=False, server_default=sa.text("'MXN'")
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("direction IN ('IN', 'OUT')", name="ck_cash_movements_direction_valid"),
        sa.CheckConstraint("amount >= 0", name="ck_cash_movements_amount_non_negative"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cash_session_id"], ["cash_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operator_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workstation_id"], ["workstations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cash_movements")),
    )
    op.create_index(
        "ix_cash_movements_cash_session_occurred_at",
        "cash_movements",
        ["cash_session_id", "occurred_at"],
        unique=False,
    )
    op.create_index("ix_cash_movements_sale_id", "cash_movements", ["sale_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_cash_movements_sale_id", table_name="cash_movements")
    op.drop_index("ix_cash_movements_cash_session_occurred_at", table_name="cash_movements")
    op.drop_table("cash_movements")

    op.drop_index("ix_sale_payments_sale_id", table_name="sale_payments")
    op.drop_table("sale_payments")

    op.drop_index("ix_sale_lines_sale_id", table_name="sale_lines")
    op.drop_table("sale_lines")

    op.drop_index("ix_sales_workstation_id", table_name="sales")
    op.drop_index("ix_sales_cash_session_id", table_name="sales")
    op.drop_index("ix_sales_branch_confirmed_at", table_name="sales")
    op.drop_table("sales")

    op.drop_index("ix_products_class_lookup", table_name="products")
    op.drop_table("products")

    op.drop_index("ix_product_classes_pos_lookup", table_name="product_classes")
    op.drop_table("product_classes")
