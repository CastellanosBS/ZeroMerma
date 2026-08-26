from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from zeromerma_api.modules.branches.application.schemas import BranchSummary, WorkstationSummary
from zeromerma_api.modules.cash.application.schemas import CashSessionView
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser


class CashCloseIssueView(BaseModel):
    code: str
    message: str


class CashClosePaymentMethodCatalogView(BaseModel):
    payment_method_code: str
    currency_code: str
    display_order: int
    is_active: bool
    is_expected_supported: bool


class CashClosePaymentMethodRowView(BaseModel):
    payment_method_code: str
    currency_code: str
    display_order: int
    counted_amount: Decimal | None = None
    expected_amount: Decimal | None = None
    variance_amount: Decimal | None = None
    is_expected_supported: bool


class CashCloseBaselineSnapshotSummaryView(BaseModel):
    is_available: bool
    latest_snapshot_id: UUID | None
    snapshot_type: str | None
    captured_at_utc: datetime | None
    source_cash_session_close_id: UUID | None
    is_first_controlled_close: bool


class CashClosePendingClassCaptureSummaryView(BaseModel):
    has_pending_class_capture: bool
    pending_class_capture_classes_count: int
    pending_class_capture_total_quantity: Decimal


class CashCloseMovementBreakdownView(BaseModel):
    movement_type: str
    direction: str
    currency_code: str
    movement_count: int
    total_amount: Decimal


class CashCloseBootstrapResponse(BaseModel):
    user: AuthenticatedUser
    branch: BranchSummary
    workstation: WorkstationSummary
    local_timestamp: datetime
    current_open_cash_session: CashSessionView | None
    branch_brand_key: str | None = None
    blockers: list[CashCloseIssueView]
    warnings: list[CashCloseIssueView]
    can_start_close: bool
    payment_method_catalog: list[CashClosePaymentMethodCatalogView]
    baseline_snapshot: CashCloseBaselineSnapshotSummaryView
    pending_class_capture: CashClosePendingClassCaptureSummaryView


class CashCloseSummaryResponse(BaseModel):
    cash_session: CashSessionView
    currency_code: str
    opening_amount: Decimal
    total_cash_in: Decimal
    total_cash_out: Decimal
    expected_cash_amount: Decimal
    movement_breakdown: list[CashCloseMovementBreakdownView]
    blockers: list[CashCloseIssueView]
    warnings: list[CashCloseIssueView]
    can_start_close: bool
    baseline_snapshot: CashCloseBaselineSnapshotSummaryView
    pending_class_capture: CashClosePendingClassCaptureSummaryView
    reconciliation_status: str


class CashCloseCountedPaymentMethodRequest(BaseModel):
    payment_method_code: str = Field(min_length=1, max_length=40)
    counted_amount: Decimal = Field(ge=Decimal("0.00"), max_digits=12, decimal_places=2)


class CashCloseCountedProductLineRequest(BaseModel):
    product_id: UUID
    counted_quantity: Decimal = Field(ge=Decimal("0.000"), max_digits=12, decimal_places=3)
    notes: str | None = Field(default=None, max_length=1000)


class CashCloseManualReconciliationAttributionLineRequest(BaseModel):
    product_id: UUID
    attributed_quantity: Decimal = Field(gt=Decimal("0.000"), max_digits=12, decimal_places=3)


class CashCloseManualReconciliationOverrideRequest(BaseModel):
    product_class_id: UUID
    attribution_lines: list[CashCloseManualReconciliationAttributionLineRequest] = Field(
        min_length=1
    )
    notes: str | None = Field(default=None, max_length=1000)


class CashCloseDiscrepancyResolutionRequest(BaseModel):
    product_id: UUID
    resolution_type: str = Field(min_length=1, max_length=40)
    reason_code: str = Field(min_length=1, max_length=40)
    quantity: Decimal = Field(gt=Decimal("0.000"), max_digits=12, decimal_places=3)
    notes: str | None = Field(default=None, max_length=1000)


class CashClosePreviewRequest(BaseModel):
    workstation_code: str = Field(min_length=1, max_length=64)
    close_mode: str = Field(default="WITH_COUNT", min_length=1, max_length=40)
    counter_empty_confirmed: bool = False
    counted_payment_methods: list[CashCloseCountedPaymentMethodRequest] = Field(
        default_factory=list
    )
    counted_product_lines: list[CashCloseCountedProductLineRequest] = Field(default_factory=list)
    manual_reconciliation_overrides: list[CashCloseManualReconciliationOverrideRequest] = Field(
        default_factory=list
    )
    discrepancy_resolutions: list[CashCloseDiscrepancyResolutionRequest] = Field(
        default_factory=list
    )
    notes: str | None = Field(default=None, max_length=1000)


