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
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from zeromerma_api.db.base import Base
from zeromerma_api.modules.orders.domain.constants import (
    ORDER_PAYMENT_METHOD_CASH,
    ORDER_PAYMENT_TYPE_ADVANCE,
    ORDER_STATUS_PENDING,
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class CustomerOrder(Base):
    __tablename__ = "customer_orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'READY', 'DELIVERED', 'CANCELED')",
            name="ck_customer_orders_status_valid",
        ),
        CheckConstraint(
            "customer_name <> ''",
            name="ck_customer_orders_customer_name_not_empty",
        ),
        CheckConstraint(
            "subtotal_amount >= 0",
            name="ck_customer_orders_subtotal_non_negative",
        ),
        CheckConstraint(
            "total_amount >= 0",
            name="ck_customer_orders_total_non_negative",
        ),
        CheckConstraint(
            "advance_amount >= 0",
            name="ck_customer_orders_advance_non_negative",
        ),
        CheckConstraint(
            "remaining_balance_amount >= 0",
            name="ck_customer_orders_remaining_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    workstation_id_created: Mapped[uuid.UUID] = mapped_column(
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
    status: Mapped[str] = mapped_column(String(20), default=ORDER_STATUS_PENDING, nullable=False)
    customer_name: Mapped[str] = mapped_column(String(160), nullable=False)
    customer_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    requested_for_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency_code: Mapped[str] = mapped_column(String(3), default="MXN", nullable=False)
    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    advance_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    remaining_balance_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class CustomerOrderItem(Base):
    __tablename__ = "customer_order_items"
    __table_args__ = (
        UniqueConstraint(
            "customer_order_id", "line_number", name="uq_customer_order_items_line_number"
        ),
        CheckConstraint("quantity > 0", name="ck_customer_order_items_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_customer_order_items_unit_price_non_negative"),
        CheckConstraint(
            "line_total_amount >= 0",
            name="ck_customer_order_items_line_total_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
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
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)


class CustomerOrderPayment(Base):
    __tablename__ = "customer_order_payments"
    __table_args__ = (
        UniqueConstraint(
            "customer_order_id",
            "sequence",
            name="uq_customer_order_payments_sequence",
        ),
        CheckConstraint(
            "payment_type IN ('ADVANCE', 'SETTLEMENT', 'REFUND')",
            name="ck_customer_order_payments_type_valid",
        ),
        CheckConstraint(
            "payment_method_code IN ('CASH', 'CARD', 'MIXED')",
            name="ck_customer_order_payments_method_valid",
        ),
        CheckConstraint(
            "amount > 0",
            name="ck_customer_order_payments_amount_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_type: Mapped[str] = mapped_column(
        String(20), default=ORDER_PAYMENT_TYPE_ADVANCE, nullable=False
    )
    payment_method_code: Mapped[str] = mapped_column(
        String(40),
        default=ORDER_PAYMENT_METHOD_CASH,
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), default="MXN", nullable=False)
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
    recorded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    recorded_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


_ = (ORDER_STATUS_PENDING,)
