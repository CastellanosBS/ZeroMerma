# apps/backend/src/zeromerma_api/schemas/payment.py
# PURPOSE: Pydantic schemas for payments API.

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    """
    Client submits method + amount (+ optional reference).
    We do NOT accept sale_id in body because it is in the URL path.
    """

    method: str = Field(..., min_length=1, max_length=16)
    amount: float = Field(..., gt=0)
    reference: Optional[str] = Field(None, max_length=64)


class PaymentOut(BaseModel):
    """
    API representation of a payment record.
    """

    id: int
    sale_id: int
    method: str
    amount: float
    reference: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True
