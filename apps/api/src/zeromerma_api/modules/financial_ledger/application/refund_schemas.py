"""Public projections distinguish refund obligations from money actually returned."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FinancialRefundEntryView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    payment_method_code: str
    execution_mode: str
    state: str
    amount: Decimal
    cash_session_id: UUID | None
    occurred_at: datetime


class FinancialRefundView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    financial_operation_id: UUID
    source_type: str
    source_id: UUID
    amount_due: Decimal
    amount_settled: Decimal
    amount_pending: Decimal
    state: str
    cash_settled_amount: Decimal
    card_settled_amount: Decimal
    original_collection_operation_ids: list[UUID]
    entries: list[FinancialRefundEntryView]


class RefundSettlementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workstation_code: str = Field(min_length=1, max_length=64)
    cash_session_id: UUID


class RefundSettlementCommand(RefundSettlementRequest):
    source_id: UUID
