"""Allow refund entries in order payments.

Revision ID: 20260417_0016_order_cancel
Revises: 20260416_0015_corr_dest
Create Date: 2026-04-17 18:10:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260417_0016_order_cancel"
down_revision: str | None = "20260416_0015_corr_dest"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_customer_order_payments_type_valid",
        "customer_order_payments",
        type_="check",
    )
    op.create_check_constraint(
        "ck_customer_order_payments_type_valid",
        "customer_order_payments",
        "payment_type IN ('ADVANCE', 'SETTLEMENT', 'REFUND')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_customer_order_payments_type_valid",
        "customer_order_payments",
        type_="check",
    )
    op.create_check_constraint(
        "ck_customer_order_payments_type_valid",
        "customer_order_payments",
        "payment_type IN ('ADVANCE', 'SETTLEMENT')",
    )
