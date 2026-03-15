# apps/backend/src/zeromerma_api/schemas/sale.py
# PURPOSE: Pydantic schemas for POS sales.
#
# SECURITY MODEL:
# - created_by_id is NOT accepted from clients.
# - created_by_id is derived from the authenticated user (JWT).
# - We forbid unknown fields on request payloads to prevent impersonation attempts.

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field

from zeromerma_api.schemas.payment import PaymentOut


class SaleItemCreate(BaseModel):
    """
    MVP: client provides unit_price (POS price source for now).
    Backend computes line_total and totals.
    """

    product_id: int = Field(..., ge=1)
    qty: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)

    model_config = ConfigDict(extra="forbid")


class SaleCreate(BaseModel):
    """
    Request body for creating a sale.

    Security:
    - created_by_id is derived from the authenticated user (JWT).
    - Clients must not send created_by_id.
    """

    branch_id: int = Field(..., ge=1)
    cash_session_id: int = Field(..., ge=1)
    items: List[SaleItemCreate]

    model_config = ConfigDict(extra="forbid")


class SaleItemOut(BaseModel):
    id: int
    product_id: int
    qty: float
    unit_price: float
    line_total: float

    model_config = ConfigDict(from_attributes=True)


class SaleOut(BaseModel):
    id: int
    branch_id: int
    cash_session_id: int
    created_by_id: int
    subtotal: float
    tax: float
    total: float
    status: str
    items: List[SaleItemOut]

    model_config = ConfigDict(from_attributes=True)


class SaleDetailOut(SaleOut):
    """
    Extends SaleOut with payments and computed balance information.
    """

    payments: List[PaymentOut]
    paid_amount: float
    balance_due: float
