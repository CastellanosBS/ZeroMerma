from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from zeromerma_api.modules.operations.application.schemas import (
    OperationDocumentView,
    OperationHistoryFilterOptionView,
    OperationHistoryListItemView,
    OperationHistoryScopeView,
)


class TransferDispatchCommitLineRequest(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=Decimal("0"), max_digits=12, decimal_places=3)
    notes: str | None = Field(default=None, max_length=500)


class TransferDispatchCommitRequest(BaseModel):
    workstation_code: str = Field(min_length=1, max_length=64)
    destination_branch_id: UUID
    lines: list[TransferDispatchCommitLineRequest] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=1000)


class TransferReceiptLineRequest(BaseModel):
    shipment_line_id: UUID
    expected_quantity: Decimal = Field(gt=Decimal("0"), max_digits=12, decimal_places=3)
    received_quantity: Decimal = Field(ge=Decimal("0"), max_digits=12, decimal_places=3)
    variance_reason: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)


class TransferReceiveRequest(BaseModel):
    workstation_code: str = Field(min_length=1, max_length=64)
    lines: list[TransferReceiptLineRequest] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=1000)


class PendingInboundTransferView(BaseModel):
    id: UUID
    folio: str
    source_branch_id: UUID
    source_branch_code: str
    source_branch_name: str
    destination_branch_id: UUID
    destination_branch_code: str
    destination_branch_name: str
    workstation_id: UUID
    workstation_code: str
    workstation_name: str
    status: str
    created_at_utc: datetime
    committed_at_utc: datetime | None
    line_count: int
    expected_total_quantity: Decimal


class TransferQuantitySummaryView(BaseModel):
    line_count: int
    expected_total_quantity: Decimal
    received_total_quantity: Decimal | None
    has_variance: bool
    variance_line_count: int


class TransferDocumentSummaryView(BaseModel):
    document_id: UUID
    folio: str
    status: str
    committed_at_utc: datetime | None
    linked_shipment_id: UUID | None
    quantity_summary: TransferQuantitySummaryView


class PendingInboundTransfersResponse(BaseModel):
    workstation_code: str
    transfers: list[PendingInboundTransferView]


class TransferDispatchHistoryResponse(BaseModel):
    workstation_code: str
    scope: str
    created_by_user_id: str | None = None
    destination_branch_id: str | None = None
    available_scopes: list[OperationHistoryScopeView]
    available_users: list[OperationHistoryFilterOptionView]
    available_destination_branches: list[OperationHistoryFilterOptionView]
    records: list[OperationHistoryListItemView]


class TransferReceiptHistoryResponse(BaseModel):
    workstation_code: str
    scope: str
    created_by_user_id: str | None = None
    source_branch_id: str | None = None
    status: str | None = None
    available_scopes: list[OperationHistoryScopeView]
    available_users: list[OperationHistoryFilterOptionView]
    available_source_branches: list[OperationHistoryFilterOptionView]
    available_statuses: list[OperationHistoryFilterOptionView]
    records: list[OperationHistoryListItemView]


class TransferDetailResponse(BaseModel):
    shipment: OperationDocumentView
    shipment_summary: TransferDocumentSummaryView
    receipt: OperationDocumentView | None
    receipt_summary: TransferDocumentSummaryView | None
