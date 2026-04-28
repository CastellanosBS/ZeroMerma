from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from zeromerma_api.db.base import Base
from zeromerma_api.modules.payments.domain.constants import (
    PAYMENT_METHOD_CASH,
    PAYMENT_STATUS_COMMITTED,
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class OperationalPaymentCategory(Base):
    __tablename__ = "operational_payment_categories"
    __table_args__ = (
        CheckConstraint(
            "code IN ('GAS', 'SUPPLIER', 'SERVICES', 'LOGISTICS', 'PURCHASE', 'OTHER')",
            name="ck_operational_payment_categories_code_valid",
        ),
    )

    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    display_order: Mapped[int] = mapped_column(nullable=False)


class OperationalPayment(Base):
    __tablename__ = "operational_payments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('COMMITTED')",
            name="ck_operational_payments_status_valid",
        ),
        CheckConstraint(
            "payment_method_code IN ('CASH', 'CARD', 'MIXED')",
            name="ck_operational_payments_method_valid",
        ),
        CheckConstraint(
            "total_amount > 0",
            name="ck_operational_payments_total_positive",
        ),
        CheckConstraint(
            "cash_amount >= 0",
            name="ck_operational_payments_cash_non_negative",
        ),
        CheckConstraint(
            "non_cash_amount >= 0",
            name="ck_operational_payments_non_cash_non_negative",
        ),
        CheckConstraint(
            "cash_amount + non_cash_amount = total_amount",
            name="ck_operational_payments_amount_split_matches_total",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    active_cash_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cash_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    payee_name: Mapped[str] = mapped_column(String(160), nullable=False)
    concept: Mapped[str] = mapped_column(String(240), nullable=False)
    category_code: Mapped[str | None] = mapped_column(
        String(40),
        ForeignKey("operational_payment_categories.code", ondelete="RESTRICT"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_method_code: Mapped[str] = mapped_column(
        String(40),
        default=PAYMENT_METHOD_CASH,
        nullable=False,
    )
    currency_code: Mapped[str] = mapped_column(String(3), default="MXN", nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cash_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    non_cash_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default=PAYMENT_STATUS_COMMITTED,
        nullable=False,
    )
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    committed_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


_ = (PAYMENT_STATUS_COMMITTED,)
