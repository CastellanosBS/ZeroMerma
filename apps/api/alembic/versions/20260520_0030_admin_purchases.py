"""Add admin purchase and receiving documents.

Revision ID: 20260520_0030_admin_purchases
Revises: 20260520_0029_admin_suppliers
Create Date: 2026-05-20 22:50:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260520_0030_admin_purchases"
down_revision: str | None = "20260520_0029_admin_suppliers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_inventory_movements_type_valid"), "inventory_movements", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_inventory_movements_type_valid"),
        "inventory_movements",
        "movement_type IN ("
        "'MANUAL_ADJUSTMENT', "
        "'STOCK_COUNT_ADJUSTMENT', "
        "'TRANSFER_DISPATCH', "
        "'TRANSFER_RECEIPT', "
        "'PRODUCTION_CONSUMPTION', "
        "'PRODUCTION_OUTPUT', "
        "'WASTE_RECORD', "
        "'PURCHASE_RECEIPT'"
        ")",
    )

    op.create_table(
        "purchase_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("folio", sa.String(length=40), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receiving_branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_document_type", sa.String(length=32), nullable=True),
        sa.Column("external_document_number", sa.String(length=120), nullable=True),
        sa.Column("external_document_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("document_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("confirmed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cancelled_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "document_type IN ('PURCHASE', 'DIRECT_ENTRY')",
            name=op.f("ck_purchase_documents_type_valid"),
        ),
        sa.CheckConstraint(
            "external_document_type IS NULL OR external_document_type IN "
            "('INVOICE', 'REMISSION', 'SUPPLIER_NOTE', 'PURCHASE_REFERENCE', 'OTHER')",
            name=op.f("ck_purchase_documents_external_type_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'ORDERED', 'PARTIALLY_RECEIVED', 'RECEIVED', 'CANCELLED')",
            name=op.f("ck_purchase_documents_status_valid"),
        ),
        sa.ForeignKeyConstraint(["cancelled_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["confirmed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["receiving_branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("folio"),
    )
    op.create_index(
        op.f("ix_purchase_documents_branch_id"),
        "purchase_documents",
        ["receiving_branch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_purchase_documents_supplier_id"),
        "purchase_documents",
        ["supplier_id"],
        unique=False,
    )

    op.create_table(
        "purchase_document_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("product_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("product_kind_snapshot", sa.String(length=32), nullable=False),
        sa.Column("unit_of_measure", sa.String(length=32), nullable=False),
        sa.Column("ordered_quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("received_quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 4), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "ordered_quantity > 0", name=op.f("ck_purchase_lines_ordered_quantity_positive")
        ),
        sa.CheckConstraint(
            "received_quantity >= 0", name=op.f("ck_purchase_lines_received_quantity_non_negative")
        ),
        sa.CheckConstraint("unit_cost >= 0", name=op.f("ck_purchase_lines_unit_cost_non_negative")),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["purchase_document_id"], ["purchase_documents.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "purchase_document_id",
            "line_number",
            name=op.f("uq_purchase_lines_document_line_number"),
        ),
    )
    op.create_index(
        op.f("ix_purchase_document_lines_product_id"),
        "purchase_document_lines",
        ["product_id"],
        unique=False,
    )

    op.create_table(
        "purchase_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("folio", sa.String(length=40), nullable=False),
        sa.Column("purchase_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("received_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("has_discrepancy", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["purchase_document_id"], ["purchase_documents.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["received_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("folio"),
    )
    op.create_index(
        op.f("ix_purchase_receipts_document_id"),
        "purchase_receipts",
        ["purchase_document_id"],
        unique=False,
    )

    op.create_table(
        "purchase_receipt_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_receipt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_line_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("received_quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 4), nullable=False),
        sa.Column("discrepancy_reason", sa.String(length=160), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "received_quantity >= 0", name=op.f("ck_purchase_receipt_lines_quantity_non_negative")
        ),
        sa.CheckConstraint(
            "unit_cost >= 0", name=op.f("ck_purchase_receipt_lines_unit_cost_non_negative")
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["purchase_line_id"], ["purchase_document_lines.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["purchase_receipt_id"], ["purchase_receipts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "purchase_receipt_id",
            "purchase_line_id",
            name=op.f("uq_purchase_receipt_lines_receipt_line"),
        ),
    )
    op.create_index(
        op.f("ix_purchase_receipt_lines_product_id"),
        "purchase_receipt_lines",
        ["product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_purchase_receipt_lines_product_id"), table_name="purchase_receipt_lines")
    op.drop_table("purchase_receipt_lines")
    op.drop_index(op.f("ix_purchase_receipts_document_id"), table_name="purchase_receipts")
    op.drop_table("purchase_receipts")
    op.drop_index(
        op.f("ix_purchase_document_lines_product_id"), table_name="purchase_document_lines"
    )
    op.drop_table("purchase_document_lines")
    op.drop_index(op.f("ix_purchase_documents_supplier_id"), table_name="purchase_documents")
    op.drop_index(op.f("ix_purchase_documents_branch_id"), table_name="purchase_documents")
    op.drop_table("purchase_documents")

    op.drop_constraint(
        op.f("ck_inventory_movements_type_valid"), "inventory_movements", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_inventory_movements_type_valid"),
        "inventory_movements",
        "movement_type IN ("
        "'MANUAL_ADJUSTMENT', "
        "'STOCK_COUNT_ADJUSTMENT', "
        "'TRANSFER_DISPATCH', "
        "'TRANSFER_RECEIPT', "
        "'PRODUCTION_CONSUMPTION', "
        "'PRODUCTION_OUTPUT', "
        "'WASTE_RECORD'"
        ")",
    )
