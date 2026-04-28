from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from zeromerma_api.modules.branches.application.schemas import BranchSummary, WorkstationSummary
from zeromerma_api.modules.cash.application.schemas import CashSessionView
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser


class TicketScopeView(BaseModel):
    code: str
    label: str


class TicketsBootstrapResponse(BaseModel):
    user: AuthenticatedUser
    branch: BranchSummary
    workstation: WorkstationSummary
    local_timestamp: datetime
    current_open_cash_session: CashSessionView | None = None
    branch_brand_key: str
    ticket_lookup_allowed: bool
    default_scope: str
    available_scopes: list[TicketScopeView]


class TicketPaymentSummaryView(BaseModel):
    payment_method_code: str
    amount: Decimal
    currency_code: str


class TicketListItemView(BaseModel):
    id: UUID
    folio: str
    confirmed_at: datetime
    total_amount: Decimal
    currency_code: str
    change_amount: Decimal
    operator_full_name: str
    item_count: int
    total_quantity: Decimal
    return_count: int
    returned_amount: Decimal
    return_status: str
    has_returnable_quantity: bool
    payment_summary: list[TicketPaymentSummaryView]


class TicketsListResponse(BaseModel):
    workstation_code: str
    scope: str
    query: str | None = None
    tickets: list[TicketListItemView]


class TicketOperatorSummaryView(BaseModel):
    id: UUID
    email: str
    full_name: str


class TicketLineItemView(BaseModel):
    id: UUID
    sequence: int
    name: str
    quantity: Decimal
    unit_price: Decimal
    line_total_amount: Decimal


class TicketPaymentDetailView(BaseModel):
    id: UUID
    sequence: int
    payment_method_code: str
    tendered_amount: Decimal
    applied_amount: Decimal
    change_amount: Decimal
    currency_code: str
    received_at: datetime


class TicketDetailResponse(BaseModel):
    id: UUID
    folio: str
    status: str
    confirmed_at: datetime
    branch: BranchSummary
    workstation: WorkstationSummary
    operator: TicketOperatorSummaryView
    cash_session_id: UUID
    currency_code: str
    item_count: int
    total_quantity: Decimal
    subtotal_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    change_amount: Decimal
    return_count: int
    returned_amount: Decimal
    return_status: str
    has_returnable_quantity: bool
    lines: list[TicketLineItemView]
    payments: list[TicketPaymentDetailView]
    can_reprint: bool = True


class TicketReprintRequest(BaseModel):
    workstation_code: str = Field(min_length=1, max_length=64)
