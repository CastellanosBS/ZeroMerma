from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from zeromerma_api.modules.inventory.infrastructure.lot_models import (
        InventoryMovementLotAllocation,
    )

from zeromerma_api.db.base import Base
from zeromerma_api.modules.inventory.domain.constants import (
    INVENTORY_ADJUSTMENT_TYPE_INCREASE,
    INVENTORY_LOCATION_BACKROOM,
    INVENTORY_MOVEMENT_DIRECTION_IN,
    INVENTORY_MOVEMENT_TYPE_MANUAL_ADJUSTMENT,
    VALID_INVENTORY_LOCATION_CODES,
    VALID_INVENTORY_MOVEMENT_TYPES,
)
from zeromerma_api.modules.inventory.domain.quantities import inventory_calculation
from zeromerma_api.modules.inventory.infrastructure.reconciliation_models import (
    InventoryReconciliationManifest as InventoryReconciliationManifest,
)
from zeromerma_api.modules.inventory.infrastructure.reconciliation_models import (
    InventoryReconciliationRow as InventoryReconciliationRow,
)

LOCATION_CHECK = (
    "location_code IN ("
    + ",".join(repr(value) for value in sorted(VALID_INVENTORY_LOCATION_CODES))
    + ")"
)
MOVEMENT_TYPE_CHECK = (
    "movement_type IN ("
    + ",".join(repr(value) for value in sorted(VALID_INVENTORY_MOVEMENT_TYPES))
    + ")"
)
MOVEMENT_CAUSE_CHECK = (
    "context_version IS NULL OR (context_version = 1 AND idempotency_record_id IS NOT NULL "
    "AND causal_effect_code IS NOT NULL AND length(btrim(causal_effect_code)) > 0 "
    "AND source_document_type IS NOT NULL AND source_document_id IS NOT NULL "
    "AND operator_user_id IS NOT NULL AND source_app IS NOT NULL "
    "AND correlation_id IS NOT NULL AND source_quantity > 0 "
    "AND source_quantity <> 'NaN'::numeric AND length(btrim(source_uom)) > 0 "
    "AND conversion_factor > 0 AND conversion_factor <> 'NaN'::numeric "
    "AND quantity = source_quantity * conversion_factor) IS TRUE"
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class InventoryBalance(Base):
    __tablename__ = "inventory_balances"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "branch_id",
            "location_code",
            name="uq_inventory_balances_product_branch_location",
        ),
        CheckConstraint(
            LOCATION_CHECK,
            name="location_valid",
        ),
        CheckConstraint(
            "quantity_reserved >= 0 AND quantity_reserved <> 'NaN'::numeric "
            "AND quantity_on_hand <> 'NaN'::numeric",
            name="reserved_valid",
        ),
        CheckConstraint(
            "inventory_value IS NULL OR (inventory_value >= 0 "
            "AND inventory_value <> 'NaN'::numeric "
            "AND quantity_on_hand >= 0 AND (quantity_on_hand <> 0 OR inventory_value = 0))",
            name="value_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    location_code: Mapped[str] = mapped_column(
        String(32),
        default=INVENTORY_LOCATION_BACKROOM,
        nullable=False,
    )
    quantity_on_hand: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), default=Decimal("0"), nullable=False
    )
    quantity_reserved: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), default=Decimal("0"), server_default=text("0"), nullable=False
    )
    inventory_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))

    @property
    @inventory_calculation
    def quantity_available(self) -> Decimal:
        return self.quantity_on_hand - self.quantity_reserved

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class InventoryAdjustment(Base):
    __tablename__ = "inventory_adjustments"
    __table_args__ = (
        CheckConstraint(
            LOCATION_CHECK,
            name="location_valid",
        ),
        CheckConstraint(
            "adjustment_type IN ('INCREASE', 'DECREASE', 'SET_COUNTED')",
            name="ck_inventory_adjustments_type_valid",
        ),
        CheckConstraint(
            "quantity > 0 OR (adjustment_type = 'SET_COUNTED' AND quantity = 0)",
            name="quantity_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    location_code: Mapped[str] = mapped_column(
        String(32),
        default=INVENTORY_LOCATION_BACKROOM,
        nullable=False,
    )
    adjustment_type: Mapped[str] = mapped_column(
        String(32),
        default=INVENTORY_ADJUSTMENT_TYPE_INCREASE,
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    previous_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    new_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    reason: Mapped[str] = mapped_column(String(160), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        CheckConstraint(
            LOCATION_CHECK,
            name="location_valid",
        ),
        CheckConstraint(
            MOVEMENT_TYPE_CHECK,
            name="type_valid",
        ),
        CheckConstraint(
            "direction IN ('IN', 'OUT')", name="ck_inventory_movements_direction_valid"
        ),
        CheckConstraint("quantity > 0", name="ck_inventory_movements_quantity_positive"),
        CheckConstraint(MOVEMENT_CAUSE_CHECK, name="cause_valid"),
        CheckConstraint(
            "((unit_cost IS NULL AND total_cost IS NULL AND cost_evidence_reference IS NULL) OR "
            "(unit_cost >= 0 AND unit_cost <> 'NaN'::numeric "
            "AND total_cost >= 0 AND total_cost <> 'NaN'::numeric "
            "AND length(btrim(cost_evidence_reference)) > 0)) IS TRUE",
            name="cost_valid",
        ),
        UniqueConstraint("idempotency_record_id", "causal_effect_code", name="uq_inventory_cause"),
        UniqueConstraint(
            "source_document_type",
            "source_document_id",
            "reversal_of_movement_id",
            name="uq_inventory_reversal_cause",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_allocations: Mapped[list[InventoryMovementLotAllocation]] = relationship(
        "InventoryMovementLotAllocation",
        lazy="raise",
        order_by="InventoryMovementLotAllocation.lot_id",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    location_code: Mapped[str] = mapped_column(
        String(32),
        default=INVENTORY_LOCATION_BACKROOM,
        nullable=False,
    )
    movement_type: Mapped[str] = mapped_column(
        String(40),
        default=INVENTORY_MOVEMENT_TYPE_MANUAL_ADJUSTMENT,
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(
        String(8),
        default=INVENTORY_MOVEMENT_DIRECTION_IN,
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(32), nullable=False)
    source_document_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_line_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    source_uom: Mapped[str | None] = mapped_column(String(32))
    conversion_factor: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    context_version: Mapped[int | None] = mapped_column(Integer)
    idempotency_record_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("idempotency_records.id", ondelete="RESTRICT")
    )
    causal_effect_code: Mapped[str | None] = mapped_column(String(160))
    source_app: Mapped[str | None] = mapped_column(String(20))
    operation_code: Mapped[str | None] = mapped_column(String(160))
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    causation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    request_id: Mapped[str | None] = mapped_column(String(128))
    workstation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workstations.id", ondelete="RESTRICT")
    )
    cash_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cash_sessions.id", ondelete="RESTRICT")
    )
    related_branch_ids: Mapped[list[str] | None] = mapped_column(JSONB)
    reversal_of_movement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_movements.id", ondelete="RESTRICT")
    )
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    total_cost: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    cost_evidence_reference: Mapped[str | None] = mapped_column(String(240))
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=utc_now)
    adjustment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory_adjustments.id", ondelete="RESTRICT"),
        nullable=True,
    )
    operator_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason: Mapped[str | None] = mapped_column(String(160), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    balance_after: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"
    __table_args__ = (
        CheckConstraint("location_code IN ('BACKROOM','COUNTER')", name="location_valid"),
        CheckConstraint(
            "quantity > 0 AND quantity <> 'NaN'::numeric AND consumed_quantity >= 0 "
            "AND released_quantity >= 0 AND consumed_quantity + released_quantity <= quantity",
            name="quantities_valid",
        ),
        CheckConstraint(
            "(status = 'ACTIVE' AND consumed_quantity = 0 AND released_quantity < quantity) OR "
            "(status = 'PARTIALLY_CONSUMED' AND consumed_quantity > 0 "
            "AND consumed_quantity + released_quantity < quantity) OR "
            "(status = 'CONSUMED' AND consumed_quantity = quantity) OR "
            "(status = 'RELEASED' AND released_quantity > 0 "
            "AND consumed_quantity + released_quantity = quantity)",
            name="status_valid",
        ),
        UniqueConstraint(
            "idempotency_record_id", "causal_effect_code", name="uq_inventory_reservation_cause"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    location_code: Mapped[str] = mapped_column(String(32))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    consumed_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    released_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    unit_of_measure: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    source_document_type: Mapped[str] = mapped_column(String(64))
    source_document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    source_line_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    idempotency_record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("idempotency_records.id", ondelete="RESTRICT")
    )
    causal_effect_code: Mapped[str] = mapped_column(String(160))
    operator_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class InventoryReservationEvent(Base):
    __tablename__ = "inventory_reservation_events"
    __table_args__ = (
        CheckConstraint("event_type IN ('RESERVE','RELEASE','CONSUME')", name="type_valid"),
        CheckConstraint("quantity > 0 AND quantity <> 'NaN'::numeric", name="quantity_valid"),
        CheckConstraint(
            "(event_type = 'CONSUME' AND inventory_movement_id IS NOT NULL) OR "
            "(event_type <> 'CONSUME' AND inventory_movement_id IS NULL)",
            name="movement_valid",
        ),
        UniqueConstraint(
            "idempotency_record_id",
            "causal_effect_code",
            name="uq_inventory_reservation_event_cause",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reservation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_reservations.id", ondelete="RESTRICT")
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"))
    event_type: Mapped[str] = mapped_column(String(16))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    inventory_movement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_movements.id", ondelete="RESTRICT"), unique=True
    )
    idempotency_record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("idempotency_records.id", ondelete="RESTRICT")
    )
    causal_effect_code: Mapped[str] = mapped_column(String(160))
    operator_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    reason: Mapped[str | None] = mapped_column(String(160))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    reservation: Mapped[InventoryReservation] = relationship(lazy="raise")
    inventory_movement: Mapped[InventoryMovement | None] = relationship(lazy="raise")
