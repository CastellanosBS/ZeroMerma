"""Add Phase 7B cash close reconciliation persistence and close document types.

Revision ID: 0008_phase_7b_cash_close
Revises: 0007_phase_7a_cash_close
Create Date: 2026-04-09 23:55:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008_phase_7b_cash_close"
down_revision: str | None = "0007_phase_7a_cash_close"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_sale_lines_physical_attribution_status_valid",
        "sale_lines",
        type_="check",
    )
    op.create_check_constraint(
        "ck_sale_lines_physical_attribution_status_valid",
        "sale_lines",
        "physical_attribution_status IN "
        "('PENDING_RECONCILIATION', 'DIRECT_ASSIGNED', 'RECONCILED')",
    )

    op.drop_constraint(
        "ck_operation_documents_document_type_valid",
        "operation_documents",
        type_="check",
    )
    op.create_check_constraint(
        "ck_operation_documents_document_type_valid",
        "operation_documents",
        "document_type IN ("
        "'COUNTER_TRANSFER', "
        "'WASTE_RECORD', "
        "'BRANCH_TRANSFER_SHIPMENT', "
        "'BRANCH_TRANSFER_RECEIPT', "
        "'CLOSE_COUNTER_ADJUSTMENT', "
        "'CLOSE_WASTE_ADJUSTMENT'"
        ")",
    )

    op.add_column(
        "cash_session_close_class_reconciliations",
        sa.Column("auto_attributed_quantity", sa.Numeric(precision=12, scale=3), nullable=True),
    )
    op.add_column(
        "cash_session_close_class_reconciliations",
        sa.Column(
            "resolution_status",
            sa.String(length=24),
            nullable=False,
            server_default="COUNT_REQUIRED",
        ),
    )
    op.create_check_constraint(
        "ck_cash_session_close_class_reconciliations_auto_non_negative",
        "cash_session_close_class_reconciliations",
        "auto_attributed_quantity IS NULL OR auto_attributed_quantity >= 0",
    )
    op.create_check_constraint(
        "ck_cash_session_close_class_reconciliations_resolution_status_valid",
        "cash_session_close_class_reconciliations",
        "resolution_status IN ('COUNT_REQUIRED', 'AUTO_RESOLVED', 'MANUAL_RESOLVED', 'UNRESOLVED')",
    )
    op.alter_column(
        "cash_session_close_class_reconciliations",
        "resolution_status",
        server_default=None,
    )

    op.create_table(
        "cash_session_close_discrepancy_resolutions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cash_session_close_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("product_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("product_class_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_class_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("product_class_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("expected_quantity", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("counted_quantity", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("discrepancy_quantity", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("resolution_type", sa.String(length=40), nullable=False),
        sa.Column("reason_code", sa.String(length=40), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("generated_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "expected_quantity >= 0",
            name="ck_cash_session_close_discrepancy_resolutions_expected_non_negative",
        ),
        sa.CheckConstraint(
            "counted_quantity >= 0",
            name="ck_cash_session_close_discrepancy_resolutions_counted_non_negative",
        ),
        sa.CheckConstraint(
            "discrepancy_quantity <> 0",
            name="ck_cash_session_close_discrepancy_resolutions_non_zero",
        ),
        sa.CheckConstraint(
            "resolution_type IN ('CLOSE_COUNTER_ADJUSTMENT', 'CLOSE_WASTE_ADJUSTMENT')",
            name="ck_cash_session_close_discrepancy_resolutions_type_valid",
        ),
        sa.CheckConstraint(
            "reason_code IN ("
            "'COUNT_ERROR', "
            "'UNREGISTERED_WASTE', "
            "'UNREGISTERED_PASS_TO_COUNTER', "
            "'COUNTER_SHORTAGE', "
            "'COUNTER_OVERAGE', "
            "'OTHER'"
            ")",
            name="ck_cash_session_close_discrepancy_resolutions_reason_valid",
        ),
        sa.ForeignKeyConstraint(
            ["cash_session_close_id"],
            ["cash_session_closes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_class_id"], ["product_classes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["generated_document_id"],
            ["operation_documents.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_cash_session_close_discrepancy_resolutions"),
        ),
    )
    op.create_index(
        "ix_cash_session_close_discrepancy_resolutions_close_id",
        "cash_session_close_discrepancy_resolutions",
        ["cash_session_close_id"],
        unique=False,
    )

    op.create_table(
        "cash_session_close_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cash_session_close_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issue_level", sa.String(length=16), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "issue_level IN ('BLOCKER', 'WARNING')",
            name="ck_cash_session_close_issues_level_valid",
        ),
        sa.ForeignKeyConstraint(
            ["cash_session_close_id"],
            ["cash_session_closes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cash_session_close_issues")),
    )
    op.create_index(
        "ix_cash_session_close_issues_close_id",
        "cash_session_close_issues",
        ["cash_session_close_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cash_session_close_issues_close_id",
        table_name="cash_session_close_issues",
    )
    op.drop_table("cash_session_close_issues")

    op.drop_index(
        "ix_cash_session_close_discrepancy_resolutions_close_id",
        table_name="cash_session_close_discrepancy_resolutions",
    )
    op.drop_table("cash_session_close_discrepancy_resolutions")

    op.drop_constraint(
        "ck_cash_session_close_class_reconciliations_resolution_status_valid",
        "cash_session_close_class_reconciliations",
        type_="check",
    )
    op.drop_constraint(
        "ck_cash_session_close_class_reconciliations_auto_non_negative",
        "cash_session_close_class_reconciliations",
        type_="check",
    )
    op.drop_column("cash_session_close_class_reconciliations", "resolution_status")
    op.drop_column("cash_session_close_class_reconciliations", "auto_attributed_quantity")

    op.drop_constraint(
        "ck_operation_documents_document_type_valid",
        "operation_documents",
        type_="check",
    )
    op.create_check_constraint(
        "ck_operation_documents_document_type_valid",
        "operation_documents",
        "document_type IN ("
        "'COUNTER_TRANSFER', "
        "'WASTE_RECORD', "
        "'BRANCH_TRANSFER_SHIPMENT', "
        "'BRANCH_TRANSFER_RECEIPT'"
        ")",
    )

    op.drop_constraint(
        "ck_sale_lines_physical_attribution_status_valid",
        "sale_lines",
        type_="check",
    )
    op.create_check_constraint(
        "ck_sale_lines_physical_attribution_status_valid",
        "sale_lines",
        "physical_attribution_status IN ('PENDING_RECONCILIATION', 'DIRECT_ASSIGNED')",
    )
