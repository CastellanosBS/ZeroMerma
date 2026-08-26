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
from zeromerma_api.modules.suppliers.domain.constants import (
    SUPPLIER_CATEGORY_OTHER,
    SUPPLIER_PAYMENT_TERMS_CASH,
    SUPPLIER_STATUS_ACTIVE,
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class Supplier(Base):
    __tablename__ = "suppliers"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'BLOCKED')",
            name="ck_suppliers_status_valid",
        ),
        CheckConstraint(
            "category IN ('RAW_MATERIALS', 'PACKAGING', 'SERVICES', 'MIXED', 'OTHER')",
            name="ck_suppliers_category_valid",
        ),
        CheckConstraint(
            "payment_terms_type IN ('CASH', 'CREDIT', 'TRANSFER', 'MIXED')",
            name="ck_suppliers_payment_terms_valid",
        ),
        CheckConstraint("credit_days >= 0", name="ck_suppliers_credit_days_non_negative"),
        CheckConstraint("lead_time_days >= 0", name="ck_suppliers_lead_time_non_negative"),
        CheckConstraint(
            "minimum_order_amount IS NULL OR minimum_order_amount >= 0",
            name="ck_suppliers_minimum_order_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    legal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    commercial_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(40), unique=True, nullable=True)
    category: Mapped[str] = mapped_column(
        String(32), default=SUPPLIER_CATEGORY_OTHER, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default=SUPPLIER_STATUS_ACTIVE, nullable=False)
    fiscal_address: Mapped[str | None] = mapped_column(String(320), nullable=True)
    fiscal_regime: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payment_fiscal_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    payment_terms_type: Mapped[str] = mapped_column(
        String(32), default=SUPPLIER_PAYMENT_TERMS_CASH, nullable=False
    )
    credit_days: Mapped[int] = mapped_column(default=0, nullable=False)
    default_currency: Mapped[str] = mapped_column(String(3), default="MXN", nullable=False)
    minimum_order_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    lead_time_days: Mapped[int] = mapped_column(default=0, nullable=False)
    delivery_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    purchase_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class SupplierContact(Base):
    __tablename__ = "supplier_contacts"
    __table_args__ = (
        CheckConstraint(
            "email IS NULL OR position('@' in email) > 1",
            name="ck_supplier_contacts_email_shape",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class SupplierProduct(Base):
    __tablename__ = "supplier_products"
    __table_args__ = (
        UniqueConstraint("supplier_id", "product_id", name="uq_supplier_products_supplier_product"),
        CheckConstraint(
            "last_known_price IS NULL OR last_known_price >= 0",
            name="ck_supplier_products_last_price_non_negative",
        ),
        CheckConstraint(
            "minimum_order_qty IS NULL OR minimum_order_qty >= 0",
            name="ck_supplier_products_minimum_qty_non_negative",
        ),
        CheckConstraint(
            "conversion_factor IS NULL OR conversion_factor > 0",
            name="ck_supplier_products_conversion_factor_positive",
        ),
        CheckConstraint("lead_time_days >= 0", name="ck_supplier_products_lead_time_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    supplier_sku: Mapped[str | None] = mapped_column(String(80), nullable=True)
    purchase_uom: Mapped[str | None] = mapped_column(String(32), nullable=True)
    conversion_factor: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    last_known_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="MXN", nullable=False)
    minimum_order_qty: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    lead_time_days: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class SupplierBranch(Base):
    __tablename__ = "supplier_branches"
    __table_args__ = (
        UniqueConstraint("supplier_id", "branch_id", name="uq_supplier_branches_supplier_branch"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    delivery_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
