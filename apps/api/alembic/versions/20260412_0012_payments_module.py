"""Create operational payments module schema.

Revision ID: 0012_payments_module
Revises: 0011_returns_module
Create Date: 2026-04-12 15:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_payments_module"
down_revision: str | None = "0011_returns_module"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "cash_movements",
        "sale_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    op.create_table(
        "operational_payment_categories",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "code IN ('GAS', 'SUPPLIER', 'SERVICES', 'LOGISTICS', 'PURCHASE', 'OTHER')",
            name="ck_operational_payment_categories_code_valid",
        ),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_operational_payment_categories")),
    )

    op.create_table(
        "operational_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workstation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("active_cash_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payee_name", sa.String(length=160), nullable=False),
        sa.Column("concept", sa.String(length=240), nullable=False),
        sa.Column("category_code", sa.String(length=40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("payment_method_code", sa.String(length=40), nullable=False),
        sa.Column(
            "currency_code", sa.String(length=3), nullable=False, server_default=sa.text("'MXN'")
        ),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("cash_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("non_cash_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("committed_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('COMMITTED')",
            name="ck_operational_payments_status_valid",
        ),
        sa.CheckConstraint(
            "payment_method_code IN ('CASH', 'CARD', 'MIXED', 'OTHER')",
            name="ck_operational_payments_method_valid",
        ),
        sa.CheckConstraint(
            "total_amount > 0",
            name="ck_operational_payments_total_positive",
        ),
        sa.CheckConstraint(
            "cash_amount >= 0",
            name="ck_operational_payments_cash_non_negative",
        ),
        sa.CheckConstraint(
            "non_cash_amount >= 0",
            name="ck_operational_payments_non_cash_non_negative",
        ),
        sa.CheckConstraint(
            "cash_amount + non_cash_amount = total_amount",
            name="ck_operational_payments_amount_split_matches_total",
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workstation_id"], ["workstations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["active_cash_session_id"],
            ["cash_sessions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["category_code"],
            ["operational_payment_categories.code"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_operational_payments")),
    )
    op.create_index(
        "ix_operational_payments_branch_created",
        "operational_payments",
        ["branch_id", "created_at_utc"],
        unique=False,
    )
    op.create_index(
        "ix_operational_payments_cash_session_created",
        "operational_payments",
        ["active_cash_session_id", "created_at_utc"],
        unique=False,
    )
    op.create_index(
        "ix_operational_payments_method",
        "operational_payments",
        ["payment_method_code"],
        unique=False,
    )

    categories_table = sa.table(
        "operational_payment_categories",
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("display_order", sa.Integer()),
    )
    op.bulk_insert(
        categories_table,
        [
            {"code": "GAS", "name": "Gasolina", "is_active": True, "display_order": 10},
            {"code": "SUPPLIER", "name": "Proveedor", "is_active": True, "display_order": 20},
            {"code": "SERVICES", "name": "Servicios", "is_active": True, "display_order": 30},
            {"code": "LOGISTICS", "name": "Logistica", "is_active": True, "display_order": 40},
            {"code": "PURCHASE", "name": "Compra urgente", "is_active": True, "display_order": 50},
            {"code": "OTHER", "name": "Otro", "is_active": True, "display_order": 60},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_operational_payments_method", table_name="operational_payments")
    op.drop_index("ix_operational_payments_cash_session_created", table_name="operational_payments")
    op.drop_index("ix_operational_payments_branch_created", table_name="operational_payments")
    op.drop_table("operational_payments")
    op.drop_table("operational_payment_categories")

    op.execute(
        sa.text(
            "DELETE FROM cash_movements "
            "WHERE movement_type = 'OPERATIONAL_PAYMENT' AND sale_id IS NULL"
        )
    )
    op.alter_column(
        "cash_movements",
        "sale_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
