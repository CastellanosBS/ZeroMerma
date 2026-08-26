"""Add financial reconciliation documents.

Revision ID: 20260520_0032_fin_recon
Revises: 20260520_0031_inputs_supplies
Create Date: 2026-05-20 23:55:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260520_0032_fin_recon"
down_revision: str | None = "20260520_0031_inputs_supplies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "financial_reconciliations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("folio", sa.String(length=40), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_document_id", sa.UUID(), nullable=False),
        sa.Column("source_reference", sa.String(length=80), nullable=False),
        sa.Column("source_occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("workstation_id", sa.UUID(), nullable=False),
        sa.Column("operator_user_id", sa.UUID(), nullable=True),
        sa.Column("payment_method_code", sa.String(length=40), nullable=False),
        sa.Column("expected_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("actual_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("difference_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reason_code", sa.String(length=60), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("evidence_note", sa.Text(), nullable=True),
        sa.Column("has_evidence", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column("resolved_by_user_id", sa.UUID(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "actual_amount >= 0",
            name=op.f("ck_financial_reconciliations_actual_non_negative"),
        ),
        sa.CheckConstraint(
            "difference_amount <> 0",
            name=op.f("ck_financial_reconciliations_difference_non_zero"),
        ),
        sa.CheckConstraint(
            "expected_amount >= 0",
            name=op.f("ck_financial_reconciliations_expected_non_negative"),
        ),
        sa.CheckConstraint(
            "reason_code IS NULL OR reason_code IN ("
            "'COUNTING_ERROR', "
            "'CASH_MISSING', "
            "'CASH_OVER', "
            "'CARD_SETTLEMENT_DIFFERENCE', "
            "'REFUND_RECORDED', "
            "'OPERATIONAL_PAYMENT_MISSING', "
            "'DEPOSIT_DIFFERENCE', "
            "'DUPLICATE_TICKET', "
            "'CORRECTION_APPLIED', "
            "'OTHER'"
            ")",
            name=op.f("ck_financial_reconciliations_reason_valid"),
        ),
        sa.CheckConstraint(
            "source_type IN ("
            "'CASH_CUT', "
            "'PAYMENT_SETTLEMENT', "
            "'DEPOSIT', "
            "'RETURN_REFUND', "
            "'OPERATIONAL_PAYMENT', "
            "'CORRECTION'"
            ")",
            name=op.f("ck_financial_reconciliations_source_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'IN_REVIEW', 'RECONCILED', 'VOIDED')",
            name=op.f("ck_financial_reconciliations_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name=op.f("fk_financial_reconciliations_branch_id_branches"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_financial_reconciliations_created_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["operator_user_id"],
            ["users.id"],
            name=op.f("fk_financial_reconciliations_operator_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_user_id"],
            ["users.id"],
            name=op.f("fk_financial_reconciliations_resolved_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workstation_id"],
            ["workstations.id"],
            name=op.f("fk_financial_reconciliations_workstation_id_workstations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_financial_reconciliations")),
        sa.UniqueConstraint("folio", name=op.f("uq_financial_reconciliations_folio")),
        sa.UniqueConstraint(
            "source_type",
            "source_document_id",
            "payment_method_code",
            name="uq_financial_reconciliations_source_method",
        ),
    )
    op.create_index(
        op.f("ix_financial_reconciliations_branch_status"),
        "financial_reconciliations",
        ["branch_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_financial_reconciliations_source"),
        "financial_reconciliations",
        ["source_type", "source_document_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_financial_reconciliations_source"),
        table_name="financial_reconciliations",
    )
    op.drop_index(
        op.f("ix_financial_reconciliations_branch_status"),
        table_name="financial_reconciliations",
    )
    op.drop_table("financial_reconciliations")
