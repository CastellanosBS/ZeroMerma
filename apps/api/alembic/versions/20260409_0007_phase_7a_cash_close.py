"""Add Phase 7A cash close foundation tables with payment-method close counts.

Revision ID: 0007_phase_7a_cash_close
Revises: 0006_phase_4a_corrections
Create Date: 2026-04-09 23:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_phase_7a_cash_close"
down_revision: str | None = "0006_phase_4a_corrections"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cash_session_closes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cash_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workstation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("closed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("opening_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total_cash_in", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total_cash_out", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("expected_cash_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("counted_cash_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("cash_variance_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("reconciliation_status", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("started_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("committed_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('PREVIEW', 'READY', 'COMMITTED')",
            name="ck_cash_session_closes_status_valid",
        ),
        sa.CheckConstraint(
            "reconciliation_status IN ('NOT_EVALUATED', 'PENDING', 'BLOCKED', 'READY')",
            name="ck_cash_session_closes_reconciliation_status_valid",
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cash_session_id"], ["cash_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["closed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workstation_id"], ["workstations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cash_session_closes")),
        sa.UniqueConstraint(
            "cash_session_id",
            name="uq_cash_session_closes_cash_session_id",
        ),
    )
    op.create_index(
        "ix_cash_session_closes_cash_session_id",
        "cash_session_closes",
        ["cash_session_id"],
        unique=False,
    )

    op.create_table(
        "cash_session_close_payment_method_counts",
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
        "cash_session_close_payment_method_counts",
        ["cash_session_close_id"],
        unique=False,
    )

    op.create_table(
        "cash_session_close_product_counts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cash_session_close_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("product_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("product_class_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_class_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("product_class_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("bucket_code", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "quantity >= 0",
            name="ck_cash_session_close_product_counts_quantity_non_negative",
        ),
        sa.CheckConstraint(
            "bucket_code IN ('BACKROOM', 'COUNTER', 'IN_TRANSIT', 'WASTE')",
            name="ck_cash_session_close_product_counts_bucket_code_valid",
        ),
        sa.ForeignKeyConstraint(
            ["cash_session_close_id"],
            ["cash_session_closes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["product_class_id"], ["product_classes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cash_session_close_product_counts")),
    )
    op.create_index(
        "ix_cash_session_close_product_counts_close_id",
        "cash_session_close_product_counts",
        ["cash_session_close_id"],
        unique=False,
    )

    op.create_table(
        "cash_session_close_class_reconciliations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cash_session_close_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_class_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_class_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("product_class_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("expected_quantity", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("attributed_quantity", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("variance_quantity", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "expected_quantity >= 0",
            name="ck_cash_session_close_class_reconciliations_expected_non_negative",
        ),
        sa.CheckConstraint(
            "attributed_quantity IS NULL OR attributed_quantity >= 0",
            name="ck_cash_session_close_class_reconciliations_attributed_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["cash_session_close_id"],
            ["cash_session_closes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["product_class_id"], ["product_classes.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_cash_session_close_class_reconciliations"),
        ),
    )
    op.create_index(
        "ix_cash_session_close_class_reconciliations_close_id",
        "cash_session_close_class_reconciliations",
        ["cash_session_close_id"],
        unique=False,
    )

    op.create_table(
        "cash_session_close_reconciliation_attributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cash_session_close_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("class_reconciliation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("product_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("product_class_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_class_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("product_class_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("attributed_quantity", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "attributed_quantity > 0",
            name="ck_cash_session_close_reconciliation_attributions_quantity_positive",
        ),
        sa.ForeignKeyConstraint(
            ["cash_session_close_id"],
            ["cash_session_closes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["class_reconciliation_id"],
            ["cash_session_close_class_reconciliations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["product_class_id"], ["product_classes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_cash_session_close_reconciliation_attributions"),
        ),
    )
    op.create_index(
        "ix_cash_session_close_reconciliation_attr_class_id",
        "cash_session_close_reconciliation_attributions",
        ["class_reconciliation_id"],
        unique=False,
    )

    op.create_table(
        "branch_counter_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_cash_session_close_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("snapshot_type", sa.String(length=32), nullable=False),
        sa.Column("captured_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("captured_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "snapshot_type IN ('CLOSE_BASELINE')",
            name="ck_branch_counter_snapshots_type_valid",
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["captured_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_cash_session_close_id"],
            ["cash_session_closes.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_branch_counter_snapshots")),
    )
    op.create_index(
        "ix_branch_counter_snapshots_branch_captured_at",
        "branch_counter_snapshots",
        ["branch_id", "captured_at_utc"],
        unique=False,
    )

    op.create_table(
        "branch_counter_snapshot_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("product_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("product_class_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_class_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("product_class_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("bucket_code", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "quantity >= 0",
            name="ck_branch_counter_snapshot_lines_quantity_non_negative",
        ),
        sa.CheckConstraint(
            "bucket_code IN ('BACKROOM', 'COUNTER', 'IN_TRANSIT', 'WASTE')",
            name="ck_branch_counter_snapshot_lines_bucket_code_valid",
        ),
        sa.ForeignKeyConstraint(
            ["product_class_id"],
            ["product_classes.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["branch_counter_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_branch_counter_snapshot_lines")),
    )
    op.create_index(
        "ix_branch_counter_snapshot_lines_snapshot_id",
        "branch_counter_snapshot_lines",
        ["snapshot_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_branch_counter_snapshot_lines_snapshot_id",
        table_name="branch_counter_snapshot_lines",
    )
    op.drop_table("branch_counter_snapshot_lines")

    op.drop_index(
        "ix_branch_counter_snapshots_branch_captured_at",
        table_name="branch_counter_snapshots",
    )
    op.drop_table("branch_counter_snapshots")

    op.drop_index(
        "ix_cash_session_close_reconciliation_attr_class_id",
        table_name="cash_session_close_reconciliation_attributions",
    )
    op.drop_table("cash_session_close_reconciliation_attributions")

    op.drop_index(
        "ix_cash_session_close_class_reconciliations_close_id",
        table_name="cash_session_close_class_reconciliations",
    )
    op.drop_table("cash_session_close_class_reconciliations")

    op.drop_index(
        "ix_cash_session_close_product_counts_close_id",
        table_name="cash_session_close_product_counts",
    )
    op.drop_table("cash_session_close_product_counts")

    op.drop_index(
        "ix_cash_session_close_payment_method_counts_close_id",
        table_name="cash_session_close_payment_method_counts",
    )
    op.drop_table("cash_session_close_payment_method_counts")

    op.drop_index(
        "ix_cash_session_closes_cash_session_id",
        table_name="cash_session_closes",
    )
    op.drop_table("cash_session_closes")
