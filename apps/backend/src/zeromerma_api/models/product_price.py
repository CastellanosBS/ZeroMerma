# apps/backend/src/zeromerma_api/models/product_price.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, created_at_col, updated_at_col

if TYPE_CHECKING:
    from .branch import Branch
    from .product import Product
    from .user_account import UserAccount


class ProductPrice(Base):
    """
    Branch-specific product price override.

    Effective price policy:
        effective_price = COALESCE(product_price.price, product.sale_price)
    """

    __tablename__ = "product_price"
    __table_args__ = (
        UniqueConstraint(
            "branch_id",
            "product_id",
            name="uq_product_price_branch_product",
        ),
        CheckConstraint("price >= 0", name="ck_product_price_price_nonneg"),
    )

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

    price: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        server_default=text("'MXN'"),
        default="MXN",
    )

    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()

    branch: Mapped["Branch"] = relationship()
    product: Mapped["Product"] = relationship(back_populates="price_overrides")
    created_by: Mapped["UserAccount | None"] = relationship()
