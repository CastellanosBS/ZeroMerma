from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from zeromerma_api.modules.hardware.domain.commands import SignedDeviceCommand
from zeromerma_api.modules.tickets.application.print_requests import ReceiptKind


class HardwareCommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workstation_code: str = Field(min_length=1, max_length=64)
    binding_id: UUID
    kind: Literal["PRINT", "OPEN_DRAWER"]
    receipt_source_kind: ReceiptKind | None = None
    receipt_source_id: UUID | None = None
    cash_entry_id: UUID | None = None

    @model_validator(mode="after")
    def require_cause(self) -> "HardwareCommandRequest":
        if self.kind == "PRINT":
            if (
                self.receipt_source_kind is None
                or self.receipt_source_id is None
                or self.cash_entry_id is not None
            ):
                raise ValueError("Printing requires an immutable receipt and cannot open a drawer.")
        elif (
            self.cash_entry_id is None
            or self.receipt_source_kind is not None
            or self.receipt_source_id is not None
        ):
            raise ValueError("Drawer opening requires a confirmed cash cause.")
        return self


class HardwareBindingView(BaseModel):
    id: UUID
    kind: Literal["PRINTER", "DRAWER"]
    enabled: bool
    support_status: Literal["PENDING_VALIDATION", "REGISTERED"]


class HardwareBootstrapView(BaseModel):
    workstation_id: UUID
    branch_id: UUID
    devices: list[HardwareBindingView]
    browser_print_fallback: Literal["UNCERTIFIED"] = "UNCERTIFIED"
    manual_drawer_opening_enabled: Literal[False] = False
    blockers: list[str]


class HardwareCommandAcknowledgement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_id: UUID
    grant: SignedDeviceCommand
    physical_outcome: Literal["NOT_CONFIRMED"] = "NOT_CONFIRMED"
