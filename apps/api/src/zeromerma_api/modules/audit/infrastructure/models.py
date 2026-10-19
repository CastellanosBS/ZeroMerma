from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from zeromerma_api.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        CheckConstraint(
            "(context_version = 0 AND source_app = 'UNKNOWN' AND actor_type = 'UNKNOWN') OR "
            "(context_version = 1 AND source_app IN ('POS','BACKOFFICE','API','SYSTEM','WORKER') "
            "AND operation_id IS NOT NULL AND correlation_id IS NOT NULL "
            "AND actor_type IN ('USER','SYSTEM','ANONYMOUS'))",
            name="operation_context_valid",
        ),
        CheckConstraint(
            "jsonb_typeof(related_branch_ids) = 'array'", name="related_branches_array"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        nullable=False,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    context_version: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    source_app: Mapped[str] = mapped_column(String(20), default="UNKNOWN", server_default="UNKNOWN")
    actor_type: Mapped[str] = mapped_column(String(20), default="UNKNOWN", server_default="UNKNOWN")
    operation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    causation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    idempotency_key: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    operation_code: Mapped[str | None] = mapped_column(String(160))
    workstation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    cash_session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    related_branch_ids: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )
