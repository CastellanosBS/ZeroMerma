from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from zeromerma_api.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_idempotency_records_key"),
        CheckConstraint(
            "idempotency_key::text ~ "
            "'^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'",
            name="idempotency_key_uuid7",
        ),
        CheckConstraint(
            "status IN ('PROCESSING','COMPLETED','REJECTED','UNKNOWN')",
            name="idempotency_status_valid",
        ),
        CheckConstraint("fingerprint_version > 0", name="idempotency_fingerprint_version_positive"),
        CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'", name="idempotency_fingerprint_format"
        ),
        CheckConstraint(
            "response_status IS NULL OR response_status BETWEEN 100 AND 599",
            name="idempotency_response_status_valid",
        ),
        CheckConstraint(
            "response_fingerprint IS NULL OR response_fingerprint ~ '^[0-9a-f]{64}$'",
            name="idempotency_response_fingerprint_format",
        ),
        CheckConstraint(
            "response_payload IS NULL OR jsonb_typeof(response_payload) = 'object'",
            name="idempotency_response_payload_object",
        ),
        CheckConstraint(
            "response_reference IS NULL OR jsonb_typeof(response_reference) = 'object'",
            name="idempotency_response_reference_object",
        ),
        CheckConstraint(
            "status NOT IN ('COMPLETED','REJECTED') OR "
            "(completed_at IS NOT NULL AND response_status IS NOT NULL "
            "AND response_schema_version IS NOT NULL "
            "AND response_fingerprint IS NOT NULL "
            "AND (response_payload IS NOT NULL OR response_reference IS NOT NULL))",
            name="idempotency_terminal_result",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    idempotency_key: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    operation_code: Mapped[str] = mapped_column(String(120), nullable=False)
    fingerprint_version: Mapped[int] = mapped_column(Integer, nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    branch_id: Mapped[UUID | None] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"))
    workstation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workstations.id", ondelete="RESTRICT")
    )
    cash_session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("cash_sessions.id", ondelete="RESTRICT")
    )
    context_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(120))
    resource_id: Mapped[str | None] = mapped_column(String(160))
    response_status: Mapped[int | None] = mapped_column(Integer)
    response_schema_version: Mapped[str | None] = mapped_column(String(40))
    response_fingerprint: Mapped[str | None] = mapped_column(String(64))
    response_reference: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    error_code: Mapped[str | None] = mapped_column(String(120))
    first_request_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


Index(
    "ix_idempotency_records_response_expiry",
    IdempotencyRecord.response_expires_at,
    postgresql_where=(
        IdempotencyRecord.response_payload.is_not(None)
        & IdempotencyRecord.response_expires_at.is_not(None)
    ),
)
