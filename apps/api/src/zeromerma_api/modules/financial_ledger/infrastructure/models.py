"""The financial operation is a cause; confirmed method entries are monetary facts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from zeromerma_api.db.base import Base

CONTEXT_CHECK = (
    "context_version = 1 AND operation_id IS NOT NULL AND correlation_id IS NOT NULL "
    "AND source_app IN ('POS','BACKOFFICE','API','SYSTEM','WORKER') AND "
    "((actor_id IS NOT NULL AND actor_type = 'USER') OR "
    "(actor_id IS NULL AND actor_type = 'SYSTEM' AND source_app IN ('SYSTEM','WORKER')))"
)
SOURCE_CHECK = (
    "effect_code = kind AND ("
    "(kind = 'CASH_OPENING' AND source_type IN ('CASH_SESSION','OPENING_STATE')) OR "
    "(kind = 'SALE_COLLECTION' AND source_type = 'SALE') OR "
    "(kind IN ('ORDER_ADVANCE','ORDER_SETTLEMENT','ORDER_REFUND') "
    "AND source_type = 'ORDER_PAYMENT') OR "
    "(kind = 'ORDER_REFUND' AND source_type = 'ORDER_CANCELLATION') OR "
    "(kind = 'SALE_REFUND' AND source_type = 'SALE_RETURN') OR "
    "(kind = 'OPERATIONAL_PAYMENT' AND source_type = 'OPERATIONAL_PAYMENT') OR "
    "(kind = 'OPERATIONAL_CHARGE' AND source_type = 'OPERATIONAL_DISCOUNT') OR "
    "(kind = 'CASH_DEPOSIT' AND source_type = 'CASH_DEPOSIT') OR "
    "(kind = 'CASH_WITHDRAWAL' AND source_type = 'CASH_WITHDRAWAL') OR "
    "(kind = 'TECHNICAL_REVERSAL' AND source_type = 'FINANCIAL_ENTRY') OR "
    "(kind = 'OPENING_OBLIGATION' AND source_type = 'OPENING_STATE'))"
)
OPENING_CHECK = (
    "((source_type = 'OPENING_STATE' AND opening_reason_code IS NOT NULL "
    "AND length(btrim(opening_reason_code)) > 0 AND source_evidence_reference IS NOT NULL "
    "AND cutover_at IS NOT NULL) OR (source_type <> 'OPENING_STATE' "
    "AND opening_reason_code IS NULL AND source_evidence_reference IS NULL "
    "AND cutover_at IS NULL)) AND "
    "((kind = 'OPENING_OBLIGATION' AND opening_obligation_kind IN "
    "('RECEIVABLE','PAYABLE','CUSTOMER_ADVANCE') AND cash_session_id IS NULL "
    "AND workstation_id IS NULL) OR (kind <> 'OPENING_OBLIGATION' "
    "AND opening_obligation_kind IS NULL)) AND "
    "(kind <> 'CASH_OPENING' OR cash_session_id IS NOT NULL) AND "
    "(source_type <> 'CASH_SESSION' OR source_id = cash_session_id)"
)
RELATION_CHECK = (
    "(kind IN ('SALE_REFUND','ORDER_REFUND') AND ((relation_kind = 'REFUND_OF' "
    "AND related_operation_id IS NOT NULL) OR "
    "(relation_kind IS NULL AND related_operation_id IS NULL))) OR "
    "(kind = 'TECHNICAL_REVERSAL' AND relation_kind = 'REVERSAL_OF' "
    "AND related_operation_id IS NOT NULL) OR "
    "(kind = 'ORDER_SETTLEMENT' AND ((relation_kind = 'SETTLEMENT_OF' "
    "AND related_operation_id IS NOT NULL) OR "
    "(relation_kind IS NULL AND related_operation_id IS NULL))) OR "
    "(kind NOT IN ('SALE_REFUND','ORDER_REFUND','TECHNICAL_REVERSAL','ORDER_SETTLEMENT') "
    "AND relation_kind IS NULL AND related_operation_id IS NULL)"
)
SUBJECT_CHECK = (
    "(kind IN ('SALE_COLLECTION','SALE_REFUND') AND subject_type = 'SALE') OR "
    "(kind IN ('ORDER_ADVANCE','ORDER_SETTLEMENT','ORDER_REFUND') AND subject_type = 'ORDER') OR "
    "(kind = 'OPERATIONAL_PAYMENT' AND subject_type = 'OPERATIONAL_PAYMENT') OR "
    "(kind = 'OPERATIONAL_CHARGE' AND subject_type = 'OPERATIONAL_DISCOUNT') OR "
    "(kind IN ('CASH_OPENING','CASH_DEPOSIT','CASH_WITHDRAWAL') "
    "AND subject_type = 'CASH_SESSION' AND subject_id = cash_session_id) OR "
    "(kind = 'OPENING_OBLIGATION' AND ((opening_obligation_kind = 'CUSTOMER_ADVANCE' "
    "AND subject_type = 'ORDER') OR (opening_obligation_kind IN ('RECEIVABLE','PAYABLE') "
    "AND subject_type IN ('ORDER','OPENING_BALANCE')))) OR "
    "(kind = 'TECHNICAL_REVERSAL' AND subject_type IN "
    "('SALE','ORDER','OPERATIONAL_PAYMENT','OPERATIONAL_DISCOUNT','CASH_SESSION','OPENING_BALANCE'))"
)
ENTRY_STATE_CHECK = (
    "state IN ('PENDING','PROCESSING','UNKNOWN','CONFIRMED','REJECTED','CANCELLED') AND "
    "((state = 'CONFIRMED' AND confirmed_at IS NOT NULL) OR "
    "(state <> 'CONFIRMED' AND confirmed_at IS NULL))"
)
ENTRY_EVIDENCE_CHECK = (
    "(resolution_kind IS NULL AND resolution_reference IS NULL "
    "AND state IN ('PENDING','PROCESSING','UNKNOWN','REJECTED','CANCELLED')) OR "
    "(resolution_kind = 'LOCAL_CASH' AND payment_method_code = 'CASH' "
    "AND state = 'CONFIRMED' AND resolution_reference IS NULL) OR "
    "(resolution_reference IS NOT NULL AND ((resolution_kind = 'EXTERNAL_RECORDING' "
    "AND execution_mode = 'ACCOUNTING_ONLY' AND state = 'CONFIRMED') OR "
    "(resolution_kind = 'PROVIDER_CAPTURE' AND execution_mode = 'PROVIDER_INTEGRATED' "
    "AND direction = 'IN' AND state = 'CONFIRMED') OR "
    "(resolution_kind = 'PROVIDER_REFUND' AND execution_mode = 'PROVIDER_INTEGRATED' "
    "AND direction = 'OUT' AND state = 'CONFIRMED') OR "
    "(resolution_kind = 'PROVIDER_REJECTION' AND execution_mode = 'PROVIDER_INTEGRATED' "
    "AND state = 'REJECTED') OR (resolution_kind = 'PROVIDER_VOID' "
    "AND execution_mode = 'PROVIDER_INTEGRATED' AND state = 'CANCELLED') OR "
    "(resolution_kind = 'MANUAL_RECONCILIATION' "
    "AND state IN ('CONFIRMED','REJECTED','CANCELLED'))))"
)
TENDER_CHECK = (
    "change_amount >= 0 AND change_amount <> 'NaN'::numeric AND "
    "(tendered_amount IS NULL OR (tendered_amount > 0 "
    "AND tendered_amount <> 'NaN'::numeric)) AND "
    "((payment_method_code = 'CASH' AND direction = 'IN' "
    "AND tendered_amount IS NOT NULL AND tendered_amount = amount + change_amount) OR "
    "((payment_method_code = 'CARD' OR direction = 'OUT') AND change_amount = 0 "
    "AND (tendered_amount IS NULL OR tendered_amount = amount)))"
)


class _FinancialContext:
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"))
    workstation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workstations.id", ondelete="RESTRICT")
    )
    cash_session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("cash_sessions.id", ondelete="RESTRICT")
    )
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    context_version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_app: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    operation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    operation_code: Mapped[str | None] = mapped_column(String(160))
    correlation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    causation_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    request_id: Mapped[str | None] = mapped_column(String(120))
    idempotency_key: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    related_branch_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.clock_timestamp()
    )


class FinancialOperation(_FinancialContext, Base):
    __tablename__ = "financial_operations"
    __table_args__ = (
        UniqueConstraint("source_type", "source_id", "effect_code", name="uq_financial_cause"),
        CheckConstraint(CONTEXT_CHECK, name="context_valid"),
        CheckConstraint("currency_code = 'MXN'", name="currency_valid"),
        CheckConstraint("jsonb_typeof(related_branch_ids) = 'array'", name="branches_array"),
        CheckConstraint("amount_due >= 0 AND amount_due <> 'NaN'::numeric", name="amount_valid"),
        CheckConstraint(SOURCE_CHECK, name="source_valid"),
        CheckConstraint(f"({OPENING_CHECK}) IS TRUE", name="opening_valid"),
        CheckConstraint(f"({RELATION_CHECK}) IS TRUE", name="relation_valid"),
        CheckConstraint(f"({SUBJECT_CHECK}) IS TRUE", name="subject_valid"),
        CheckConstraint(
            "kind NOT IN ('SALE_COLLECTION','OPERATIONAL_PAYMENT','OPERATIONAL_CHARGE') "
            "OR source_id = subject_id",
            name="source_subject_valid",
        ),
        CheckConstraint(
            "related_operation_id IS NULL OR related_operation_id <> id", name="not_self"
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    effect_code: Mapped[str] = mapped_column(String(40), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    amount_due: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    opening_obligation_kind: Mapped[str | None] = mapped_column(String(32))
    opening_reason_code: Mapped[str | None] = mapped_column(String(64))
    source_evidence_reference: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    cutover_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    related_operation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("financial_operations.id", ondelete="RESTRICT")
    )
    relation_kind: Mapped[str | None] = mapped_column(String(24))


class FinancialEntry(_FinancialContext, Base):
    __tablename__ = "financial_entries"
    __table_args__ = (
        UniqueConstraint("financial_operation_id", "leg_key", name="uq_financial_entry_leg"),
        UniqueConstraint("reverses_entry_id", name="uq_financial_entry_reversal"),
        CheckConstraint(CONTEXT_CHECK, name="context_valid"),
        CheckConstraint("currency_code = 'MXN'", name="currency_valid"),
        CheckConstraint("jsonb_typeof(related_branch_ids) = 'array'", name="branches_array"),
        CheckConstraint("amount > 0 AND amount <> 'NaN'::numeric", name="amount_valid"),
        CheckConstraint("length(btrim(leg_key)) > 0", name="leg_key_valid"),
        CheckConstraint("payment_method_code IN ('CASH','CARD')", name="method_valid"),
        CheckConstraint("direction IN ('IN','OUT')", name="direction_valid"),
        CheckConstraint(
            "(payment_method_code = 'CASH' AND execution_mode = 'LOCAL' "
            "AND cash_session_id IS NOT NULL) OR (payment_method_code = 'CARD' "
            "AND execution_mode IN ('ACCOUNTING_ONLY','PROVIDER_INTEGRATED','MANUAL_FALLBACK'))",
            name="execution_valid",
        ),
        CheckConstraint(ENTRY_STATE_CHECK, name="state_valid"),
        CheckConstraint(f"({ENTRY_EVIDENCE_CHECK}) IS TRUE", name="evidence_valid"),
        CheckConstraint(TENDER_CHECK, name="tender_valid"),
        CheckConstraint("reverses_entry_id IS NULL OR reverses_entry_id <> id", name="not_self"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    financial_operation_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_operations.id", ondelete="RESTRICT"), nullable=False
    )
    leg_key: Mapped[str] = mapped_column(String(40), nullable=False)
    payment_method_code: Mapped[str] = mapped_column(String(8), nullable=False)
    direction: Mapped[str] = mapped_column(String(3), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tendered_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    change_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default=text("0")
    )
    execution_mode: Mapped[str] = mapped_column(String(24), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_kind: Mapped[str | None] = mapped_column(String(32))
    resolution_reference: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    reverses_entry_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("financial_entries.id", ondelete="RESTRICT")
    )


Index(
    "uq_financial_cash_opening",
    FinancialOperation.cash_session_id,
    unique=True,
    postgresql_where=text("kind = 'CASH_OPENING'"),
)
Index(
    "ix_financial_operations_branch_time",
    FinancialOperation.branch_id,
    FinancialOperation.occurred_at,
)
Index("ix_financial_operations_operation_id", FinancialOperation.operation_id)
Index(
    "ix_financial_operations_subject",
    FinancialOperation.subject_type,
    FinancialOperation.subject_id,
)
Index("ix_financial_entries_session_state", FinancialEntry.cash_session_id, FinancialEntry.state)
Index("ix_financial_entries_operation_id", FinancialEntry.operation_id)
