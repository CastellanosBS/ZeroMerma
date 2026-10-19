"""Lot identity and materialized physical allocations share the inventory ledger."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from zeromerma_api.db.base import Base

if TYPE_CHECKING:
    from zeromerma_api.modules.inventory.infrastructure.models import (
        InventoryReservation,
        InventoryReservationEvent,
    )


class InventoryLot(Base):
    __tablename__ = "inventory_lots"
    __table_args__ = (
        UniqueConstraint("product_id", "lot_code", name="uq_inventory_lot_product_code"),
        CheckConstraint("length(btrim(lot_code)) > 0", name="code_required"),
        CheckConstraint("NOT unidentified OR expires_at IS NULL", name="unknown_expiry"),
        CheckConstraint(
            "produced_at IS NULL OR expires_at IS NULL OR produced_at < expires_at",
            name="dates_valid",
        ),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    lot_code: Mapped[str] = mapped_column(String(120))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    produced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unidentified: Mapped[bool] = mapped_column(Boolean, default=False)
    source_document_type: Mapped[str] = mapped_column(String(64))
    source_document_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    source_line_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    idempotency_record_id: Mapped[UUID] = mapped_column(
        ForeignKey("idempotency_records.id", ondelete="RESTRICT")
    )
    operator_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class InventoryLotBalance(Base):
    __tablename__ = "inventory_lot_balances"
    __table_args__ = (
        UniqueConstraint(
            "branch_id", "product_id", "location_code", "lot_id", name="uq_inventory_lot_balance"
        ),
        CheckConstraint(
            "quantity_on_hand >= 0 AND quantity_reserved >= 0 "
            "AND quantity_reserved <= quantity_on_hand AND quantity_on_hand <> 'NaN'::numeric",
            name="quantities_valid",
        ),
        CheckConstraint(
            "location_code IN ('BACKROOM','COUNTER','IN_TRANSIT','WASTE','QUARANTINE','WIP')",
            name="location_valid",
        ),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"))
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    lot_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_lots.id", ondelete="RESTRICT"))
    location_code: Mapped[str] = mapped_column(String(32))
    quantity_on_hand: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal(0))
    quantity_reserved: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal(0))


class InventoryMovementLotAllocation(Base):
    __tablename__ = "inventory_movement_lot_allocations"
    __table_args__ = (
        UniqueConstraint("movement_id", "lot_id", name="uq_inventory_movement_lot"),
        CheckConstraint("quantity > 0 AND quantity <> 'NaN'::numeric", name="quantity_valid"),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    movement_id: Mapped[UUID] = mapped_column(
        ForeignKey("inventory_movements.id", ondelete="RESTRICT")
    )
    lot_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_lots.id", ondelete="RESTRICT"))
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))


class InventoryReservationLotAllocation(Base):
    __tablename__ = "inventory_reservation_lot_allocations"
    __table_args__ = (
        UniqueConstraint("reservation_id", "lot_id", name="uq_inventory_reservation_lot"),
        CheckConstraint(
            "quantity > 0 AND consumed_quantity >= 0 AND released_quantity >= 0 "
            "AND consumed_quantity + released_quantity <= quantity",
            name="quantities_valid",
        ),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    reservation_id: Mapped[UUID] = mapped_column(
        ForeignKey("inventory_reservations.id", ondelete="RESTRICT")
    )
    lot_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_lots.id", ondelete="RESTRICT"))
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    consumed_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal(0))
    released_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal(0))
    reservation: Mapped[InventoryReservation] = relationship(lazy="raise")


class InventoryReservationEventLotAllocation(Base):
    __tablename__ = "inventory_reservation_event_lots"
    __table_args__ = (
        UniqueConstraint(
            "reservation_event_id", "lot_id", name="uq_inventory_reservation_event_lot"
        ),
        CheckConstraint("quantity > 0 AND quantity <> 'NaN'::numeric", name="quantity_valid"),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    reservation_event_id: Mapped[UUID] = mapped_column(
        ForeignKey("inventory_reservation_events.id", ondelete="RESTRICT")
    )
    lot_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_lots.id", ondelete="RESTRICT"))
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    reservation_event: Mapped[InventoryReservationEvent] = relationship(lazy="raise")
