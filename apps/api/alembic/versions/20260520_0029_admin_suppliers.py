"""Add admin suppliers module.

Revision ID: 20260520_0029_admin_suppliers
Revises: 20260520_0028_admin_waste
Create Date: 2026-05-20 22:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260520_0029_admin_suppliers"
down_revision: str | None = "20260520_0028_admin_waste"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("legal_name", sa.String(length=200), nullable=False),
        sa.Column("commercial_name", sa.String(length=200), nullable=True),
        sa.Column("tax_id", sa.String(length=40), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("fiscal_address", sa.String(length=320), nullable=True),
        sa.Column("fiscal_regime", sa.String(length=120), nullable=True),
        sa.Column("payment_fiscal_email", sa.String(length=320), nullable=True),
        sa.Column("payment_terms_type", sa.String(length=32), nullable=False),
        sa.Column("credit_days", sa.Integer(), nullable=False),
        sa.Column("default_currency", sa.String(length=3), nullable=False),
        sa.Column("minimum_order_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("lead_time_days", sa.Integer(), nullable=False),
        sa.Column("delivery_notes", sa.Text(), nullable=True),
        sa.Column("purchase_notes", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "category IN ('RAW_MATERIALS', 'PACKAGING', 'SERVICES', 'MIXED', 'OTHER')",
            name=op.f("ck_suppliers_category_valid"),
        ),
        sa.CheckConstraint("credit_days >= 0", name=op.f("ck_suppliers_credit_days_non_negative")),
        sa.CheckConstraint("lead_time_days >= 0", name=op.f("ck_suppliers_lead_time_non_negative")),
        sa.CheckConstraint(
            "minimum_order_amount IS NULL OR minimum_order_amount >= 0",
            name=op.f("ck_suppliers_minimum_order_non_negative"),
        ),
        sa.CheckConstraint(
            "payment_terms_type IN ('CASH', 'CREDIT', 'TRANSFER', 'MIXED')",
            name=op.f("ck_suppliers_payment_terms_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'BLOCKED')", name=op.f("ck_suppliers_status_valid")
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("tax_id"),
    )
    op.create_table(
        "supplier_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("role", sa.String(length=120), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("whatsapp", sa.String(length=40), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "email IS NULL OR position('@' in email) > 1",
            name=op.f("ck_supplier_contacts_email_shape"),
        ),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "supplier_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_sku", sa.String(length=80), nullable=True),
        sa.Column("purchase_uom", sa.String(length=32), nullable=True),
        sa.Column("last_known_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("minimum_order_qty", sa.Numeric(12, 3), nullable=True),
        sa.Column("lead_time_days", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "last_known_price IS NULL OR last_known_price >= 0",
            name=op.f("ck_supplier_products_last_price_non_negative"),
        ),
        sa.CheckConstraint(
            "lead_time_days >= 0", name=op.f("ck_supplier_products_lead_time_non_negative")
        ),
        sa.CheckConstraint(
            "minimum_order_qty IS NULL OR minimum_order_qty >= 0",
            name=op.f("ck_supplier_products_minimum_qty_non_negative"),
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "supplier_id", "product_id", name=op.f("uq_supplier_products_supplier_product")
        ),
    )
    op.create_table(
        "supplier_branches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("delivery_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "supplier_id", "branch_id", name=op.f("uq_supplier_branches_supplier_branch")
        ),
    )


def downgrade() -> None:
    op.drop_table("supplier_branches")
    op.drop_table("supplier_products")
    op.drop_table("supplier_contacts")
    op.drop_table("suppliers")
