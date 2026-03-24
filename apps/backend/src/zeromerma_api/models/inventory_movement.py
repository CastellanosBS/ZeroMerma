# apps/backend/src/zeromerma_api/models/inventory_movement.py
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, created_at_col, updated_at_col

if TYPE_CHECKING:
    pass


class MovementReason(str, Enum):
    """
    Allowed inventory movement reasons for the immutable stock ledger.

    Conventions:
    - negative qty -> stock outflow
    - positive qty -> stock inflow
    """

    SALE = "SALE"
    SALE_VOID = "SALE_VOID"
    SALE_REFUND = "SALE_REFUND"
    PURCHASE = "PURCHASE"
    ADJUSTMENT = "ADJUSTMENT"
    PRODUCTION_INPUT = "PRODUCTION_INPUT"
    PRODUCTION_OUTPUT = "PRODUCTION_OUTPUT"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    OPENING_BALANCE = "OPENING_BALANCE"


class InventoryMovement(Base):
    """
    One immutable stock movement row.

    Traceability:
    - branch_id / product_id identify where and what changed
    - reason explains why
    - ref_type / ref_id link the movement to the generating document
    - created_by_id attributes the action when possible
    """

    __tablename__ = "inventory_movement"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branch.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    qty: Mapped[float] = mapped_column(Numeric(18, 3), nullable=False)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)

    ref_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ref_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()

    product = relationship("Product", back_populates="movements")
