from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from zeromerma_api.db.base import Base
from zeromerma_api.modules.sales.domain.constants import (
    CASH_MOVEMENT_DIRECTION_IN,
    CASH_MOVEMENT_TYPE_SALE_COLLECTION,
    SALE_LINE_PHYSICAL_ATTRIBUTION_PENDING_RECONCILIATION,
    SALE_LINE_PHYSICAL_ATTRIBUTION_RECONCILED,
    SALE_PAYMENT_METHOD_CASH,
    SALE_STATUS_CONFIRMED,
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint("status IN ('CONFIRMED')", name="ck_sales_status_valid"),
        CheckConstraint("subtotal_amount >= 0", name="ck_sales_subtotal_amount_non_negative"),
        CheckConstraint("total_amount >= 0", name="ck_sales_total_amount_non_negative"),
        CheckConstraint("paid_amount >= 0", name="ck_sales_paid_amount_non_negative"),
        CheckConstraint("change_amount >= 0", name="ck_sales_change_amount_non_negative"),
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
    cash_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cash_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    operator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), default=SALE_STATUS_CONFIRMED, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), default="MXN", nullable=False)
    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    change_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class SaleLine(Base):
    __tablename__ = "sale_lines"
    __table_args__ = (
        UniqueConstraint("sale_id", "sequence", name="uq_sale_lines_sale_sequence"),
        CheckConstraint(
            "capture_mode IN ('CLASS_CAPTURE', 'PRODUCT_DIRECT')",
            name="ck_sale_lines_capture_mode_valid",
        ),
        CheckConstraint("quantity > 0", name="ck_sale_lines_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_sale_lines_unit_price_non_negative"),
        CheckConstraint("line_total_amount >= 0", name="ck_sale_lines_total_amount_non_negative"),
        CheckConstraint(
            "physical_attribution_status IN "
            "('PENDING_RECONCILIATION', 'DIRECT_ASSIGNED', 'RECONCILED')",
            name="ck_sale_lines_physical_attribution_status_valid",
        ),
        CheckConstraint(
            "("
            "(capture_mode = 'CLASS_CAPTURE' "
            "AND product_class_id IS NOT NULL "
            "AND product_id IS NULL)"
            " OR "
            "(capture_mode = 'PRODUCT_DIRECT' "
            "AND product_class_id IS NULL "
            "AND product_id IS NOT NULL)"
            ")",
            name="ck_sale_lines_reference_shape",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    capture_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    product_class_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_classes.id", ondelete="RESTRICT"),
        nullable=True,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=True,
    )
    catalog_code_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    catalog_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    physical_attribution_status: Mapped[str] = mapped_column(
        String(40),
        default=SALE_LINE_PHYSICAL_ATTRIBUTION_PENDING_RECONCILIATION,
        nullable=False,
    )


class SalePayment(Base):
    __tablename__ = "sale_payments"
    __table_args__ = (
        UniqueConstraint("sale_id", "sequence", name="uq_sale_payments_sale_sequence"),
        CheckConstraint(
            "tendered_amount >= 0",
            name="ck_sale_payments_tendered_amount_non_negative",
        ),
        CheckConstraint("applied_amount >= 0", name="ck_sale_payments_applied_amount_non_negative"),
        CheckConstraint("change_amount >= 0", name="ck_sale_payments_change_amount_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_method_code: Mapped[str] = mapped_column(
        String(40),
        default=SALE_PAYMENT_METHOD_CASH,
        nullable=False,
    )
    tendered_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    applied_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    change_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), default="MXN", nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class CashMovement(Base):
    __tablename__ = "cash_movements"
    __table_args__ = (
        CheckConstraint("direction IN ('IN', 'OUT')", name="ck_cash_movements_direction_valid"),
        CheckConstraint("amount >= 0", name="ck_cash_movements_amount_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales.id", ondelete="RESTRICT"),
        nullable=True,
    )
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
    operator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    movement_type: Mapped[str] = mapped_column(
        String(40),
        default=CASH_MOVEMENT_TYPE_SALE_COLLECTION,
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(
        String(10),
        default=CASH_MOVEMENT_DIRECTION_IN,
        nullable=False,
    )
    payment_method_code: Mapped[str] = mapped_column(
        String(40),
        default=SALE_PAYMENT_METHOD_CASH,
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), default="MXN", nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


_ = (
    SALE_LINE_PHYSICAL_ATTRIBUTION_RECONCILED,
)
