from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from zeromerma_api.db.base import Base
from zeromerma_api.modules.discounts.domain.constants import (
    COMMERCIAL_DISCOUNT_STATUS_INACTIVE,
    DISCOUNT_STATUS_COMMITTED,
    PAYMENT_METHOD_CASH,
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class OperationalDiscountCategory(Base):
    __tablename__ = "operational_discount_categories"
    __table_args__ = (
        CheckConstraint(
            "code IN ("
            "'EMPLOYEE_INSURANCE', "
            "'EMPLOYEE_LOAN', "
            "'INTERNAL_CHARGE', "
            "'PAYROLL_ADVANCE_ADJUSTMENT', "
            "'OTHER'"
            ")",
            name="ck_operational_discount_categories_code_valid",
        ),
    )

    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    display_order: Mapped[int] = mapped_column(nullable=False)


class OperationalDiscount(Base):
    __tablename__ = "operational_discounts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('COMMITTED')",
            name="ck_operational_discounts_status_valid",
        ),
        CheckConstraint(
            "payment_method_code IN ('CASH', 'CARD', 'MIXED')",
            name="ck_operational_discounts_method_valid",
        ),
        CheckConstraint(
            "total_amount > 0",
            name="ck_operational_discounts_total_positive",
        ),
        CheckConstraint(
            "cash_amount >= 0",
            name="ck_operational_discounts_cash_non_negative",
        ),
        CheckConstraint(
            "non_cash_amount >= 0",
            name="ck_operational_discounts_non_cash_non_negative",
        ),
        CheckConstraint(
            "cash_amount + non_cash_amount = total_amount",
            name="ck_operational_discounts_amount_split_matches_total",
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
    subject_name: Mapped[str] = mapped_column(String(160), nullable=False)
    concept: Mapped[str] = mapped_column(String(240), nullable=False)
    category_code: Mapped[str | None] = mapped_column(
        String(40),
        ForeignKey("operational_discount_categories.code", ondelete="RESTRICT"),
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
        default=DISCOUNT_STATUS_COMMITTED,
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


class CommercialDiscount(Base):
    __tablename__ = "commercial_discounts"
    __table_args__ = (
        CheckConstraint(
            "discount_type IN ('PERCENTAGE', 'FIXED_AMOUNT')",
            name="ck_commercial_discounts_type_valid",
        ),
        CheckConstraint(
            "target_scope IN ('GLOBAL', 'PRODUCT', 'CLASS')",
            name="ck_commercial_discounts_scope_valid",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED')",
            name="ck_commercial_discounts_status_valid",
        ),
        CheckConstraint("value > 0", name="ck_commercial_discounts_value_positive"),
        CheckConstraint(
            "discount_type != 'PERCENTAGE' OR value <= 100",
            name="ck_commercial_discounts_percentage_range",
        ),
        CheckConstraint(
            "("
            "(target_scope = 'GLOBAL' AND product_id IS NULL AND product_class_id IS NULL)"
            " OR "
            "(target_scope = 'PRODUCT' AND product_id IS NOT NULL AND product_class_id IS NULL)"
            " OR "
            "(target_scope = 'CLASS' AND product_id IS NULL AND product_class_id IS NOT NULL)"
            ")",
            name="ck_commercial_discounts_target_shape",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="RESTRICT"),
        nullable=True,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=True,
    )
    product_class_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_classes.id", ondelete="RESTRICT"),
        nullable=True,
    )
    code: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    discount_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), default="MXN", nullable=False)
    valid_from_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    is_pos_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default=COMMERCIAL_DISCOUNT_STATUS_INACTIVE,
        nullable=False,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
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
