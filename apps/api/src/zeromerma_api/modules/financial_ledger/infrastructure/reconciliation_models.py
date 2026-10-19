"""Immutable evidence and per-row progress for resumable financial imports."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from zeromerma_api.db.base import Base


class FinancialImportManifest(Base):
    __tablename__ = "financial_import_manifests"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"))
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    admitted_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )


class FinancialImportRow(Base):
    __tablename__ = "financial_import_rows"
    __table_args__ = (UniqueConstraint("manifest_id", "row_key", name="uq_financial_import_row"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    manifest_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_import_manifests.id", ondelete="RESTRICT")
    )
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"))
    row_key: Mapped[str] = mapped_column(String(80), nullable=False)
    row_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    financial_operation_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_operations.id", ondelete="RESTRICT"), unique=True
    )
    operation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    reconciliation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
