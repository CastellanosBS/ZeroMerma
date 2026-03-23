from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, created_at_col, updated_at_col

if TYPE_CHECKING:
    from .product import Product


class ProductCategory(Base):
    """
    Canonical product category master.

    This model now includes a minimal POS projection layer:
    - quick_name: short UI label
    - show_in_pos: backend visibility flag
    - default_pos_order: backend-provided default ordering hint

    Important:
    The backend provides visibility and default ordering hints, but it does NOT
    define a rigid keyboard mapping. Frontend remains free to build keyboard-first
    or touch-first layouts on top of this projection.
    """

    __tablename__ = "product_category"
    __table_args__ = (
        UniqueConstraint("code", name="uq_product_category_code"),
        Index("ix_product_category_show_in_pos", "show_in_pos"),
        Index("ix_product_category_default_pos_order", "default_pos_order"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    code: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        doc="Stable internal category code.",
    )

    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Human-readable category name.",
    )

    quick_name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Short label for POS presentation.",
    )

    show_in_pos: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        default=True,
        doc="Whether this category is visible in POS bootstrap.",
    )

    default_pos_order: Mapped[int] = mapped_column(
        nullable=False,
        server_default=text("100"),
        default=100,
        doc="Default backend-provided ordering hint for POS presentation.",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        default=True,
        doc="Soft-delete flag for operational visibility.",
    )

    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()

    products: Mapped[list["Product"]] = relationship(back_populates="category")
