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
from zeromerma_api.modules.corrections.domain.constants import (
    CORRECTION_STATUS_COMMITTED,
    CORRECTION_TYPE_DELTA_ADJUSTMENT,
    CORRECTION_TYPE_DESTINATION_ADJUSTMENT,
)
from zeromerma_api.modules.operations.domain.constants import (
    OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT,
    OPERATION_DOCUMENT_TYPE_COUNTER_TRANSFER,
    OPERATION_DOCUMENT_TYPE_WASTE_RECORD,
    OPERATION_UNIT_OF_MEASURE_EACH,
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class CorrectionReason(Base):
    __tablename__ = "correction_reasons"

    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)


class CorrectionDocument(Base):
    __tablename__ = "correction_documents"
    __table_args__ = (
        CheckConstraint(
            "target_document_type IN ("
            "'COUNTER_TRANSFER', "
            "'WASTE_RECORD', "
            "'BRANCH_TRANSFER_SHIPMENT'"
            ")",
            name="ck_correction_documents_target_document_type_valid",
        ),
        CheckConstraint(
            "correction_type IN ('DELTA_ADJUSTMENT', 'DESTINATION_ADJUSTMENT')",
            name="ck_correction_documents_correction_type_valid",
        ),
        CheckConstraint(
            "status IN ('COMMITTED')",
            name="ck_correction_documents_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operation_documents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    correction_type: Mapped[str] = mapped_column(
        String(40),
        default=CORRECTION_TYPE_DELTA_ADJUSTMENT,
        nullable=False,
    )
    source_branch_id: Mapped[uuid.UUID] = mapped_column(
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
    reason_code: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("correction_reasons.code", ondelete="RESTRICT"),
        nullable=False,
    )
    corrected_destination_branch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default=CORRECTION_STATUS_COMMITTED,
        nullable=False,
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


class CorrectionDocumentLine(Base):
    __tablename__ = "correction_document_lines"
    __table_args__ = (
        UniqueConstraint(
            "correction_document_id",
            "line_number",
            name="uq_correction_document_lines_document_line_number",
        ),
        CheckConstraint(
            "delta_quantity <> 0",
            name="ck_correction_document_lines_delta_quantity_non_zero",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    correction_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("correction_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    target_line_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operation_document_lines.id", ondelete="RESTRICT"),
        nullable=True,
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
    delta_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_of_measure_code: Mapped[str] = mapped_column(
        String(16),
        default=OPERATION_UNIT_OF_MEASURE_EACH,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


_ = (
    OPERATION_DOCUMENT_TYPE_COUNTER_TRANSFER,
    OPERATION_DOCUMENT_TYPE_WASTE_RECORD,
    OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT,
    CORRECTION_TYPE_DESTINATION_ADJUSTMENT,
)
