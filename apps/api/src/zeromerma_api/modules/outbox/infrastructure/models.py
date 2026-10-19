from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from zeromerma_api.db.base import Base


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
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
        CheckConstraint(
            "schema_version >= 0 AND (context_version = 0 OR schema_version > 0)",
            name="schema_version_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aggregate_type: Mapped[str] = mapped_column(String(120), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(120), nullable=False)
    event_name: Mapped[str] = mapped_column(String(160), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    context_version: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    source_app: Mapped[str] = mapped_column(String(20), default="UNKNOWN", server_default="UNKNOWN")
    actor_type: Mapped[str] = mapped_column(String(20), default="UNKNOWN", server_default="UNKNOWN")
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    branch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    request_id: Mapped[str | None] = mapped_column(String(120))
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
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    headers: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        nullable=False,
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
