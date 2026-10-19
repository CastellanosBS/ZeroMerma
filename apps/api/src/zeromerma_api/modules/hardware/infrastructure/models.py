"""Workstation device bindings and immutable causal local command identities."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from zeromerma_api.db.base import Base


class HardwareDeviceBinding(Base):
    __tablename__ = "hardware_device_bindings"
    __table_args__ = (
        CheckConstraint("kind IN ('PRINTER','DRAWER')", name="ck_hardware_binding_kind"),
        CheckConstraint("environment IN ('SANDBOX','PRODUCTION')", name="ck_hardware_environment"),
        CheckConstraint("version > 0", name="ck_hardware_binding_version"),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"))
    workstation_id: Mapped[UUID] = mapped_column(ForeignKey("workstations.id", ondelete="RESTRICT"))
    kind: Mapped[str] = mapped_column(String(16))
    adapter_code: Mapped[str] = mapped_column(String(64))
    adapter_version: Mapped[str] = mapped_column(String(32))
    environment: Mapped[str] = mapped_column(String(16))
    origin: Mapped[str] = mapped_column(String(200))
    certification_evidence_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)


class HardwareCommandIntent(Base):
    __tablename__ = "hardware_command_intents"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"))
    workstation_id: Mapped[UUID] = mapped_column(ForeignKey("workstations.id", ondelete="RESTRICT"))
    binding_id: Mapped[UUID] = mapped_column(
        ForeignKey("hardware_device_bindings.id", ondelete="RESTRICT")
    )
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    cash_entry_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("financial_entries.id", ondelete="RESTRICT"), unique=True
    )
    command: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
