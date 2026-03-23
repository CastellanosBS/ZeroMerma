# apps/backend/src/zeromerma_api/schemas/catalog.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from .common import (
    NonNegativeMoney,
    ORMReadSchema,
    PatchInputSchema,
    StrictInputSchema,
)

UomLiteral = Literal["PCS", "KG", "G", "L", "ML"]


# ---------------------------------------------------------------------------
# Category schemas
# ---------------------------------------------------------------------------


class CategoryCreate(StrictInputSchema):
    """
    Payload to create a product category.
    """

    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=120)
    is_active: bool = True


class CategoryUpdate(PatchInputSchema):
    """
    Partial update payload for a product category.
    """

    code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_active: bool | None = None


class CategoryOut(ORMReadSchema):
    """
    Category returned by the API.
    """

    id: int
    code: str
    name: str
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Product schemas
# ---------------------------------------------------------------------------


class ProductCreate(StrictInputSchema):
    """
    Payload to create a product.

    Notes:
    - category_id is required at the API level even if the DB remains temporarily
      backward-compatible.
    - is_input distinguishes ingredients/raw materials from sellable products.
    """

    sku: str | None = Field(default=None, min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=200)
    category_id: int = Field(ge=1)

    uom: UomLiteral = "PCS"
    is_input: bool = False

    sale_price: NonNegativeMoney | None = None
    standard_cost: NonNegativeMoney | None = None

    is_active: bool = True


class ProductUpdate(PatchInputSchema):
    """
    Partial update payload for a product.
    """

    sku: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category_id: int | None = Field(default=None, ge=1)

    uom: UomLiteral | None = None
    is_input: bool | None = None

    sale_price: NonNegativeMoney | None = None
    standard_cost: NonNegativeMoney | None = None

    is_active: bool | None = None


class ProductOut(ORMReadSchema):
    """
    Product returned by the API.
    """

    id: int
    sku: str | None = None
    name: str

    category_id: int | None = None
    category_name: str | None = None

    uom: UomLiteral | str
    is_input: bool

    sale_price: Decimal | None = None
    standard_cost: Decimal | None = None

    is_active: bool

    created_at: datetime | None = None
    updated_at: datetime | None = None