class CashCloseReconciliationProductView(BaseModel):
    product_id: UUID
    product_code: str
    product_name: str
    product_class_id: UUID
    product_class_code: str
    product_class_name: str
    expected_quantity_before_deferred_attr: Decimal
    counted_quantity: Decimal | None = None
    final_expected_quantity: Decimal | None = None
    discrepancy_quantity: Decimal | None = None
    notes: str | None = None


class CashCloseCounterClassAvailabilityView(BaseModel):
    product_class_id: UUID
    product_class_code: str
    product_class_name: str
    expected_quantity_before_deferred_attr: Decimal
    pending_class_capture_quantity: Decimal
    available_quantity: Decimal


class CashCloseAttributionLineView(BaseModel):
    product_id: UUID
    product_code: str
    product_name: str
    product_class_id: UUID
    product_class_code: str
    product_class_name: str
    attributed_quantity: Decimal
    attribution_source: str
    notes: str | None = None


class CashCloseClassReconciliationView(BaseModel):
    product_class_id: UUID
    product_class_code: str
    product_class_name: str
    pending_quantity: Decimal
    auto_attributed_quantity: Decimal
    final_attributed_quantity: Decimal
    discrepancy_quantity: Decimal
    resolution_status: str
    attribution_lines: list[CashCloseAttributionLineView]
    notes: str | None = None


class CashCloseDiscrepancyResolutionView(BaseModel):
    product_id: UUID
    product_code: str
    product_name: str
    product_class_id: UUID
    product_class_code: str
    product_class_name: str
    expected_quantity: Decimal
    counted_quantity: Decimal
    discrepancy_quantity: Decimal
    resolution_type: str
    reason_code: str | None = None
    notes: str | None = None
    generated_document_id: UUID | None = None


class CashCloseGeneratedDocumentView(BaseModel):
    id: UUID
    document_type: str
    status: str


class CashCloseReconciliationResponse(BaseModel):
    cash_session: CashSessionView
    baseline_snapshot: CashCloseBaselineSnapshotSummaryView
    pending_class_capture: CashClosePendingClassCaptureSummaryView
    blockers: list[CashCloseIssueView]
    warnings: list[CashCloseIssueView]
    can_commit: bool
    relevant_products: list[CashCloseReconciliationProductView]
    counter_class_availability: list[CashCloseCounterClassAvailabilityView]
    class_reconciliations: list[CashCloseClassReconciliationView]
    reconciliation_status: str


class CashClosePreviewResponse(BaseModel):
    cash_session: CashSessionView
    close_mode: str
    counter_empty_confirmed: bool
    currency_code: str
    opening_amount: Decimal
    total_cash_in: Decimal
    total_cash_out: Decimal
    expected_cash_amount: Decimal
    counted_cash_amount: Decimal | None = None
    cash_variance_amount: Decimal | None = None
    payment_method_rows: list[CashClosePaymentMethodRowView]
    movement_breakdown: list[CashCloseMovementBreakdownView]
    blockers: list[CashCloseIssueView]
    warnings: list[CashCloseIssueView]
    can_start_close: bool
    baseline_snapshot: CashCloseBaselineSnapshotSummaryView
    pending_class_capture: CashClosePendingClassCaptureSummaryView
    reconciliation_status: str
    counted_product_lines: list[CashCloseReconciliationProductView]
    class_reconciliations: list[CashCloseClassReconciliationView]
    discrepancy_resolutions: list[CashCloseDiscrepancyResolutionView]
    generated_discrepancy_documents: list[CashCloseGeneratedDocumentView]
    notes: str | None


class CashCloseDetailResponse(BaseModel):
    id: UUID
    cash_session: CashSessionView
    close_mode: str
    counter_empty_confirmed: bool
    branch: BranchSummary
    workstation: WorkstationSummary
    branch_brand_key: str | None = None
    opened_by: AuthenticatedUser
    closed_by: AuthenticatedUser | None
    opened_at: datetime
    closed_at: datetime
    currency_code: str
    opening_amount: Decimal
    total_cash_in: Decimal
    total_cash_out: Decimal
    expected_cash_amount: Decimal
    counted_cash_amount: Decimal | None = None
    cash_variance_amount: Decimal | None = None
    payment_method_rows: list[CashClosePaymentMethodRowView]
    movement_breakdown: list[CashCloseMovementBreakdownView]
    pending_class_capture: CashClosePendingClassCaptureSummaryView
    reconciliation_status: str
    counted_product_lines: list[CashCloseReconciliationProductView]
    class_reconciliations: list[CashCloseClassReconciliationView]
    discrepancy_resolutions: list[CashCloseDiscrepancyResolutionView]
    generated_discrepancy_documents: list[CashCloseGeneratedDocumentView]
    warnings: list[CashCloseIssueView]
    notes: str | None
