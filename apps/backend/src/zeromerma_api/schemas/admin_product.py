from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

UomLiteral = Literal["PCS", "KG", "G", "L", "ML"]


class AdminProductCategoryRef(BaseModel):
    id: int
    code: str
    name: str
    quick_name: str | None = None
    is_active: bool

    model_config = ConfigDict(extra="forbid")


class AdminProductOut(BaseModel):
    id: int
    sku: str | None = None
    name: str
    quick_name: str | None = None
    category_id: int | None = None
    uom: UomLiteral
    is_input: bool
    show_in_pos: bool
    is_sellable_in_pos: bool
    default_pos_order: int
    sale_price: Decimal | None = None
    standard_cost: Decimal | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    category: AdminProductCategoryRef | None = None

    model_config = ConfigDict(extra="forbid")


class AdminProductCreateIn(BaseModel):
    sku: str | None = Field(default=None, max_length=32)
    name: str = Field(min_length=1, max_length=255)
    quick_name: str | None = Field(default=None, max_length=100)
    category_id: int = Field(ge=1)
    uom: UomLiteral = "PCS"
    is_input: bool = False
    show_in_pos: bool = True
    is_sellable_in_pos: bool = True
    default_pos_order: int = Field(default=100, ge=0)
    sale_price: Decimal | None = Field(default=None, ge=0)
    standard_cost: Decimal | None = Field(default=None, ge=0)
    is_active: bool = True

    model_config = ConfigDict(extra="forbid")


class AdminProductUpdateIn(BaseModel):
    sku: str | None = Field(default=None, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    quick_name: str | None = Field(default=None, max_length=100)
    category_id: int | None = Field(default=None, ge=1)
    uom: UomLiteral | None = None
    is_input: bool | None = None
    show_in_pos: bool | None = None
    is_sellable_in_pos: bool | None = None
    default_pos_order: int | None = Field(default=None, ge=0)
    sale_price: Decimal | None = Field(default=None, ge=0)
    standard_cost: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")
