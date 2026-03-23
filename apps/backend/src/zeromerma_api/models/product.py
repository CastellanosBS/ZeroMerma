from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, created_at_col, updated_at_col

if TYPE_CHECKING:
    from .inventory_balance import InventoryBalance
    from .inventory_movement import InventoryMovement
    from .product_category import ProductCategory
    from .product_price import ProductPrice
    from .sale_item import SaleItem


class Product(Base):
    """
    Canonical product master aligned with the current database schema.

    Business semantics:
    - is_input = True  -> ingredient/raw material, not sellable in POS
    - is_input = False -> finished/sellable product
    - sale_price stores catalog-level base sale price

    POS projection semantics:
    - quick_name: short POS-friendly label
    - show_in_pos: backend visibility flag
    - is_sellable_in_pos: explicit POS sellability flag
    - default_pos_order: backend-provided default ordering hint

    Important:
    Frontend owns the final UX/layout/keyboard mapping. Backend only exposes
    visibility and default ordering hints.
    """

    __tablename__ = "product"
    __table_args__ = (
        CheckConstraint(
            "uom IN ('PCS', 'KG', 'G', 'L', 'ML')",
            name="ck_product_uom_allowed",
        ),
        Index("ix_product_show_in_pos", "show_in_pos"),
        Index("ix_product_is_sellable_in_pos", "is_sellable_in_pos"),
        Index("ix_product_default_pos_order", "default_pos_order"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    sku: Mapped[str | None] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=True,
        doc="Optional internal SKU / short code.",
    )

    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Human-readable product name.",
    )

    quick_name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Short label for POS presentation.",
    )

    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_category.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
        doc="Optional category linkage during the backward-compatible transition period.",
    )

    uom: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'PCS'"),
        default="PCS",
        doc="Unit of measure. Must satisfy the DB CHECK constraint.",
    )

    is_input: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        default=False,
        doc="True for raw materials / ingredients, False for sellable finished goods.",
    )

    show_in_pos: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        default=True,
        doc="Whether this product is visible in POS bootstrap.",
    )

    is_sellable_in_pos: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        default=True,
        doc="Explicit sellability flag for POS presentation.",
    )

    default_pos_order: Mapped[int] = mapped_column(
        nullable=False,
        server_default=text("100"),
        default=100,
        doc="Default backend-provided ordering hint for POS presentation.",
    )

    sale_price: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
        doc="Catalog-level base sale price.",
    )

    standard_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
        doc="Catalog-level reference cost.",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        default=True,
        doc="Soft-delete flag.",
    )

    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()

    category: Mapped["ProductCategory | None"] = relationship(back_populates="products")
    movements: Mapped[list["InventoryMovement"]] = relationship(back_populates="product")
    balances: Mapped[list["InventoryBalance"]] = relationship(back_populates="product")
    sale_items: Mapped[list["SaleItem"]] = relationship(back_populates="product")
    price_overrides: Mapped[list["ProductPrice"]] = relationship(back_populates="product")
