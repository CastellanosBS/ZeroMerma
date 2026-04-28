"""Remove OTHER as an allowed payment method across sales and operational flows.

Revision ID: 0014_remove_other_payment_method
Revises: 0013_discounts_module
Create Date: 2026-04-13 12:40:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_remove_other_payment_method"
down_revision: str | None = "0013_discounts_module"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            UPDATE sale_payments
            SET payment_method_code = 'CARD'
            WHERE payment_method_code = 'OTHER'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE cash_movements
            SET payment_method_code = 'CARD'
            WHERE payment_method_code = 'OTHER'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE customer_order_payments
            SET payment_method_code = 'CARD'
            WHERE payment_method_code = 'OTHER'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE operational_payments
            SET payment_method_code = 'CARD'
            WHERE payment_method_code = 'OTHER'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE operational_discounts
            SET payment_method_code = 'CARD'
            WHERE payment_method_code = 'OTHER'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE cash_session_close_payment_method_counts AS card_rows
            SET counted_amount = card_rows.counted_amount + other_rows.counted_amount
            FROM cash_session_close_payment_method_counts AS other_rows
            WHERE other_rows.payment_method_code = 'OTHER'
              AND card_rows.cash_session_close_id = other_rows.cash_session_close_id
              AND card_rows.payment_method_code = 'CARD'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM cash_session_close_payment_method_counts AS other_rows
            WHERE other_rows.payment_method_code = 'OTHER'
              AND EXISTS (
                SELECT 1
                FROM cash_session_close_payment_method_counts AS card_rows
                WHERE card_rows.cash_session_close_id = other_rows.cash_session_close_id
                  AND card_rows.payment_method_code = 'CARD'
              )
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE cash_session_close_payment_method_counts
            SET payment_method_code = 'CARD'
            WHERE payment_method_code = 'OTHER'
            """
        )
    )

    op.drop_constraint(
        "ck_customer_order_payments_method_valid",
        "customer_order_payments",
        type_="check",
    )
    op.create_check_constraint(
        "ck_customer_order_payments_method_valid",
        "customer_order_payments",
        "payment_method_code IN ('CASH', 'CARD', 'MIXED')",
    )

    op.drop_constraint(
        "ck_operational_payments_method_valid",
        "operational_payments",
        type_="check",
    )
    op.create_check_constraint(
        "ck_operational_payments_method_valid",
        "operational_payments",
        "payment_method_code IN ('CASH', 'CARD', 'MIXED')",
    )

    op.drop_constraint(
        "ck_operational_discounts_method_valid",
        "operational_discounts",
        type_="check",
    )
    op.create_check_constraint(
        "ck_operational_discounts_method_valid",
        "operational_discounts",
        "payment_method_code IN ('CASH', 'CARD', 'MIXED')",
    )

    op.drop_constraint(
        "ck_cash_session_close_payment_method_counts_method_valid",
        "cash_session_close_payment_method_counts",
        type_="check",
    )
    op.create_check_constraint(
        "ck_cash_session_close_payment_method_counts_method_valid",
        "cash_session_close_payment_method_counts",
        "payment_method_code IN ('CASH', 'CARD', 'MIXED')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_cash_session_close_payment_method_counts_method_valid",
        "cash_session_close_payment_method_counts",
        type_="check",
    )
    op.create_check_constraint(
        "ck_cash_session_close_payment_method_counts_method_valid",
        "cash_session_close_payment_method_counts",
        "payment_method_code IN ('CASH', 'CARD', 'MIXED', 'OTHER')",
    )

    op.drop_constraint(
        "ck_operational_discounts_method_valid",
        "operational_discounts",
        type_="check",
    )
    op.create_check_constraint(
        "ck_operational_discounts_method_valid",
        "operational_discounts",
        "payment_method_code IN ('CASH', 'CARD', 'MIXED', 'OTHER')",
    )

    op.drop_constraint(
        "ck_operational_payments_method_valid",
        "operational_payments",
        type_="check",
    )
    op.create_check_constraint(
        "ck_operational_payments_method_valid",
        "operational_payments",
        "payment_method_code IN ('CASH', 'CARD', 'MIXED', 'OTHER')",
    )

    op.drop_constraint(
        "ck_customer_order_payments_method_valid",
        "customer_order_payments",
        type_="check",
    )
    op.create_check_constraint(
        "ck_customer_order_payments_method_valid",
        "customer_order_payments",
        "payment_method_code IN ('CASH', 'CARD', 'MIXED', 'OTHER')",
    )
