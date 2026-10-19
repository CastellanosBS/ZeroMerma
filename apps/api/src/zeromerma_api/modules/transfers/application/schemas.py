from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from zeromerma_api.modules.operations.application.schemas import (
    OperationDocumentView,
    OperationHistoryFilterOptionView,
    OperationHistoryListItemView,
    OperationHistoryScopeView,
)


class TransferDispatchCommitLineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: UUID
    quantity: Decimal = Field(gt=Decimal("0"), max_digits=12, decimal_places=3)
    notes: str | None = Field(default=None, max_length=500)


class TransferDispatchCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workstation_code: str = Field(min_length=1, max_length=64)
    cash_session_id: UUID
    destination_branch_id: UUID
    lines: list[TransferDispatchCommitLineRequest] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def unique_products(self) -> TransferDispatchCommitRequest:
        if len({line.product_id for line in self.lines}) != len(self.lines):
            raise ValueError("Transfer products must be unique.")
        return self


class TransferLotAllocationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lot_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)


class TransferLotProgressView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lot_id: UUID
    lot_code: str
    expires_at: datetime | None
    sent_quantity: Decimal
    received_quantity: Decimal
    returned_quantity: Decimal
    waste_quantity: Decimal
    pending_quantity: Decimal


class TransferLotQuantityView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lot_id: UUID
    lot_code: str
    expires_at: datetime | None
    quantity: Decimal


class TransferReceiptLineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    shipment_line_id: UUID
    expected_quantity: Decimal = Field(gt=Decimal("0"), max_digits=12, decimal_places=3)
    received_quantity: Decimal = Field(ge=Decimal("0"), max_digits=12, decimal_places=3)
    variance_reason: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)
    lot_allocations: list[TransferLotAllocationRequest] | None = None


class TransferReceiveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workstation_code: str = Field(min_length=1, max_length=64)
    cash_session_id: UUID
    lines: list[TransferReceiptLineRequest] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def unique_lines(self) -> TransferReceiveRequest:
        if len({line.shipment_line_id for line in self.lines}) != len(self.lines):
            raise ValueError("Receipt lines must be unique.")
        return self


TransferResolutionKind = Literal["RETURN_TO_ORIGIN", "SEND_TO_WASTE"]


class TransferResolutionLineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    shipment_line_id: UUID
    quantity: Decimal = Field(gt=Decimal("0"), max_digits=12, decimal_places=3)
    lot_allocations: list[TransferLotAllocationRequest] | None = None


class AdminTransferResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: TransferResolutionKind
    destination_location: Literal["BACKROOM", "QUARANTINE"] = "QUARANTINE"
    reason: str = Field(min_length=1, max_length=500)
    lines: list[TransferResolutionLineRequest] = Field(min_length=1)

    @field_validator("reason")
    @classmethod
    def required_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A physical resolution requires a reason.")
        return value.strip()

    @model_validator(mode="after")
    def unique_lines(self) -> AdminTransferResolveRequest:
        if len({line.shipment_line_id for line in self.lines}) != len(self.lines):
            raise ValueError("Resolution lines must be unique.")
        return self


class TransferResolveRequest(AdminTransferResolveRequest):
    workstation_code: str = Field(min_length=1, max_length=64)
    cash_session_id: UUID


class TransferResolutionLineView(BaseModel):
    shipment_line_id: UUID
    product_id: UUID
    quantity: Decimal
    unit_of_measure: str
    lots: list[TransferLotQuantityView] = Field(default_factory=list)


class TransferResolutionView(BaseModel):
    id: UUID
    kind: TransferResolutionKind
    destination_location: str
    branch_id: UUID
    reason: str
    actor_id: UUID
    occurred_at: datetime
    lines: list[TransferResolutionLineView]


TransferCommandCode = Literal[
    "create", "update", "dispatch", "receive", "cancel", "resolve_return", "resolve_waste"
]
PosTransferCommandCode = Literal["dispatch", "receive", "resolve_return", "resolve_waste"]


class TransferCommandLineView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shipment_line_id: UUID
    product_id: UUID
    sent_quantity: Decimal
    received_quantity: Decimal
    returned_quantity: Decimal = Decimal("0")
    waste_quantity: Decimal = Decimal("0")
    pending_quantity: Decimal
    lots: list[TransferLotProgressView] = Field(default_factory=list)


class TransferCommandResultView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    folio: str
    status: str
    origin_branch_id: UUID
    destination_branch_id: UUID
    receipt_id: UUID | None
    resolution_id: UUID | None = None
    cash_session_id: UUID | None
    committed_at_utc: datetime | None
    lines: list[TransferCommandLineView]


class PendingInboundTransferView(BaseModel):
    id: UUID
    folio: str
    source_branch_id: UUID
    source_branch_code: str
    source_branch_name: str
    destination_branch_id: UUID
    destination_branch_code: str
    destination_branch_name: str
    workstation_id: UUID | None
    workstation_code: str | None
    workstation_name: str | None
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


class TransferReceiptHistoryItemView(OperationHistoryListItemView):
    shipment_id: UUID


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
    records: list[TransferReceiptHistoryItemView]


class TransferDetailResponse(BaseModel):
    shipment: OperationDocumentView
    shipment_summary: TransferDocumentSummaryView
    receipts: list[OperationDocumentView]
    receipt_summaries: list[TransferDocumentSummaryView]
    receipt_progress: list[TransferCommandLineView]
    resolutions: list[TransferResolutionView] = Field(default_factory=list)
