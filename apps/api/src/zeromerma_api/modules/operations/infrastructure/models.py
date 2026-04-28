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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from zeromerma_api.db.base import Base
from zeromerma_api.modules.operations.domain.constants import (
    OPERATION_DOCUMENT_STATUS_COMMITTED,
    OPERATION_DOCUMENT_TYPE_CLOSE_COUNTER_ADJUSTMENT,
    OPERATION_DOCUMENT_TYPE_CLOSE_WASTE_ADJUSTMENT,
    OPERATION_DOCUMENT_TYPE_COUNTER_TRANSFER,
    OPERATION_UNIT_OF_MEASURE_EACH,
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class WasteReason(Base):
    __tablename__ = "waste_reasons"

    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)


class OperationDocument(Base):
    __tablename__ = "operation_documents"
    __table_args__ = (
        CheckConstraint(
            "document_type IN ("
            "'COUNTER_TRANSFER', "
            "'WASTE_RECORD', "
            "'BRANCH_TRANSFER_SHIPMENT', "
            "'BRANCH_TRANSFER_RECEIPT', "
            "'CLOSE_COUNTER_ADJUSTMENT', "
            "'CLOSE_WASTE_ADJUSTMENT'"
            ")",
            name="ck_operation_documents_document_type_valid",
        ),
        CheckConstraint(
            "status IN ("
            "'DRAFT', "
            "'COMMITTED', "
            "'IN_TRANSIT', "
            "'RECEIVED', "
            "'RECEIVED_WITH_VARIANCE', "
            "'CANCELLED'"
            ")",
            name="ck_operation_documents_status_valid",
        ),
        CheckConstraint(
            "source_bucket_code IS NULL OR "
            "source_bucket_code IN ('BACKROOM', 'COUNTER', 'IN_TRANSIT', 'WASTE')",
            name="ck_operation_documents_source_bucket_valid",
        ),
        CheckConstraint(
            "destination_bucket_code IS NULL OR "
            "destination_bucket_code IN ('BACKROOM', 'COUNTER', 'IN_TRANSIT', 'WASTE')",
            name="ck_operation_documents_destination_bucket_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_type: Mapped[str] = mapped_column(
        String(40),
        default=OPERATION_DOCUMENT_TYPE_COUNTER_TRANSFER,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=OPERATION_DOCUMENT_STATUS_COMMITTED,
        nullable=False,
    )
    source_branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    destination_branch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=True,
    )
    source_bucket_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    destination_bucket_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
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
    reason_code: Mapped[str | None] = mapped_column(
        String(40),
        ForeignKey("waste_reasons.code", ondelete="RESTRICT"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operation_documents.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    committed_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class OperationDocumentLine(Base):
    __tablename__ = "operation_document_lines"
    __table_args__ = (
        UniqueConstraint(
            "operation_document_id",
            "line_number",
            name="uq_operation_document_lines_document_line_number",
        ),
        CheckConstraint("quantity > 0", name="ck_operation_document_lines_quantity_positive"),
        CheckConstraint(
            "expected_quantity IS NULL OR expected_quantity > 0",
            name="ck_operation_document_lines_expected_quantity_positive",
        ),
        CheckConstraint(
            "received_quantity IS NULL OR received_quantity >= 0",
            name="ck_operation_document_lines_received_quantity_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operation_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operation_documents.id", ondelete="CASCADE"),
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
    expected_quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    received_quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    unit_of_measure_code: Mapped[str] = mapped_column(
        String(16),
        default=OPERATION_UNIT_OF_MEASURE_EACH,
        nullable=False,
    )
    variance_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


_ = (
    OPERATION_DOCUMENT_TYPE_CLOSE_COUNTER_ADJUSTMENT,
    OPERATION_DOCUMENT_TYPE_CLOSE_WASTE_ADJUSTMENT,
)
