# apps/backend/src/zeromerma_api/schemas/common.py
from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class StrictInputSchema(BaseModel):
    """
    Canonical base class for request payloads.

    Rules:
    - Reject unknown fields to keep contracts explicit and auditable.
    - Strip surrounding whitespace from strings where applicable.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class PatchInputSchema(BaseModel):
    """
    Canonical base class for PATCH/partial-update payloads.
    Same strictness as StrictInputSchema, but semantically reserved for partial updates.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class ORMReadSchema(BaseModel):
    """
    Canonical base class for response models built from ORM objects or row-like objects.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )


Money = Annotated[
    Decimal,
    Field(max_digits=18, decimal_places=2),
]

NonNegativeMoney = Annotated[
    Decimal,
    Field(ge=Decimal("0"), max_digits=18, decimal_places=2),
]

PositiveMoney = Annotated[
    Decimal,
    Field(gt=Decimal("0"), max_digits=18, decimal_places=2),
]

Quantity = Annotated[
    Decimal,
    Field(max_digits=18, decimal_places=3),
]

NonNegativeQuantity = Annotated[
    Decimal,
    Field(ge=Decimal("0"), max_digits=18, decimal_places=3),
]

PositiveQuantity = Annotated[
    Decimal,
    Field(gt=Decimal("0"), max_digits=18, decimal_places=3),
]
