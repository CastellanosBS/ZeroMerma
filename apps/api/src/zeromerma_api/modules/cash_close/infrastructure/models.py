from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from zeromerma_api.db.base import Base
from zeromerma_api.modules.cash_close.domain.constants import (
    BRANCH_COUNTER_SNAPSHOT_TYPE_CLOSE_BASELINE,
    CASH_CLOSE_CLASS_RESOLUTION_STATUS_COUNT_REQUIRED,
    CASH_CLOSE_DISCREPANCY_REASON_COUNT_ERROR,
    CASH_CLOSE_DISCREPANCY_RESOLUTION_TYPE_CLOSE_COUNTER_ADJUSTMENT,
    CASH_CLOSE_ISSUE_LEVEL_BLOCKER,
    CASH_CLOSE_MODE_WITH_COUNT,
    CASH_CLOSE_PAYMENT_METHOD_CASH,
    CASH_CLOSE_RECONCILIATION_STATUS_NOT_EVALUATED,
    CASH_CLOSE_STATUS_PREVIEW,
    FINANCIAL_RECONCILIATION_SOURCE_CASH_CUT,
    FINANCIAL_RECONCILIATION_STATUS_PENDING,
)
from zeromerma_api.modules.operations.domain.constants import (
    OPERATION_BUCKET_BACKROOM,
    OPERATION_BUCKET_COUNTER,
    OPERATION_BUCKET_IN_TRANSIT,
    OPERATION_BUCKET_WASTE,
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class CashSessionClose(Base):
    __tablename__ = "cash_session_closes"
    __table_args__ = (
        UniqueConstraint(
            "cash_session_id",
            name="uq_cash_session_closes_cash_session_id",
        ),
        CheckConstraint(
            "status IN ('PREVIEW', 'READY', 'COMMITTED')",
            name="ck_cash_session_closes_status_valid",
        ),
        CheckConstraint(
            "close_mode IN ('WITH_COUNT')",
            name="ck_cash_session_closes_close_mode_valid",
        ),
        CheckConstraint(
            "reconciliation_status IN ('NOT_EVALUATED', 'PENDING', 'BLOCKED', 'READY')",
            name="ck_cash_session_closes_reconciliation_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cash_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cash_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    workstation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workstations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    closed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), default=CASH_CLOSE_STATUS_PREVIEW, nullable=False
    )
    close_mode: Mapped[str] = mapped_column(
        String(32), default=CASH_CLOSE_MODE_WITH_COUNT, nullable=False
    )
    counter_empty_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    opening_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_cash_in: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_cash_out: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    expected_cash_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    counted_cash_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    cash_variance_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    reconciliation_status: Mapped[str] = mapped_column(
        String(20),
        default=CASH_CLOSE_RECONCILIATION_STATUS_NOT_EVALUATED,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    committed_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class CashSessionClosePaymentMethodCount(Base):
    __tablename__ = "cash_session_close_payment_method_counts"
    __table_args__ = (
        UniqueConstraint(
            "cash_session_close_id",
            "payment_method_code",
            name="uq_cash_session_close_payment_method_counts_close_method",
        ),
        CheckConstraint(
            "payment_method_code IN ('CASH', 'CARD', 'MIXED')",
            name="ck_cash_session_close_payment_method_counts_method_valid",
        ),
        CheckConstraint(
            "counted_amount >= 0",
            name="ck_cash_session_close_payment_method_counts_counted_non_negative",
        ),
        CheckConstraint(
            "expected_amount IS NULL OR expected_amount >= 0",
            name="ck_cash_session_close_payment_method_counts_expected_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cash_session_close_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cash_session_closes.id", ondelete="CASCADE"),
        nullable=False,
    )
    payment_method_code: Mapped[str] = mapped_column(String(40), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    counted_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    expected_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    variance_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)


class CashSessionCloseProductCount(Base):
    __tablename__ = "cash_session_close_product_counts"
    __table_args__ = (
        CheckConstraint(
            "quantity >= 0",
            name="ck_cash_session_close_product_counts_quantity_non_negative",
        ),
        CheckConstraint(
            "bucket_code IN ('BACKROOM', 'COUNTER', 'IN_TRANSIT', 'WASTE')",
            name="ck_cash_session_close_product_counts_bucket_code_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cash_session_close_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cash_session_closes.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_code_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    product_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    product_class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_classes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_class_code_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    product_class_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    bucket_code: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class CashSessionCloseClassReconciliation(Base):
    __tablename__ = "cash_session_close_class_reconciliations"
    __table_args__ = (
        CheckConstraint(
            "expected_quantity >= 0",
            name="ck_cash_session_close_class_reconciliations_expected_non_negative",
        ),
        CheckConstraint(
            "auto_attributed_quantity IS NULL OR auto_attributed_quantity >= 0",
            name="ck_cash_session_close_class_reconciliations_auto_non_negative",
        ),
        CheckConstraint(
            "attributed_quantity IS NULL OR attributed_quantity >= 0",
            name="ck_cash_session_close_class_reconciliations_attributed_non_negative",
        ),
        CheckConstraint(
            "resolution_status IN "
            "('COUNT_REQUIRED', 'AUTO_RESOLVED', 'MANUAL_RESOLVED', 'UNRESOLVED')",
            name="ck_cash_session_close_class_reconciliations_resolution_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cash_session_close_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cash_session_closes.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_classes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_class_code_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    product_class_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    expected_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    auto_attributed_quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    attributed_quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    variance_quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    resolution_status: Mapped[str] = mapped_column(
        String(24),
        default=CASH_CLOSE_CLASS_RESOLUTION_STATUS_COUNT_REQUIRED,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class CashSessionCloseReconciliationAttribution(Base):
    __tablename__ = "cash_session_close_reconciliation_attributions"
    __table_args__ = (
        CheckConstraint(
            "attributed_quantity > 0",
            name="ck_cash_session_close_reconciliation_attributions_quantity_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cash_session_close_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cash_session_closes.id", ondelete="CASCADE"),
        nullable=False,
    )
    class_reconciliation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cash_session_close_class_reconciliations.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_code_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    product_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    product_class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_classes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_class_code_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    product_class_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    attributed_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class CashSessionCloseDiscrepancyResolution(Base):
    __tablename__ = "cash_session_close_discrepancy_resolutions"
    __table_args__ = (
        CheckConstraint(
            "expected_quantity >= 0",
            name="ck_cash_session_close_discrepancy_resolutions_expected_non_negative",
        ),
        CheckConstraint(
            "counted_quantity >= 0",
            name="ck_cash_session_close_discrepancy_resolutions_counted_non_negative",
        ),
        CheckConstraint(
            "discrepancy_quantity <> 0",
            name="ck_cash_session_close_discrepancy_resolutions_non_zero",
        ),
        CheckConstraint(
            "resolution_type IN ('CLOSE_COUNTER_ADJUSTMENT', 'CLOSE_WASTE_ADJUSTMENT')",
            name="ck_cash_session_close_discrepancy_resolutions_type_valid",
        ),
        CheckConstraint(
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
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cash_session_close_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cash_session_closes.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_code_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    product_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    product_class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_classes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_class_code_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    product_class_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    expected_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    counted_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    discrepancy_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    resolution_type: Mapped[str] = mapped_column(String(40), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(40), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operation_documents.id", ondelete="SET NULL"),
        nullable=True,
    )


class CashSessionCloseIssue(Base):
    __tablename__ = "cash_session_close_issues"
    __table_args__ = (
        CheckConstraint(
            "issue_level IN ('BLOCKER', 'WARNING')",
            name="ck_cash_session_close_issues_level_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cash_session_close_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cash_session_closes.id", ondelete="CASCADE"),
        nullable=False,
    )
    issue_level: Mapped[str] = mapped_column(String(16), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)


class FinancialReconciliation(Base):
    __tablename__ = "financial_reconciliations"
    __table_args__ = (
        UniqueConstraint(
            "source_type",
            "source_document_id",
            "payment_method_code",
            name="uq_financial_reconciliations_source_method",
        ),
        CheckConstraint(
            "source_type IN ("
            "'CASH_CUT', "
            "'PAYMENT_SETTLEMENT', "
            "'DEPOSIT', "
            "'RETURN_REFUND', "
            "'OPERATIONAL_PAYMENT', "
            "'CORRECTION'"
            ")",
            name="ck_financial_reconciliations_source_valid",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'IN_REVIEW', 'RECONCILED', 'VOIDED')",
            name="ck_financial_reconciliations_status_valid",
        ),
        CheckConstraint(
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
            name="ck_financial_reconciliations_reason_valid",
        ),
        CheckConstraint(
            "expected_amount >= 0",
            name="ck_financial_reconciliations_expected_non_negative",
        ),
        CheckConstraint(
            "actual_amount >= 0",
            name="ck_financial_reconciliations_actual_non_negative",
        ),
        CheckConstraint(
            "difference_amount <> 0",
            name="ck_financial_reconciliations_difference_non_zero",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    folio: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(40),
        default=FINANCIAL_RECONCILIATION_SOURCE_CASH_CUT,
        nullable=False,
    )
    source_document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(80), nullable=False)
    source_occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    workstation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workstations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    operator_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    payment_method_code: Mapped[str] = mapped_column(String(40), nullable=False)
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    actual_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    difference_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default=FINANCIAL_RECONCILIATION_STATUS_PENDING,
        nullable=False,
    )
    reason_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_evidence: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class BranchCounterSnapshot(Base):
    __tablename__ = "branch_counter_snapshots"
    __table_args__ = (
        CheckConstraint(
            "snapshot_type IN ('CLOSE_BASELINE')",
            name="ck_branch_counter_snapshots_type_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_cash_session_close_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cash_session_closes.id", ondelete="SET NULL"),
        nullable=True,
    )
    snapshot_type: Mapped[str] = mapped_column(
        String(32),
        default=BRANCH_COUNTER_SNAPSHOT_TYPE_CLOSE_BASELINE,
        nullable=False,
    )
    captured_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    captured_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class BranchCounterSnapshotLine(Base):
    __tablename__ = "branch_counter_snapshot_lines"
    __table_args__ = (
        CheckConstraint(
            "quantity >= 0",
            name="ck_branch_counter_snapshot_lines_quantity_non_negative",
        ),
        CheckConstraint(
            "bucket_code IN ('BACKROOM', 'COUNTER', 'IN_TRANSIT', 'WASTE')",
            name="ck_branch_counter_snapshot_lines_bucket_code_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branch_counter_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_code_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    product_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    product_class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_classes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_class_code_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    product_class_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    bucket_code: Mapped[str] = mapped_column(String(32), nullable=False)


_ = (
    CASH_CLOSE_PAYMENT_METHOD_CASH,
    CASH_CLOSE_DISCREPANCY_REASON_COUNT_ERROR,
    CASH_CLOSE_DISCREPANCY_RESOLUTION_TYPE_CLOSE_COUNTER_ADJUSTMENT,
    CASH_CLOSE_ISSUE_LEVEL_BLOCKER,
    CASH_CLOSE_CLASS_RESOLUTION_STATUS_COUNT_REQUIRED,
    CASH_CLOSE_MODE_WITH_COUNT,
    OPERATION_BUCKET_BACKROOM,
    OPERATION_BUCKET_COUNTER,
    OPERATION_BUCKET_IN_TRANSIT,
    OPERATION_BUCKET_WASTE,
)
