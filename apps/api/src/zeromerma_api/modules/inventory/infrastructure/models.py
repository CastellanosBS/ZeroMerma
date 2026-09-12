from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from zeromerma_api.db.base import Base
from zeromerma_api.modules.inventory.domain.constants import (
    INVENTORY_ADJUSTMENT_TYPE_INCREASE,
    INVENTORY_LOCATION_BACKROOM,
    INVENTORY_MOVEMENT_DIRECTION_IN,
    INVENTORY_MOVEMENT_TYPE_MANUAL_ADJUSTMENT,
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
            "location_code IN ('BACKROOM', 'COUNTER', 'IN_TRANSIT', 'WASTE')",
            name="ck_inventory_balances_location_valid",
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
            "location_code IN ('BACKROOM', 'COUNTER', 'IN_TRANSIT', 'WASTE')",
            name="ck_inventory_adjustments_location_valid",
        ),
        CheckConstraint(
            "adjustment_type IN ('INCREASE', 'DECREASE', 'SET_COUNTED')",
            name="ck_inventory_adjustments_type_valid",
        ),
        CheckConstraint("quantity > 0", name="ck_inventory_adjustments_quantity_positive"),
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
            "location_code IN ('BACKROOM', 'COUNTER', 'IN_TRANSIT', 'WASTE')",
            name="ck_inventory_movements_location_valid",
        ),
        CheckConstraint(
            "movement_type IN ("
            "'MANUAL_ADJUSTMENT', "
            "'STOCK_COUNT_ADJUSTMENT', "
            "'TRANSFER_DISPATCH', "
            "'TRANSFER_RECEIPT', "
            "'PURCHASE_RECEIPT', "
            "'PRODUCTION_CONSUMPTION', "
            "'PRODUCTION_OUTPUT', "
            "'WASTE_RECORD'"
            ")",
            name="ck_inventory_movements_type_valid",
        ),
        CheckConstraint(
            "direction IN ('IN', 'OUT')", name="ck_inventory_movements_direction_valid"
        ),
        CheckConstraint("quantity > 0", name="ck_inventory_movements_quantity_positive"),
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
