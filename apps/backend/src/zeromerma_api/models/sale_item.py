# PURPOSE: Sale line items.
#          Each line references a product, quantity, and price snapshot.

from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class SaleItem(Base):
    """
    SaleItem:
      - belongs to one sale
      - references one product
      - stores qty and unit_price (snapshot at sale time)
      - stores line_total = qty * unit_price (computed by backend)
    """

    __tablename__ = "sale_item"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sale.id", ondelete="CASCADE"),  # if sale deleted, delete items
        index=True,
        nullable=False,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    qty: Mapped[float] = mapped_column(
        Numeric(18, 3),  # allow fractional quantities if needed
        nullable=False,
    )

    unit_price: Mapped[float] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    line_total: Mapped[float] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")
