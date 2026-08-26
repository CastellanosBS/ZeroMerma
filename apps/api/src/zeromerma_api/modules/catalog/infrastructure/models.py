from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from zeromerma_api.db.base import Base
from zeromerma_api.modules.catalog.domain.constants import (
    CATALOG_CAPTURE_MODE_CLASS_CAPTURE,
    CATALOG_PRODUCT_KIND_FINISHED_GOOD,
    CATALOG_USAGE_TYPE_OTHER,
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class ProductClass(Base):
    __tablename__ = "product_classes"
    __table_args__ = (
        CheckConstraint(
            "capture_mode_default IN ('CLASS_CAPTURE', 'PRODUCT_DIRECT')",
            name="ck_product_classes_capture_mode_valid",
        ),
        CheckConstraint(
            "class_capture_unit_price IS NULL OR class_capture_unit_price >= 0",
            name="ck_product_classes_class_capture_unit_price_non_negative",
        ),
        CheckConstraint(
            "("
            "(capture_mode_default = 'CLASS_CAPTURE' AND class_capture_unit_price IS NOT NULL)"
            " OR "
            "(capture_mode_default = 'PRODUCT_DIRECT' AND class_capture_unit_price IS NULL)"
            ")",
            name="ck_product_classes_capture_mode_price_shape",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    quick_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    search_aliases: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    capture_mode_default: Mapped[str] = mapped_column(
        String(32),
        default=CATALOG_CAPTURE_MODE_CLASS_CAPTURE,
        nullable=False,
    )
    class_capture_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency_code: Mapped[str] = mapped_column(String(3), default="MXN", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_sellable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("unit_price >= 0", name="ck_products_unit_price_non_negative"),
        CheckConstraint(
            "standard_cost IS NULL OR standard_cost >= 0",
            name="ck_products_standard_cost_non_negative",
        ),
        CheckConstraint(
            "product_kind IN ('FINISHED_GOOD', 'RAW_MATERIAL', 'CONSUMABLE', 'DISPOSABLE')",
            name="ck_products_product_kind_valid",
        ),
        CheckConstraint(
            "usage_type IS NULL OR usage_type IN ("
            "'RECIPE_INPUT', "
            "'PRODUCTION_SUPPLY', "
            "'PACKAGING', "
            "'CLEANING_SANITATION', "
            "'OPERATIONAL_SUPPLY', "
            "'OTHER'"
            ")",
            name="ck_products_usage_type_valid",
        ),
        CheckConstraint(
            "purchase_conversion_factor IS NULL OR purchase_conversion_factor > 0",
            name="ck_products_purchase_conversion_positive",
        ),
        CheckConstraint(
            "minimum_stock IS NULL OR minimum_stock >= 0",
            name="ck_products_minimum_stock_non_negative",
        ),
        CheckConstraint(
            "reorder_point IS NULL OR reorder_point >= 0",
            name="ck_products_reorder_point_non_negative",
        ),
        CheckConstraint(
            "preferred_order_quantity IS NULL OR preferred_order_quantity >= 0",
            name="ck_products_preferred_order_qty_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_classes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    quick_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    search_aliases: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    product_kind: Mapped[str] = mapped_column(
        String(32),
        default=CATALOG_PRODUCT_KIND_FINISHED_GOOD,
        nullable=False,
    )
    unit_of_measure: Mapped[str] = mapped_column(String(32), default="piece", nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    standard_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    currency_code: Mapped[str] = mapped_column(String(3), default="MXN", nullable=False)
    is_inventory_tracked: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_purchasable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    purchase_unit_of_measure: Mapped[str | None] = mapped_column(String(32), nullable=True)
    purchase_conversion_factor: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6),
        nullable=True,
    )
    usage_type: Mapped[str | None] = mapped_column(
        String(40),
        default=CATALOG_USAGE_TYPE_OTHER,
        nullable=True,
    )
    minimum_stock: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    reorder_point: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    preferred_order_quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    procurement_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_sellable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = (CheckConstraint("yield_qty > 0", name="ck_recipes_yield_qty_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    yield_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    yield_uom: Mapped[str] = mapped_column(String(32), default="piece", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class RecipeInput(Base):
    __tablename__ = "recipe_inputs"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_recipe_inputs_quantity_positive"),
        UniqueConstraint("recipe_id", "input_product_id", name="uq_recipe_inputs_recipe_product"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
    )
    input_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
