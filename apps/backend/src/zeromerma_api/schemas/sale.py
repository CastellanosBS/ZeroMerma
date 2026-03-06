# apps/backend/src/zeromerma_api/schemas/sale.py
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


class SaleCreate(BaseModel):
    branch_id: int = Field(..., ge=1)
    cash_session_id: int = Field(..., ge=1)
    created_by_id: int = Field(..., ge=1)
    items: List[SaleItemCreate]


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
