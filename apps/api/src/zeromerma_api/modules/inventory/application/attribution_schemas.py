from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ClassAttributionLineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sale_line_id: UUID
    product_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    lot_id: UUID | None = None


class ClassAttributionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workstation_code: str = Field(min_length=1, max_length=64)
    cash_session_id: UUID
    lines: list[ClassAttributionLineRequest] = Field(min_length=1, max_length=200)


class ClassAttributionResultLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attribution_id: UUID
    sale_line_id: UUID
    product_id: UUID
    quantity: Decimal
    remaining_quantity: Decimal
    inventory_movement_id: UUID | None


class ClassAttributionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sale_id: UUID
    operation_id: UUID
    lines: list[ClassAttributionResultLine]
