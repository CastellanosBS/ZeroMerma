"""Create operational discounts module schema.

Revision ID: 0013_discounts_module
Revises: 0012_payments_module
Create Date: 2026-04-12 18:20:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_discounts_module"
down_revision: str | None = "0012_payments_module"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "operational_discount_categories",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "code IN ("
            "'EMPLOYEE_INSURANCE', "
            "'EMPLOYEE_LOAN', "
            "'INTERNAL_CHARGE', "
            "'PAYROLL_ADVANCE_ADJUSTMENT', "
            "'OTHER'"
            ")",
            name="ck_operational_discount_categories_code_valid",
        ),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_operational_discount_categories")),
    )

    op.create_table(
        "operational_discounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workstation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("active_cash_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_name", sa.String(length=160), nullable=False),
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
            name="ck_operational_discounts_status_valid",
        ),
        sa.CheckConstraint(
            "payment_method_code IN ('CASH', 'CARD', 'MIXED', 'OTHER')",
            name="ck_operational_discounts_method_valid",
        ),
        sa.CheckConstraint(
            "total_amount > 0",
            name="ck_operational_discounts_total_positive",
        ),
        sa.CheckConstraint(
            "cash_amount >= 0",
            name="ck_operational_discounts_cash_non_negative",
        ),
        sa.CheckConstraint(
            "non_cash_amount >= 0",
            name="ck_operational_discounts_non_cash_non_negative",
        ),
        sa.CheckConstraint(
            "cash_amount + non_cash_amount = total_amount",
            name="ck_operational_discounts_amount_split_matches_total",
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
            ["operational_discount_categories.code"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_operational_discounts")),
    )
    op.create_index(
        "ix_operational_discounts_branch_created",
        "operational_discounts",
        ["branch_id", "created_at_utc"],
        unique=False,
    )
    op.create_index(
        "ix_operational_discounts_cash_session_created",
        "operational_discounts",
        ["active_cash_session_id", "created_at_utc"],
        unique=False,
    )
    op.create_index(
        "ix_operational_discounts_method",
        "operational_discounts",
        ["payment_method_code"],
        unique=False,
    )

    categories_table = sa.table(
        "operational_discount_categories",
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("display_order", sa.Integer()),
    )
    op.bulk_insert(
        categories_table,
        [
            {
                "code": "EMPLOYEE_INSURANCE",
                "name": "Seguro del empleado",
                "is_active": True,
                "display_order": 10,
            },
            {
                "code": "EMPLOYEE_LOAN",
                "name": "Prestamo del empleado",
                "is_active": True,
                "display_order": 20,
            },
            {
                "code": "INTERNAL_CHARGE",
                "name": "Cargo interno",
                "is_active": True,
                "display_order": 30,
            },
            {
                "code": "PAYROLL_ADVANCE_ADJUSTMENT",
                "name": "Ajuste de adelanto de nomina",
                "is_active": True,
                "display_order": 40,
            },
            {
                "code": "OTHER",
                "name": "Otro",
                "is_active": True,
                "display_order": 50,
            },
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM cash_movements "
            "WHERE movement_type = 'OPERATIONAL_DISCOUNT' AND sale_id IS NULL"
        )
    )
    op.drop_index("ix_operational_discounts_method", table_name="operational_discounts")
    op.drop_index(
        "ix_operational_discounts_cash_session_created",
        table_name="operational_discounts",
    )
    op.drop_index("ix_operational_discounts_branch_created", table_name="operational_discounts")
    op.drop_table("operational_discounts")
    op.drop_table("operational_discount_categories")
