"""Allow independent order refund obligations and exact settled payment links.

Revision ID: 20261019_0045_refund_obligations
Revises: 20261019_0044_financial_ledger
"""

import sqlalchemy as sa
from alembic import op

revision = "20261019_0045_refund_obligations"
down_revision = "20261019_0044_financial_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE financial_operations DROP CONSTRAINT ck_financial_operations_source_valid;
        ALTER TABLE financial_operations ADD CONSTRAINT ck_financial_operations_source_valid CHECK (
          effect_code = kind AND (
            (kind = 'CASH_OPENING' AND source_type IN ('CASH_SESSION','OPENING_STATE')) OR
            (kind = 'SALE_COLLECTION' AND source_type = 'SALE') OR
            (kind IN ('ORDER_ADVANCE','ORDER_SETTLEMENT','ORDER_REFUND')
              AND source_type = 'ORDER_PAYMENT') OR
            (kind = 'ORDER_REFUND' AND source_type = 'ORDER_CANCELLATION') OR
            (kind = 'SALE_REFUND' AND source_type = 'SALE_RETURN') OR
            (kind = 'OPERATIONAL_PAYMENT' AND source_type = 'OPERATIONAL_PAYMENT') OR
            (kind = 'OPERATIONAL_CHARGE' AND source_type = 'OPERATIONAL_DISCOUNT') OR
            (kind = 'CASH_DEPOSIT' AND source_type = 'CASH_DEPOSIT') OR
            (kind = 'CASH_WITHDRAWAL' AND source_type = 'CASH_WITHDRAWAL') OR
            (kind = 'TECHNICAL_REVERSAL' AND source_type = 'FINANCIAL_ENTRY') OR
            (kind = 'OPENING_OBLIGATION' AND source_type = 'OPENING_STATE')
          ));
    """)
    op.add_column(
        "customer_order_payments", sa.Column("financial_entry_id", sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        "fk_customer_order_payments_financial_entry_id_financial_entries",
        "customer_order_payments",
        "financial_entries",
        ["financial_entry_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_customer_order_payments_financial_entry_id",
        "customer_order_payments",
        ["financial_entry_id"],
    )


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM financial_operations WHERE source_type = 'ORDER_CANCELLATION')
             OR EXISTS (SELECT 1 FROM customer_order_payments
                        WHERE financial_entry_id IS NOT NULL) THEN
            RAISE EXCEPTION 'Refund evidence requires a forward correction or verified restore';
          END IF;
        END $$;
    """)
    op.drop_constraint(
        "uq_customer_order_payments_financial_entry_id", "customer_order_payments", type_="unique"
    )
    op.drop_constraint(
        "fk_customer_order_payments_financial_entry_id_financial_entries",
        "customer_order_payments",
        type_="foreignkey",
    )
    op.drop_column("customer_order_payments", "financial_entry_id")
    op.execute("""
        ALTER TABLE financial_operations DROP CONSTRAINT ck_financial_operations_source_valid;
        ALTER TABLE financial_operations ADD CONSTRAINT ck_financial_operations_source_valid CHECK (
          effect_code = kind AND (
            (kind = 'CASH_OPENING' AND source_type IN ('CASH_SESSION','OPENING_STATE')) OR
            (kind = 'SALE_COLLECTION' AND source_type = 'SALE') OR
            (kind IN ('ORDER_ADVANCE','ORDER_SETTLEMENT','ORDER_REFUND')
              AND source_type = 'ORDER_PAYMENT') OR
            (kind = 'SALE_REFUND' AND source_type = 'SALE_RETURN') OR
            (kind = 'OPERATIONAL_PAYMENT' AND source_type = 'OPERATIONAL_PAYMENT') OR
            (kind = 'OPERATIONAL_CHARGE' AND source_type = 'OPERATIONAL_DISCOUNT') OR
            (kind = 'CASH_DEPOSIT' AND source_type = 'CASH_DEPOSIT') OR
            (kind = 'CASH_WITHDRAWAL' AND source_type = 'CASH_WITHDRAWAL') OR
            (kind = 'TECHNICAL_REVERSAL' AND source_type = 'FINANCIAL_ENTRY') OR
            (kind = 'OPENING_OBLIGATION' AND source_type = 'OPENING_STATE')
          ));
    """)
