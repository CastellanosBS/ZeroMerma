from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TerminalOperationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    financial_entry_id: UUID
    terminal_binding_id: UUID
    original_operation_id: UUID | None = None


class TerminalOperationAcknowledgement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    financial_entry_id: UUID
    status: Literal["CREATED"] = "CREATED"


class TerminalOperationView(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    id: UUID
    financial_entry_id: UUID
    branch_id: UUID
    workstation_id: UUID
    cash_session_id: UUID
    terminal_binding_id: UUID
    operation_type: Literal["CAPTURE", "REFUND"]
    status: Literal[
        "CREATED",
        "PROCESSING",
        "AUTHORIZED",
        "UNKNOWN",
        "CAPTURED",
        "REFUNDED",
        "DECLINED",
        "FAILED",
    ]
    reconciliation_status: Literal["PENDING", "MATCHED", "DISCREPANCY"]
    amount: Decimal
    currency_code: Literal["MXN"]
    provider_code: str
    environment: Literal["SANDBOX", "PRODUCTION"]
    created_at: datetime
    updated_at: datetime


class TerminalBootstrapView(BaseModel):
    provider_code: Literal["BBVA"] = "BBVA"
    integrated_payments_enabled: bool
    accounting_only_available: Literal[True] = True
    manual_fallback_enabled: Literal[False] = False
    final_pilot_start: Literal["POSTPONED", "EXTERNAL_GATE_REQUIRED"] = "POSTPONED"
    blockers: list[str]
