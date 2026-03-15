# apps/backend/src/zeromerma_api/schemas/cash_session.py
# PURPOSE: Pydantic schemas for cash session endpoints.
#
# SECURITY MODEL:
# - Actor identifiers are NOT accepted from clients:
#     * opened_by_id is derived from the authenticated user (JWT).
#     * closed_by_id is derived from the authenticated user (JWT).
# - We forbid unknown fields on request payloads to prevent impersonation attempts
#   or stale clients sending deprecated fields.

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CashSessionOut(BaseModel):
    """
    API representation of a cash session.
    Response models remain stable and explicit.
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

    Security:
    - opened_by_id is derived from the authenticated user (JWT).
    - Clients must not send opened_by_id.
    """

    branch_id: int = Field(..., ge=1)
    opening_amount: float = Field(..., ge=0)

    model_config = ConfigDict(extra="forbid")


class CashSessionCloseIn(BaseModel):
    """
    Request body for closing a cash session.

    Security:
    - closed_by_id is derived from the authenticated user (JWT).
    - Clients must not send closed_by_id.
    """

    closing_amount: float = Field(..., ge=0)

    model_config = ConfigDict(extra="forbid")
