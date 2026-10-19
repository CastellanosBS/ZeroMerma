from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from zeromerma_api.db.base import Base


class TransferTransitResolution(Base):
    """An immutable confirmation of the physical disposition of outstanding transit stock."""

    __tablename__ = "transfer_transit_resolutions"
    __table_args__ = (
        CheckConstraint("kind IN ('RETURN_TO_ORIGIN', 'SEND_TO_WASTE')", name="kind_valid"),
        CheckConstraint("length(trim(reason)) > 0", name="reason_required"),
        CheckConstraint("origin_branch_id <> destination_branch_id", name="branches_distinct"),
        CheckConstraint(
            "(kind = 'RETURN_TO_ORIGIN' AND destination_location IN ('BACKROOM','QUARANTINE')) OR "
            "(kind = 'SEND_TO_WASTE' AND destination_location = 'WASTE')",
            name="destination_valid",
        ),
        CheckConstraint(
            "(kind = 'RETURN_TO_ORIGIN' AND branch_id = origin_branch_id) OR "
            "(kind = 'SEND_TO_WASTE' AND branch_id = destination_branch_id)",
            name="physical_branch_valid",
        ),
        UniqueConstraint("idempotency_record_id", name="uq_transfer_resolution_command"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("operation_documents.id", ondelete="RESTRICT"), index=True
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"))
    origin_branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="RESTRICT")
    )
    destination_branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="RESTRICT")
    )
    idempotency_record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("idempotency_records.id", ondelete="RESTRICT")
    )
    kind: Mapped[str] = mapped_column(String(32))
    destination_location: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(String(500))
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    workstation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workstations.id", ondelete="RESTRICT"), nullable=True
    )
    cash_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cash_sessions.id", ondelete="RESTRICT"), nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TransferTransitResolutionLine(Base):
    __tablename__ = "transfer_transit_resolution_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        UniqueConstraint("resolution_id", "shipment_line_id", name="uq_transfer_resolution_line"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resolution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("transfer_transit_resolutions.id", ondelete="RESTRICT"), index=True
    )
    shipment_line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("operation_document_lines.id", ondelete="RESTRICT")
    )
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    unit_of_measure: Mapped[str] = mapped_column(String(32))
