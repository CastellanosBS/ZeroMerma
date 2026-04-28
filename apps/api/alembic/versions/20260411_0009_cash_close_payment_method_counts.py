"""Migrate cash close denomination rows into payment-method close counts.

Revision ID: 0009_cash_close_payment_methods
Revises: 0008_phase_7b_cash_close
Create Date: 2026-04-11 12:10:00.000000
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_cash_close_payment_methods"
down_revision: str | None = "0008_phase_7b_cash_close"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PAYMENT_METHOD_TABLE = "cash_session_close_payment_method_counts"
DENOMINATION_TABLE = "cash_session_close_denominations"
DENOMINATION_CATALOG_TABLE = "cash_close_denomination_catalog"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(PAYMENT_METHOD_TABLE):
        op.create_table(
            PAYMENT_METHOD_TABLE,
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("cash_session_close_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("payment_method_code", sa.String(length=40), nullable=False),
            sa.Column("currency_code", sa.String(length=3), nullable=False),
            sa.Column("counted_amount", sa.Numeric(precision=12, scale=2), nullable=False),
            sa.Column("expected_amount", sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column("variance_amount", sa.Numeric(precision=12, scale=2), nullable=True),
            sa.CheckConstraint(
                "payment_method_code IN ('CASH', 'CARD', 'MIXED', 'OTHER')",
                name="ck_cash_session_close_payment_method_counts_method_valid",
            ),
            sa.CheckConstraint(
                "counted_amount >= 0",
                name="ck_cash_session_close_payment_method_counts_counted_non_negative",
            ),
            sa.CheckConstraint(
                "expected_amount IS NULL OR expected_amount >= 0",
                name="ck_cash_session_close_payment_method_counts_expected_non_negative",
            ),
            sa.ForeignKeyConstraint(
                ["cash_session_close_id"],
                ["cash_session_closes.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint(
                "id",
                name=op.f("pk_cash_session_close_payment_method_counts"),
            ),
            sa.UniqueConstraint(
                "cash_session_close_id",
                "payment_method_code",
                name="uq_cash_session_close_payment_method_counts_close_method",
            ),
        )
        op.create_index(
            "ix_cash_session_close_payment_method_counts_close_id",
            PAYMENT_METHOD_TABLE,
            ["cash_session_close_id"],
            unique=False,
        )

    _backfill_cash_payment_rows(bind)

    inspector = sa.inspect(bind)
    if inspector.has_table(DENOMINATION_TABLE):
        op.drop_table(DENOMINATION_TABLE)
    inspector = sa.inspect(bind)
    if inspector.has_table(DENOMINATION_CATALOG_TABLE):
        op.drop_table(DENOMINATION_CATALOG_TABLE)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(DENOMINATION_CATALOG_TABLE):
        op.create_table(
            DENOMINATION_CATALOG_TABLE,
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("denomination_value", sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column("denomination_type", sa.String(length=16), nullable=False),
            sa.Column("currency_code", sa.String(length=3), nullable=False),
            sa.Column("display_order", sa.Integer(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.CheckConstraint(
                "denomination_value > 0",
                name="ck_cash_close_denomination_catalog_value_positive",
            ),
            sa.CheckConstraint(
                "denomination_type IN ('BILL', 'COIN')",
                name="ck_cash_close_denomination_catalog_type_valid",
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_cash_close_denomination_catalog")),
            sa.UniqueConstraint(
                "currency_code",
                "denomination_value",
                name="uq_cash_close_denomination_catalog_currency_value",
            ),
        )
        op.create_index(
            "ix_cash_close_denomination_catalog_active_order",
            DENOMINATION_CATALOG_TABLE,
            ["currency_code", "is_active", "display_order"],
            unique=False,
        )

    inspector = sa.inspect(bind)
    if not inspector.has_table(DENOMINATION_TABLE):
        op.create_table(
            DENOMINATION_TABLE,
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("cash_session_close_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("denomination_catalog_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("denomination_value", sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column("denomination_type", sa.String(length=16), nullable=False),
            sa.Column("currency_code", sa.String(length=3), nullable=False),
            sa.Column("unit_count", sa.Integer(), nullable=False),
            sa.Column("subtotal_amount", sa.Numeric(precision=12, scale=2), nullable=False),
            sa.CheckConstraint(
                "unit_count >= 0",
                name="ck_cash_session_close_denominations_unit_count_non_negative",
            ),
            sa.CheckConstraint(
                "subtotal_amount >= 0",
                name="ck_cash_session_close_denominations_subtotal_non_negative",
            ),
            sa.ForeignKeyConstraint(
                ["cash_session_close_id"],
                ["cash_session_closes.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["denomination_catalog_id"],
                [f"{DENOMINATION_CATALOG_TABLE}.id"],
                ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_cash_session_close_denominations")),
        )
        op.create_index(
            "ix_cash_session_close_denominations_close_id",
            DENOMINATION_TABLE,
            ["cash_session_close_id"],
            unique=False,
        )

    _restore_synthetic_denomination_rows(bind)

    inspector = sa.inspect(bind)
    if inspector.has_table(PAYMENT_METHOD_TABLE):
        op.drop_index(
            "ix_cash_session_close_payment_method_counts_close_id",
            table_name=PAYMENT_METHOD_TABLE,
        )
        op.drop_table(PAYMENT_METHOD_TABLE)


def _backfill_cash_payment_rows(bind: sa.Connection) -> None:
    close_rows = bind.execute(
        sa.text(
            """
            SELECT
              id,
              expected_cash_amount,
              counted_cash_amount,
              cash_variance_amount
            FROM cash_session_closes
            """
        )
    ).mappings().all()
    existing_close_ids = {
        row["cash_session_close_id"]
        for row in bind.execute(
            sa.text(
                f"""
                SELECT cash_session_close_id
                FROM {PAYMENT_METHOD_TABLE}
                WHERE payment_method_code = 'CASH'
                """
            )
        ).mappings()
    }

    payment_method_rows: list[dict[str, object]] = []
    for close_row in close_rows:
        close_id = close_row["id"]
        if close_id in existing_close_ids:
            continue

        counted_amount = close_row["counted_cash_amount"] or Decimal("0.00")
        expected_amount = close_row["expected_cash_amount"]
        variance_amount = (
            close_row["cash_variance_amount"]
            if close_row["cash_variance_amount"] is not None
            else counted_amount - expected_amount
        )
        payment_method_rows.append(
            {
                "id": uuid.uuid4(),
                "cash_session_close_id": close_id,
                "payment_method_code": "CASH",
                "currency_code": "MXN",
                "counted_amount": counted_amount,
                "expected_amount": expected_amount,
                "variance_amount": variance_amount,
            }
        )

    if payment_method_rows:
        payment_method_table = sa.table(
            PAYMENT_METHOD_TABLE,
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("cash_session_close_id", postgresql.UUID(as_uuid=True)),
            sa.column("payment_method_code", sa.String(length=40)),
            sa.column("currency_code", sa.String(length=3)),
            sa.column("counted_amount", sa.Numeric(precision=12, scale=2)),
            sa.column("expected_amount", sa.Numeric(precision=12, scale=2)),
            sa.column("variance_amount", sa.Numeric(precision=12, scale=2)),
        )
        op.bulk_insert(payment_method_table, payment_method_rows)


def _restore_synthetic_denomination_rows(bind: sa.Connection) -> None:
    close_rows = bind.execute(
        sa.text(
            f"""
            SELECT
              pm.cash_session_close_id,
              pm.counted_amount
            FROM {PAYMENT_METHOD_TABLE} pm
            WHERE pm.payment_method_code = 'CASH'
            """
        )
    ).mappings().all()
    if not close_rows:
        return

    catalog_rows_by_amount: dict[Decimal, uuid.UUID] = {}
    catalog_rows: list[dict[str, object]] = []
    denomination_rows: list[dict[str, object]] = []

    for display_order, close_row in enumerate(close_rows, start=10):
        counted_amount = close_row["counted_amount"] or Decimal("0.00")
        catalog_id = catalog_rows_by_amount.get(counted_amount)
        if catalog_id is None:
            catalog_id = uuid.uuid4()
            catalog_rows_by_amount[counted_amount] = catalog_id
            catalog_rows.append(
                {
                    "id": catalog_id,
                    "denomination_value": counted_amount,
                    "denomination_type": "BILL",
                    "currency_code": "MXN",
                    "display_order": display_order,
                    "is_active": True,
                }
            )

        denomination_rows.append(
            {
                "id": uuid.uuid4(),
                "cash_session_close_id": close_row["cash_session_close_id"],
                "denomination_catalog_id": catalog_id,
                "denomination_value": counted_amount,
                "denomination_type": "BILL",
                "currency_code": "MXN",
                "unit_count": 1,
                "subtotal_amount": counted_amount,
            }
        )

    if catalog_rows:
        catalog_table = sa.table(
            DENOMINATION_CATALOG_TABLE,
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("denomination_value", sa.Numeric(precision=10, scale=2)),
            sa.column("denomination_type", sa.String(length=16)),
            sa.column("currency_code", sa.String(length=3)),
            sa.column("display_order", sa.Integer()),
            sa.column("is_active", sa.Boolean()),
        )
        op.bulk_insert(catalog_table, catalog_rows)

    if denomination_rows:
        denomination_table = sa.table(
            DENOMINATION_TABLE,
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("cash_session_close_id", postgresql.UUID(as_uuid=True)),
            sa.column("denomination_catalog_id", postgresql.UUID(as_uuid=True)),
            sa.column("denomination_value", sa.Numeric(precision=10, scale=2)),
            sa.column("denomination_type", sa.String(length=16)),
            sa.column("currency_code", sa.String(length=3)),
            sa.column("unit_count", sa.Integer()),
            sa.column("subtotal_amount", sa.Numeric(precision=12, scale=2)),
        )
        op.bulk_insert(denomination_table, denomination_rows)
