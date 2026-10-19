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


class TicketAttributionOptionView(BaseModel):
    product_id: UUID
    product_code: str
    product_name: str
    lot_id: UUID | None
    lot_code: str | None
    expires_at: datetime | None
    available_quantity: Decimal | None
    is_inventory_tracked: bool
    lot_tracking_enabled: bool


class TicketPhysicalAttributionView(BaseModel):
    id: UUID
    product_id: UUID
    quantity: Decimal
    inventory_movement_id: UUID | None
    occurred_at: datetime


class TicketLineItemView(BaseModel):
    id: UUID
    sequence: int
    name: str
    quantity: Decimal
    unit_price: Decimal
    line_total_amount: Decimal
    capture_mode: str
    remaining_attribution_quantity: Decimal
    attribution_options: list[TicketAttributionOptionView]
    physical_attributions: list[TicketPhysicalAttributionView]


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
