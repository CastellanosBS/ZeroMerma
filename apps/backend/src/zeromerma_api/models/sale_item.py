# apps/backend/src/zeromerma_api/models/sale_item.py
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .product import Product
    from .sale import Sale


class SaleItem(Base):
    """
    Sale line item.

    Stores the pricing snapshot used at sale time:
      - qty
      - unit_price
      - line_total
    """

    __tablename__ = "sale_item"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sale.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    qty: Mapped[Decimal] = mapped_column(
        Numeric(18, 3),
        nullable=False,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    line_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    sale: Mapped["Sale"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="sale_items")
