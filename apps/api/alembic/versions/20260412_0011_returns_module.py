"""Create sale returns module schema.

Revision ID: 0011_returns_module
Revises: 0010_orders_module
Create Date: 2026-04-12 10:15:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_returns_module"
down_revision: str | None = "0010_orders_module"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sale_returns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workstation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cash_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("refund_method_code", sa.String(length=40), nullable=False),
        sa.Column(
            "currency_code", sa.String(length=3), nullable=False, server_default=sa.text("'MXN'")
        ),
        sa.Column("total_refund_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('COMMITTED')",
            name="ck_sale_returns_status_valid",
        ),
        sa.CheckConstraint(
            "refund_method_code IN ('CASH')",
            name="ck_sale_returns_refund_method_valid",
        ),
        sa.CheckConstraint(
            "total_refund_amount >= 0",
            name="ck_sale_returns_total_refund_non_negative",
        ),
        sa.ForeignKeyConstraint(["original_sale_id"], ["sales.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workstation_id"], ["workstations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cash_session_id"], ["cash_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sale_returns")),
    )
    op.create_index(
        "ix_sale_returns_branch_created",
        "sale_returns",
        ["branch_id", "created_at_utc"],
        unique=False,
    )
    op.create_index(
        "ix_sale_returns_original_sale",
        "sale_returns",
        ["original_sale_id"],
        unique=False,
    )

    op.create_table(
        "sale_return_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_return_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("original_sale_line_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_capture_mode", sa.String(length=32), nullable=False),
        sa.Column("original_catalog_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("original_catalog_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("returned_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("returned_product_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("returned_product_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("returned_product_class_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("returned_product_class_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("returned_product_class_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("returned_quantity", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("refund_unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("refund_line_total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("disposition_code", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "returned_quantity > 0",
            name="ck_sale_return_lines_quantity_positive",
        ),
        sa.CheckConstraint(
            "refund_unit_price >= 0",
            name="ck_sale_return_lines_refund_unit_price_non_negative",
        ),
        sa.CheckConstraint(
            "refund_line_total_amount >= 0",
            name="ck_sale_return_lines_refund_line_total_non_negative",
        ),
        sa.CheckConstraint(
            "disposition_code IN ('RESTOCK_COUNTER', 'RESTOCK_BACKROOM', 'SEND_TO_WASTE')",
            name="ck_sale_return_lines_disposition_valid",
        ),
        sa.ForeignKeyConstraint(["sale_return_id"], ["sale_returns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["original_sale_line_id"], ["sale_lines.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["returned_product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["returned_product_class_id"], ["product_classes.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sale_return_lines")),
        sa.UniqueConstraint(
            "sale_return_id",
            "line_number",
            name="uq_sale_return_lines_line_number",
        ),
    )
    op.create_index(
        "ix_sale_return_lines_sale_return",
        "sale_return_lines",
        ["sale_return_id"],
        unique=False,
    )
    op.create_index(
        "ix_sale_return_lines_original_sale_line",
        "sale_return_lines",
        ["original_sale_line_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_sale_return_lines_original_sale_line", table_name="sale_return_lines")
    op.drop_index("ix_sale_return_lines_sale_return", table_name="sale_return_lines")
    op.drop_table("sale_return_lines")

    op.drop_index("ix_sale_returns_original_sale", table_name="sale_returns")
    op.drop_index("ix_sale_returns_branch_created", table_name="sale_returns")
    op.drop_table("sale_returns")
