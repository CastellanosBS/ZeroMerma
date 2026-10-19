from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from zeromerma_api.db.base import Base


class PaymentTerminalBinding(Base):
    __tablename__ = "payment_terminal_bindings"
    __table_args__ = (
        UniqueConstraint(
            "provider_code",
            "environment",
            "account_reference",
            "terminal_reference",
            name="uq_payment_terminal_binding",
        ),
        CheckConstraint("environment IN ('SANDBOX','PRODUCTION')", name="environment_valid"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"))
    workstation_id: Mapped[UUID] = mapped_column(ForeignKey("workstations.id", ondelete="RESTRICT"))
    provider_code: Mapped[str] = mapped_column(String(32))
    environment: Mapped[str] = mapped_column(String(16))
    account_reference: Mapped[str] = mapped_column(String(120))
    terminal_reference: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    contract_evidence_id: Mapped[UUID] = mapped_column()
    hardware_evidence_id: Mapped[UUID] = mapped_column()
    certification_evidence_id: Mapped[UUID] = mapped_column()


class ExternalPaymentOperation(Base):
    __tablename__ = "external_payment_operations"
    __table_args__ = (
        UniqueConstraint("financial_entry_id", name="uq_external_payment_entry"),
        UniqueConstraint(
            "provider_code",
            "environment",
            "account_reference",
            "provider_idempotency_key",
            name="uq_external_provider_key",
        ),
        UniqueConstraint(
            "provider_code",
            "environment",
            "account_reference",
            "provider_operation_id",
            name="uq_external_provider_operation",
        ),
        CheckConstraint(
            "amount > 0 AND amount <> 'NaN'::numeric AND currency_code = 'MXN'", name="amount_valid"
        ),
        CheckConstraint("operation_type IN ('CAPTURE','REFUND')", name="type_valid"),
        CheckConstraint(
            "status IN ('CREATED','PROCESSING','AUTHORIZED','UNKNOWN',"
            "'CAPTURED','REFUNDED','DECLINED','FAILED')",
            name="status_valid",
        ),
        CheckConstraint(
            "reconciliation_status IN ('PENDING','MATCHED','DISCREPANCY')",
            name="reconciliation_valid",
        ),
        CheckConstraint(
            "(operation_type = 'REFUND') = (original_operation_id IS NOT NULL)",
            name="original_valid",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    financial_entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_entries.id", ondelete="RESTRICT")
    )
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"))
    workstation_id: Mapped[UUID] = mapped_column(ForeignKey("workstations.id", ondelete="RESTRICT"))
    cash_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("cash_sessions.id", ondelete="RESTRICT")
    )
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    terminal_binding_id: Mapped[UUID] = mapped_column(
        ForeignKey("payment_terminal_bindings.id", ondelete="RESTRICT")
    )
    idempotency_record_id: Mapped[UUID] = mapped_column(
        ForeignKey("idempotency_records.id", ondelete="RESTRICT")
    )
    original_operation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("external_payment_operations.id", ondelete="RESTRICT")
    )
    operation_type: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="CREATED")
    reconciliation_status: Mapped[str] = mapped_column(String(16), default="PENDING")
    provider_code: Mapped[str] = mapped_column(String(32))
    environment: Mapped[str] = mapped_column(String(16))
    account_reference: Mapped[str] = mapped_column(String(120))
    terminal_reference: Mapped[str] = mapped_column(String(120))
    provider_idempotency_key: Mapped[UUID] = mapped_column()
    provider_operation_id: Mapped[str | None] = mapped_column(String(120))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency_code: Mapped[str] = mapped_column(String(3))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExternalPaymentEvidence(Base):
    __tablename__ = "external_payment_evidence"
    __table_args__ = (
        UniqueConstraint(
            "provider_code",
            "environment",
            "account_reference",
            "event_id",
            name="uq_external_provider_event",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    external_operation_id: Mapped[UUID] = mapped_column(
        ForeignKey("external_payment_operations.id", ondelete="RESTRICT")
    )
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"))
    provider_code: Mapped[str] = mapped_column(String(32))
    environment: Mapped[str] = mapped_column(String(16))
    account_reference: Mapped[str] = mapped_column(String(120))
    event_id: Mapped[str] = mapped_column(String(120))
    state: Mapped[str] = mapped_column(String(16))
    fingerprint: Mapped[str] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
