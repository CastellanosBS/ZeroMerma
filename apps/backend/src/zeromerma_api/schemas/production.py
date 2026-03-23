# apps/backend/src/zeromerma_api/schemas/production.py
from __future__ import annotations

from pydantic import Field

from .common import ORMReadSchema, PositiveQuantity, StrictInputSchema


class ProductionLine(StrictInputSchema):
    """
    One input/output line in a production run.
    """

    product_id: int = Field(ge=1)
    qty: PositiveQuantity


class ProductionRunCreate(StrictInputSchema):
    """
    Create a production run.

    Security:
    - created_by_id is derived from the authenticated user, not from the payload.
    """

    branch_id: int = Field(ge=1)
    note: str | None = Field(default=None, max_length=500)

    inputs: list[ProductionLine] = Field(min_length=1)
    outputs: list[ProductionLine] = Field(min_length=1)


class ProductionRunOut(ORMReadSchema):
    """
    Response payload for production run creation.
    """

    id: int
    branch_id: int
    created_by_id: int
    inputs_count: int
    outputs_count: int
