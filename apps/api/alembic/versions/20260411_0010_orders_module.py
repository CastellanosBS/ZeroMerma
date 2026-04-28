"""Create customer orders module schema.

Revision ID: 0010_orders_module
Revises: 0009_cash_close_payment_methods
Create Date: 2026-04-11 16:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_orders_module"
down_revision: str | None = "0009_cash_close_payment_methods"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customer_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workstation_id_created", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("active_cash_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("customer_name", sa.String(length=160), nullable=False),
        sa.Column("customer_phone", sa.String(length=32), nullable=True),
        sa.Column("requested_for_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "currency_code", sa.String(length=3), nullable=False, server_default=sa.text("'MXN'")
        ),
        sa.Column("subtotal_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("advance_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("remaining_balance_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('PENDING', 'READY', 'DELIVERED', 'CANCELED')",
            name="ck_customer_orders_status_valid",
        ),
        sa.CheckConstraint(
            "customer_name <> ''",
            name="ck_customer_orders_customer_name_not_empty",
        ),
        sa.CheckConstraint(
            "subtotal_amount >= 0",
            name="ck_customer_orders_subtotal_non_negative",
        ),
        sa.CheckConstraint(
            "total_amount >= 0",
            name="ck_customer_orders_total_non_negative",
        ),
        sa.CheckConstraint(
            "advance_amount >= 0",
            name="ck_customer_orders_advance_non_negative",
        ),
        sa.CheckConstraint(
            "remaining_balance_amount >= 0",
            name="ck_customer_orders_remaining_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["active_cash_session_id"], ["cash_sessions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["canceled_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["delivered_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["workstation_id_created"], ["workstations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_customer_orders")),
    )
    op.create_index(
        "ix_customer_orders_branch_status_created",
        "customer_orders",
        ["branch_id", "status", "created_at_utc"],
        unique=False,
    )
    op.create_index(
        "ix_customer_orders_requested_for",
        "customer_orders",
        ["branch_id", "requested_for_at"],
        unique=False,
    )

    op.create_table(
        "customer_order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("product_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("product_class_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_class_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("product_class_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("line_total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_customer_order_items_quantity_positive"),
        sa.CheckConstraint(
            "unit_price >= 0", name="ck_customer_order_items_unit_price_non_negative"
        ),
        sa.CheckConstraint(
            "line_total_amount >= 0",
            name="ck_customer_order_items_line_total_non_negative",
        ),
        sa.ForeignKeyConstraint(["customer_order_id"], ["customer_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_class_id"], ["product_classes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_customer_order_items")),
        sa.UniqueConstraint(
            "customer_order_id",
            "line_number",
            name="uq_customer_order_items_line_number",
        ),
    )
    op.create_index(
        "ix_customer_order_items_order_id",
        "customer_order_items",
        ["customer_order_id"],
        unique=False,
    )

    op.create_table(
        "customer_order_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("payment_type", sa.String(length=20), nullable=False),
        sa.Column("payment_method_code", sa.String(length=40), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "currency_code", sa.String(length=3), nullable=False, server_default=sa.text("'MXN'")
        ),
        sa.Column("workstation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cash_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recorded_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "payment_type IN ('ADVANCE', 'SETTLEMENT')",
            name="ck_customer_order_payments_type_valid",
        ),
        sa.CheckConstraint(
            "payment_method_code IN ('CASH', 'CARD', 'MIXED', 'OTHER')",
            name="ck_customer_order_payments_method_valid",
        ),
        sa.CheckConstraint(
            "amount > 0",
            name="ck_customer_order_payments_amount_positive",
        ),
        sa.ForeignKeyConstraint(["cash_session_id"], ["cash_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_order_id"], ["customer_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workstation_id"], ["workstations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_customer_order_payments")),
        sa.UniqueConstraint(
            "customer_order_id",
            "sequence",
            name="uq_customer_order_payments_sequence",
        ),
    )
    op.create_index(
        "ix_customer_order_payments_order_id",
        "customer_order_payments",
        ["customer_order_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_customer_order_payments_order_id", table_name="customer_order_payments")
    op.drop_table("customer_order_payments")

    op.drop_index("ix_customer_order_items_order_id", table_name="customer_order_items")
    op.drop_table("customer_order_items")

    op.drop_index("ix_customer_orders_requested_for", table_name="customer_orders")
    op.drop_index("ix_customer_orders_branch_status_created", table_name="customer_orders")
    op.drop_table("customer_orders")
