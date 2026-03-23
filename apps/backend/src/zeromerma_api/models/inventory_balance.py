# apps/backend/src/zeromerma_api/models/inventory_balance.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, created_at_col, updated_at_col

if TYPE_CHECKING:
    from .branch import Branch
    from .product import Product


class InventoryBalance(Base):
    """
    Snapshot inventory table used for fast operational stock reads and atomic decrements.

    This table complements the inventory_movement ledger:
    - inventory_movement = historical audit trail
    - inventory_balance  = current operational state
    """

    __tablename__ = "inventory_balance"
    __table_args__ = (
        Index(
            "uq_inventory_balance_branch_product",
            "branch_id",
            "product_id",
            unique=True,
        ),
        CheckConstraint("on_hand >= 0", name="ck_inventory_balance_on_hand_nonneg"),
        CheckConstraint("reserved >= 0", name="ck_inventory_balance_reserved_nonneg"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branch.id", ondelete="RESTRICT"),
        nullable=False,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="RESTRICT"),
        nullable=False,
    )

    on_hand: Mapped[Decimal] = mapped_column(
        Numeric(18, 3),
        nullable=False,
        server_default=text("0"),
        default=0,
    )

    reserved: Mapped[Decimal] = mapped_column(
        Numeric(18, 3),
        nullable=False,
        server_default=text("0"),
        default=0,
    )

    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()

    branch: Mapped["Branch"] = relationship()
    product: Mapped["Product"] = relationship(back_populates="balances")
