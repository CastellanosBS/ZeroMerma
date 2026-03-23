# apps/backend/src/zeromerma_api/schemas/pricing.py
# PURPOSE:
#   API contracts for Pricing Policy (Phase 6.4).
#
# POLICY:
#   - Base price: product.sale_price
#   - Branch override: product_price.price for (branch_id, product_id)
#   - Effective price: COALESCE(override_price, base_price)
#
# DESIGN GOALS:
#   - Backward compatible with existing POS behavior (client can still send unit_price).
#   - Admin-only write operations for overrides.
#   - Read operations available to CASHIER/ADMIN.

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PriceOverrideUpsert(BaseModel):
    """
    Create or update a branch/product price override.
    """

    model_config = ConfigDict(extra="forbid")

    price: Decimal = Field(ge=0)
    currency: str = Field(default="MXN", min_length=3, max_length=3)


class PriceOverrideOut(BaseModel):
    """
    Representation of a stored override row.
    """

    model_config = ConfigDict(extra="ignore")

    id: int
    branch_id: int
    product_id: int
    price: Decimal
    currency: str


class EffectivePriceRow(BaseModel):
    """
    Effective price view for a product at a given branch.
    """

    model_config = ConfigDict(extra="ignore")

    branch_id: int
    product_id: int
    sku: Optional[str] = None
    name: str

    category_id: int
    category_name: Optional[str] = None

    is_input: bool
    uom: str

    base_price: Optional[Decimal] = None
    override_price: Optional[Decimal] = None
    currency: str

    effective_price: Optional[Decimal] = None
