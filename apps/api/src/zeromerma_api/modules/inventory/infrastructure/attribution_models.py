from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from zeromerma_api.db.base import Base

if TYPE_CHECKING:
    from zeromerma_api.modules.inventory.infrastructure.models import InventoryMovement


class ClassInventoryObligation(Base):
    __tablename__ = "class_inventory_obligations"
    __table_args__ = (
        UniqueConstraint("sale_line_id", name="uq_class_inventory_obligation_sale_line"),
        CheckConstraint("required_quantity > 0", name="ck_class_obligation_required"),
        CheckConstraint(
            "attributed_quantity >= 0 AND attributed_quantity <= required_quantity",
            name="ck_class_obligation_attributed",
        ),
        CheckConstraint(
            "(status = 'OPEN' AND attributed_quantity < required_quantity) OR "
            "(status = 'FULFILLED' AND attributed_quantity = required_quantity)",
            name="ck_class_obligation_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sale_lines.id", ondelete="RESTRICT"), nullable=False
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)
    product_class_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_classes.id"), nullable=False
    )
    required_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    attributed_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, default=Decimal("0")
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class ClassInventoryAttribution(Base):
    __tablename__ = "class_inventory_attributions"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_class_attribution_quantity"),
        UniqueConstraint(
            "idempotency_record_id", "causal_effect_code", name="uq_class_attribution_effect"
        ),
        UniqueConstraint("inventory_movement_id", name="uq_class_attribution_movement"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    obligation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("class_inventory_obligations.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    inventory_movement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_movements.id", ondelete="RESTRICT"), nullable=True
    )
    inventory_movement: Mapped[InventoryMovement | None] = relationship(lazy="raise")
    idempotency_record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("idempotency_records.id", ondelete="RESTRICT"), nullable=False
    )
    causal_effect_code: Mapped[str] = mapped_column(String(160), nullable=False)
    source_document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
