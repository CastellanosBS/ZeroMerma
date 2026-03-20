# apps/backend/src/zeromerma_api/schemas/pos_cash_session.py
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class CashSessionOpenRequest(BaseModel):
    """
    Request payload to open a cash session.

    Security model:
    - The authenticated user becomes the opener (opened_by_id is derived from the token).
    - The client must NOT provide opened_by_id.
    """

    branch_id: int = Field(ge=1)
    opening_amount: Decimal = Field(ge=Decimal("0"))


class CashSessionCloseRequest(BaseModel):
    """
    Request payload to close a cash session.

    Security model:
    - The authenticated user becomes the closer (closed_by_id is derived from the token).
    - The client must NOT provide closed_by_id.
    """

    closing_amount: Decimal = Field(ge=Decimal("0"))
