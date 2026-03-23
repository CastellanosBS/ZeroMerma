from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, created_at_col, updated_at_col

if TYPE_CHECKING:
    from .customer_order import CustomerOrder
    from .product import Product


class CustomerOrderItem(Base):
    """
    Customer order line.

    Snapshot fields freeze the commercial commitment at order creation time:
    - unit_price_snapshot
    - line_total_snapshot

    2B.1 intentionally does NOT freeze product names yet; current product
    master data is used for display, while monetary commitment stays frozen.
    """

    __tablename__ = "customer_order_item"
    __table_args__ = (
        Index("ix_customer_order_item_customer_order_id", "customer_order_id"),
        Index("ix_customer_order_item_product_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    customer_order_id: Mapped[int] = mapped_column(
        ForeignKey("customer_order.id", ondelete="CASCADE"),
        nullable=False,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="RESTRICT"),
        nullable=False,
    )

    qty: Mapped[Decimal] = mapped_column(
        Numeric(18, 3),
        nullable=False,
    )

    unit_price_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    line_total_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()

    customer_order: Mapped["CustomerOrder"] = relationship(
        back_populates="items",
    )

    product: Mapped["Product"] = relationship()
