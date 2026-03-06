# apps/backend/src/zeromerma_api/schemas/cash_session.py
# PURPOSE: Pydantic schemas for cash session endpoints.

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CashSessionOut(BaseModel):
    """
    API representation of a cash session.
    We keep fields explicit; clients depend on this stability.
    """

    id: int
    branch_id: int
    opened_by_id: int
    closed_by_id: Optional[int]
    opened_at: datetime
    closed_at: Optional[datetime]
    opening_amount: float
    closing_amount: Optional[float]
    status: str

    model_config = ConfigDict(from_attributes=True)


class CashSessionOpenIn(BaseModel):
    """
    Request body for opening a cash session.
    """

    branch_id: int = Field(..., ge=1)
    opened_by_id: int = Field(..., ge=1)
    opening_amount: float = Field(..., ge=0)


class CashSessionCloseIn(BaseModel):
    """
    Request body for closing a cash session.
    """

    closed_by_id: int = Field(..., ge=1)
    closing_amount: float = Field(..., ge=0)
