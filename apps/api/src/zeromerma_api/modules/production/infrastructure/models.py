from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
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
from zeromerma_api.modules.production.domain.constants import (
    PRODUCTION_INPUT_STATUS_AVAILABLE,
    PRODUCTION_STATUS_DRAFT,
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class ProductionBatch(Base):
    __tablename__ = "production_batches"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')",
            name="ck_production_batches_status_valid",
        ),
        CheckConstraint(
            "planned_output_qty > 0", name="ck_production_batches_planned_output_positive"
        ),
        CheckConstraint(
            "actual_output_qty IS NULL OR actual_output_qty >= 0",
            name="ck_production_batches_actual_output_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), default=PRODUCTION_STATUS_DRAFT, nullable=False)
    planned_output_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    actual_output_qty: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    variance_qty: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    variance_percent: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    planned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    started_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    completed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    cancelled_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    variance_reason: Mapped[str | None] = mapped_column(String(180), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class ProductionBatchInput(Base):
    __tablename__ = "production_batch_inputs"
    __table_args__ = (
        UniqueConstraint(
            "production_batch_id",
            "input_product_id",
            name="uq_production_batch_inputs_batch_product",
        ),
        CheckConstraint(
            "required_qty > 0", name="ck_production_batch_inputs_required_qty_positive"
        ),
        CheckConstraint(
            "consumed_qty IS NULL OR consumed_qty >= 0",
            name="ck_production_batch_inputs_consumed_qty_non_negative",
        ),
        CheckConstraint(
            "status IN ('available', 'insufficient', 'unavailable')",
            name="ck_production_batch_inputs_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("production_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    input_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    required_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    consumed_qty: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    available_qty_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    shortage_qty_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    unit_of_measure: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default=PRODUCTION_INPUT_STATUS_AVAILABLE,
        nullable=False,
    )
    standard_cost_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
