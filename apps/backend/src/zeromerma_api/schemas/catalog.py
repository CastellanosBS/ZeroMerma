# apps/backend/src/zeromerma_api/schemas/catalog.py
# PURPOSE:
#   Pydantic schemas for the Catalog module (ProductCategory + Product v2).
#
# PRODUCT v2 FIELDS:
#   - uom: unit of measure (PCS/KG/G/L/ML)
#   - is_input: True for ingredients/raw materials; False for finished/sellable goods
#   - sale_price: optional catalog-level selling price (used later for pricing policy)
#   - standard_cost: optional catalog-level standard cost (used later for costing)
#
# API DESIGN GOALS:
#   - Backward compatible: existing clients can omit new fields.
#   - Strict-enough validation to keep the catalog clean.
#   - Response models include convenience fields (category_name).

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# ProductCategory schemas
# ---------------------------------------------------------------------------


class CategoryBase(BaseModel):
    """
    Shared fields for ProductCategory.
    """

    model_config = ConfigDict(extra="ignore")

    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=120)
    is_active: bool = True


class CategoryCreate(CategoryBase):
    """
    Payload to create a category.
    """

    pass


class CategoryUpdate(BaseModel):
    """
    Payload to update a category.

    All fields optional to support partial updates via PUT.
    """

    model_config = ConfigDict(extra="ignore")

    code: Optional[str] = Field(default=None, min_length=1, max_length=32)
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    is_active: Optional[bool] = None


class CategoryOut(CategoryBase):
    """
    Category returned by the API.
    """

    id: int


# ---------------------------------------------------------------------------
# Product schemas
# ---------------------------------------------------------------------------


class ProductBase(BaseModel):
    """
    Shared fields for Product v2.

    NOTE:
    - category_id is required in v2 because we want every product to belong to a category.
    - uom/is_input have safe defaults (aligned with DB server defaults).
    """

    model_config = ConfigDict(extra="ignore")

    sku: Optional[str] = Field(default=None, min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    category_id: int = Field(ge=1)

    # v2 fields
    uom: str = Field(default="PCS", min_length=1, max_length=16)
    is_input: bool = Field(default=False)

    # optional catalog economics
    sale_price: Optional[Decimal] = Field(default=None, ge=0)
    standard_cost: Optional[Decimal] = Field(default=None, ge=0)

    is_active: bool = True


class ProductCreate(ProductBase):
    """
    Payload to create a product.
    """

    pass


class ProductUpdate(BaseModel):
    """
    Payload to update an existing product (partial fields).
    """

    model_config = ConfigDict(extra="ignore")

    sku: Optional[str] = Field(default=None, min_length=1, max_length=64)
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    category_id: Optional[int] = Field(default=None, ge=1)

    uom: Optional[str] = Field(default=None, min_length=1, max_length=16)
    is_input: Optional[bool] = None

    sale_price: Optional[Decimal] = Field(default=None, ge=0)
    standard_cost: Optional[Decimal] = Field(default=None, ge=0)

    is_active: Optional[bool] = None


class ProductOut(ProductBase):
    """
    Product returned by the API.
    """

    id: int
    category_name: Optional[str] = None
