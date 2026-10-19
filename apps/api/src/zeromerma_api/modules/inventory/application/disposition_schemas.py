from __future__ import annotations

from decimal import Decimal
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InventoryDispositionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    branch_id: UUID
    product_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    kind: Literal["RETURN_CORRECTION", "QUARANTINE_RELEASE"]
    destination: Literal["BACKROOM", "COUNTER", "QUARANTINE", "WASTE"]
    return_allocation_id: UUID | None = None
    lot_id: UUID | None = None
    inspection_passed: bool = False
    reason: str = Field(min_length=3, max_length=160)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_cause(self) -> Self:
        if not self.reason.strip():
            raise ValueError("A physical disposition requires a reason.")
        if self.kind == "RETURN_CORRECTION":
            if self.return_allocation_id is None or self.destination not in {"QUARANTINE", "WASTE"}:
                raise ValueError(
                    "Return corrections need an original allocation and a safe destination."
                )
            if self.lot_id is not None:
                raise ValueError("Return corrections retain the original allocation's lot.")
        elif self.return_allocation_id is not None or self.destination == "QUARANTINE":
            raise ValueError("Quarantine disposition requires a different physical destination.")
        elif self.destination != "WASTE" and not self.inspection_passed:
            raise ValueError("Releasing stock requires an explicit successful inspection.")
        return self


class InventoryDispositionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_id: UUID
    branch_id: UUID
    product_id: UUID
    kind: Literal["RETURN_CORRECTION", "QUARANTINE_RELEASE"]
    source: str
    destination: str
    quantity: Decimal
    return_allocation_id: UUID | None
    lot_id: UUID | None
    movement_ids: list[UUID]
