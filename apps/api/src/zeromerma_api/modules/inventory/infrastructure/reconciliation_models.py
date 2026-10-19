"""Immutable authority declarations and resumable inventory reconciliation evidence."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from zeromerma_api.db.base import Base


class InventoryReconciliationManifest(Base):
    __tablename__ = "inventory_reconciliation_manifests"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"))
    manifest_sha256: Mapped[str] = mapped_column(String(64))
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB)
    admitted_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )


class InventoryReconciliationRow(Base):
    __tablename__ = "inventory_reconciliation_rows"
    __table_args__ = (
        UniqueConstraint("manifest_id", "row_key", name="uq_inventory_reconciliation_row"),
        CheckConstraint("action IN ('OPENING','REBUILD')", name="action_valid"),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    manifest_id: Mapped[UUID] = mapped_column(
        ForeignKey("inventory_reconciliation_manifests.id", ondelete="RESTRICT")
    )
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"))
    row_key: Mapped[str] = mapped_column(String(80))
    row_sha256: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(16))
    idempotency_record_id: Mapped[UUID] = mapped_column(
        ForeignKey("idempotency_records.id", ondelete="RESTRICT")
    )
    inventory_movement_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("inventory_movements.id", ondelete="RESTRICT"), unique=True
    )
    reconciliation: Mapped[dict[str, Any]] = mapped_column(JSONB)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
