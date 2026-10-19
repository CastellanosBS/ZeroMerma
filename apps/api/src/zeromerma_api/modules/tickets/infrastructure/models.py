"""Immutable document snapshots, created by the owning business transaction."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from zeromerma_api.db.base import Base


class ReceiptSnapshot(Base):
    __tablename__ = "receipt_snapshots"
    __table_args__ = (
        UniqueConstraint("source_kind", "source_id", name="uq_receipt_source"),
        CheckConstraint("source_kind IN ('SALE','ORDER_PAYMENT','RETURN')", name="ck_receipt_kind"),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"))
    workstation_id: Mapped[UUID] = mapped_column(ForeignKey("workstations.id", ondelete="RESTRICT"))
    source_kind: Mapped[str] = mapped_column(String(24))
    source_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    document: Mapped[dict[str, Any]] = mapped_column(JSONB)
    document_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
