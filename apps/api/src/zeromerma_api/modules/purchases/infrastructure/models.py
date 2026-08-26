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
from zeromerma_api.modules.purchases.domain.constants import (
    PURCHASE_DOCUMENT_TYPE_PURCHASE,
    PURCHASE_STATUS_DRAFT,
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class PurchaseDocument(Base):
    __tablename__ = "purchase_documents"
    __table_args__ = (
        CheckConstraint(
            "document_type IN ('PURCHASE', 'DIRECT_ENTRY')",
            name="ck_purchase_documents_type_valid",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'ORDERED', 'PARTIALLY_RECEIVED', 'RECEIVED', 'CANCELLED')",
            name="ck_purchase_documents_status_valid",
        ),
        CheckConstraint(
            "external_document_type IS NULL OR external_document_type IN "
            "('INVOICE', 'REMISSION', 'SUPPLIER_NOTE', 'PURCHASE_REFERENCE', 'OTHER')",
            name="ck_purchase_documents_external_type_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    folio: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    document_type: Mapped[str] = mapped_column(
        String(32), default=PURCHASE_DOCUMENT_TYPE_PURCHASE, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default=PURCHASE_STATUS_DRAFT, nullable=False)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    receiving_branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    external_document_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    external_document_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    external_document_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    document_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    confirmed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    cancelled_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class PurchaseDocumentLine(Base):
    __tablename__ = "purchase_document_lines"
    __table_args__ = (
        UniqueConstraint(
            "purchase_document_id", "line_number", name="uq_purchase_lines_document_line_number"
        ),
        CheckConstraint("ordered_quantity > 0", name="ck_purchase_lines_ordered_quantity_positive"),
        CheckConstraint(
            "received_quantity >= 0", name="ck_purchase_lines_received_quantity_non_negative"
        ),
        CheckConstraint("unit_cost >= 0", name="ck_purchase_lines_unit_cost_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    purchase_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_number: Mapped[int] = mapped_column(nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_code_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    product_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    product_kind_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(32), nullable=False)
    ordered_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), default=Decimal("0"), nullable=False
    )
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
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


class PurchaseReceipt(Base):
    __tablename__ = "purchase_receipts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    folio: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    purchase_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_documents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    received_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    has_discrepancy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PurchaseReceiptLine(Base):
    __tablename__ = "purchase_receipt_lines"
    __table_args__ = (
        UniqueConstraint(
            "purchase_receipt_id", "purchase_line_id", name="uq_purchase_receipt_lines_receipt_line"
        ),
        CheckConstraint(
            "received_quantity >= 0", name="ck_purchase_receipt_lines_quantity_non_negative"
        ),
        CheckConstraint("unit_cost >= 0", name="ck_purchase_receipt_lines_unit_cost_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    purchase_receipt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_receipts.id", ondelete="CASCADE"),
        nullable=False,
    )
    purchase_line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_document_lines.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    line_number: Mapped[int] = mapped_column(nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    discrepancy_reason: Mapped[str | None] = mapped_column(String(160), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
