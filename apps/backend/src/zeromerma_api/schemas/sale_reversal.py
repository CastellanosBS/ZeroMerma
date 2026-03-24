from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field, field_validator

from .common import ORMReadSchema, StrictInputSchema

SaleReversalKind = Literal["VOID", "REFUND"]


class SaleVoidIn(StrictInputSchema):
    """
    Void one OPEN unpaid sale.
    """

    reason: str = Field(min_length=5, max_length=500)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("reason must not be blank.")
        return normalized


class SaleRefundIn(StrictInputSchema):
    """
    Fully refund one PAID sale.

    This block implements only full refunds. Partial refunds are intentionally
    deferred to a later block to keep accounting and inventory semantics clean.
    """

    reason: str = Field(min_length=5, max_length=500)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("reason must not be blank.")
        return normalized


class SaleReversalOut(ORMReadSchema):
    """
    Canonical response for sale void/refund actions.
    """

    sale_id: int
    status: str
    reversal_kind: SaleReversalKind | str

    branch_id: int
    cash_session_id: int

    voided_at: datetime | None = None
    voided_by_id: int | None = None

    refunded_at: datetime | None = None
    refunded_by_id: int | None = None

    reversal_reason: str
    total: Decimal
    reversal_snapshot: dict[str, Any]
