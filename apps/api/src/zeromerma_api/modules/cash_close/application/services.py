from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.application.access import (
    WorkstationAccessService,
    WorkstationContext,
)
from zeromerma_api.modules.branches.application.schemas import BranchSummary, WorkstationSummary
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.cash.application.schemas import CashSessionView
from zeromerma_api.modules.cash.application.services import CashSessionQueryService
from zeromerma_api.modules.cash.domain.constants import (
    CASH_SESSION_STATUS_CLOSED,
    CASH_SESSION_STATUS_OPEN,
)
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.cash_close.application.schemas import (
    CashCloseAttributionLineView,
    CashCloseBaselineSnapshotSummaryView,
    CashCloseBootstrapResponse,
    CashCloseClassReconciliationView,
    CashCloseCountedPaymentMethodRequest,
    CashCloseCountedProductLineRequest,
    CashCloseCounterClassAvailabilityView,
    CashCloseDetailResponse,
    CashCloseDiscrepancyResolutionRequest,
    CashCloseDiscrepancyResolutionView,
    CashCloseGeneratedDocumentView,
    CashCloseIssueView,
    CashCloseManualReconciliationOverrideRequest,
    CashCloseMovementBreakdownView,
    CashClosePaymentMethodCatalogView,
    CashClosePaymentMethodRowView,
    CashClosePendingClassCaptureSummaryView,
    CashClosePreviewRequest,
    CashClosePreviewResponse,
    CashCloseReconciliationProductView,
    CashCloseReconciliationResponse,
    CashCloseSummaryResponse,
)
from zeromerma_api.modules.cash_close.domain.constants import (
    BRANCH_COUNTER_SNAPSHOT_TYPE_CLOSE_BASELINE,
    CASH_CLOSE_BLOCKER_INCONSISTENT_SESSION_CONTEXT,
    CASH_CLOSE_BLOCKER_INTERNAL_INTEGRITY_MISMATCH,
    CASH_CLOSE_BLOCKER_INVALID_COUNT_PAYLOAD,
    CASH_CLOSE_BLOCKER_INVALID_DISCREPANCY_RESOLUTION,
    CASH_CLOSE_BLOCKER_INVALID_MANUAL_RECONCILIATION_OVERRIDE,
    CASH_CLOSE_BLOCKER_MISSING_COUNTED_CLOSING_STOCK,
    CASH_CLOSE_BLOCKER_MISSING_COUNTED_PAYMENT_TOTALS,
    CASH_CLOSE_BLOCKER_NO_ACTIVE_OPEN_CASH_SESSION,
    CASH_CLOSE_BLOCKER_SESSION_ALREADY_CLOSED,
    CASH_CLOSE_BLOCKER_UNRESOLVED_CLASS_CAPTURE_MISMATCH,
    CASH_CLOSE_CLASS_RESOLUTION_STATUS_AUTO_RESOLVED,
    CASH_CLOSE_CLASS_RESOLUTION_STATUS_COUNT_REQUIRED,
    CASH_CLOSE_CLASS_RESOLUTION_STATUS_MANUAL_RESOLVED,
    CASH_CLOSE_CLASS_RESOLUTION_STATUS_UNRESOLVED,
    CASH_CLOSE_CURRENCY_MXN,
    CASH_CLOSE_DISCREPANCY_REASON_COUNTER_OVERAGE,
    CASH_CLOSE_DISCREPANCY_REASON_COUNTER_SHORTAGE,
    CASH_CLOSE_DISCREPANCY_RESOLUTION_TYPE_CLOSE_COUNTER_ADJUSTMENT,
    CASH_CLOSE_DISCREPANCY_RESOLUTION_TYPE_CLOSE_WASTE_ADJUSTMENT,
    CASH_CLOSE_ISSUE_LEVEL_WARNING,
    CASH_CLOSE_MODE_WITH_COUNT,
    CASH_CLOSE_PAYMENT_METHOD_CARD,
    CASH_CLOSE_PAYMENT_METHOD_CASH,
    CASH_CLOSE_PAYMENT_METHOD_MIXED,
    CASH_CLOSE_RECONCILIATION_STATUS_BLOCKED,
    CASH_CLOSE_RECONCILIATION_STATUS_NOT_EVALUATED,
    CASH_CLOSE_RECONCILIATION_STATUS_PENDING,
    CASH_CLOSE_RECONCILIATION_STATUS_READY,
    CASH_CLOSE_STATUS_COMMITTED,
    CASH_CLOSE_WARNING_LARGE_CASH_VARIANCE,
    CASH_CLOSE_WARNING_LONG_SESSION_DURATION,
    CASH_CLOSE_WARNING_OUTBOUND_TRANSFERS_IN_TRANSIT,
    CASH_CLOSE_WARNING_PENDING_INBOUND_TRANSFERS,
    EXPECTED_CASH_CLOSE_PAYMENT_METHOD_CODES,
    LARGE_CASH_VARIANCE_WARNING_THRESHOLD,
    LONG_SESSION_DURATION_WARNING_HOURS,
    OUTBOX_EVENT_CASH_SESSION_CLOSED_V1,
    OUTBOX_EVENT_CLASS_CAPTURE_RECONCILED_V1,
    OUTBOX_EVENT_CLOSE_DISCREPANCY_GENERATED_V1,
    VALID_CASH_CLOSE_DISCREPANCY_REASON_CODES,
    VALID_CASH_CLOSE_DISCREPANCY_RESOLUTION_TYPES,
    VALID_CASH_CLOSE_MODES,
    VALID_CASH_CLOSE_PAYMENT_METHOD_CODES,
)
from zeromerma_api.modules.cash_close.domain.exceptions import (
    CashCloseConflictError,
    CashCloseNotFoundError,
    CashCloseValidationError,
)
from zeromerma_api.modules.cash_close.infrastructure.models import (
    BranchCounterSnapshot,
    BranchCounterSnapshotLine,
    CashSessionClose,
    CashSessionCloseClassReconciliation,
    CashSessionCloseDiscrepancyResolution,
    CashSessionCloseIssue,
    CashSessionClosePaymentMethodCount,
    CashSessionCloseProductCount,
    CashSessionCloseReconciliationAttribution,
)
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.corrections.domain.constants import CORRECTION_STATUS_COMMITTED
from zeromerma_api.modules.corrections.infrastructure.models import (
    CorrectionDocument,
    CorrectionDocumentLine,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User, UserBranchAssignment
from zeromerma_api.modules.operations.domain.constants import (
    BRANCH_BRAND_MAPPING,
    OPERATION_BUCKET_BACKROOM,
    OPERATION_BUCKET_COUNTER,
    OPERATION_BUCKET_WASTE,
    OPERATION_DOCUMENT_STATUS_COMMITTED,
    OPERATION_DOCUMENT_STATUS_IN_TRANSIT,
    OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT,
    OPERATION_DOCUMENT_TYPE_CLOSE_COUNTER_ADJUSTMENT,
    OPERATION_DOCUMENT_TYPE_CLOSE_WASTE_ADJUSTMENT,
    OPERATION_DOCUMENT_TYPE_COUNTER_TRANSFER,
    OPERATION_DOCUMENT_TYPE_WASTE_RECORD,
)
from zeromerma_api.modules.operations.infrastructure.models import (
    OperationDocument,
    OperationDocumentLine,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.returns.domain.constants import (
    RETURN_DISPOSITION_RESTOCK_COUNTER,
    RETURN_STATUS_COMMITTED,
)
from zeromerma_api.modules.returns.infrastructure.models import SaleReturn, SaleReturnLine
from zeromerma_api.modules.sales.domain.constants import (
    CASH_MOVEMENT_DIRECTION_IN,
    CASH_MOVEMENT_DIRECTION_OUT,
    SALE_LINE_PHYSICAL_ATTRIBUTION_PENDING_RECONCILIATION,
    SALE_LINE_PHYSICAL_ATTRIBUTION_RECONCILED,
)
from zeromerma_api.modules.sales.infrastructure.models import CashMovement, Sale, SaleLine

MONEY_QUANTIZER = Decimal("0.01")
QUANTITY_QUANTIZER = Decimal("0.001")
ZERO_MONEY = Decimal("0.00")
ZERO_QUANTITY = Decimal("0.000")

PAYMENT_METHOD_CATALOG = (
    (
        CASH_CLOSE_PAYMENT_METHOD_CASH,
        10,
        CASH_CLOSE_PAYMENT_METHOD_CASH in EXPECTED_CASH_CLOSE_PAYMENT_METHOD_CODES,
    ),
    (
        CASH_CLOSE_PAYMENT_METHOD_CARD,
        20,
        CASH_CLOSE_PAYMENT_METHOD_CARD in EXPECTED_CASH_CLOSE_PAYMENT_METHOD_CODES,
    ),
    (
        CASH_CLOSE_PAYMENT_METHOD_MIXED,
        30,
        CASH_CLOSE_PAYMENT_METHOD_MIXED in EXPECTED_CASH_CLOSE_PAYMENT_METHOD_CODES,
    ),
)


@dataclass(frozen=True)
class CashCloseContextState:
    workstation_context: WorkstationContext
    current_open_cash_session: CashSessionView | None
    latest_workstation_session_id: uuid.UUID | None
    latest_workstation_session_status: str | None
    user_open_session_on_other_workstation: CashSessionView | None


@dataclass(frozen=True)
class CashCloseFinancialSummary:
    currency_code: str
    total_cash_in: Decimal
    total_cash_out: Decimal
    expected_cash_amount: Decimal
    movement_breakdown: list[CashCloseMovementBreakdownView]


@dataclass(frozen=True)
class ProductIdentity:
    product_id: uuid.UUID
    product_code: str
    product_name: str
    product_class_id: uuid.UUID
    product_class_code: str
    product_class_name: str
    product_display_order: int
    class_display_order: int


@dataclass(frozen=True)
class PendingClassCaptureRow:
    product_class_id: uuid.UUID
    product_class_code: str
    product_class_name: str
    display_order: int
    pending_quantity: Decimal


@dataclass(frozen=True)
class CountedProductInput:
    counted_quantity: Decimal
    notes: str | None


@dataclass(frozen=True)
class ManualOverrideInput:
    product_class_id: uuid.UUID
    attribution_lines: list[tuple[uuid.UUID, Decimal]]
    notes: str | None


@dataclass(frozen=True)
class DiscrepancyResolutionInput:
    product_id: uuid.UUID
    resolution_type: str
    reason_code: str
    quantity: Decimal
    notes: str | None


@dataclass(frozen=True)
class ResolvedProductState:
    identity: ProductIdentity
    expected_quantity_before_deferred_attr: Decimal
    counted_quantity: Decimal | None
    final_expected_quantity: Decimal | None
    discrepancy_quantity: Decimal | None
    notes: str | None


@dataclass(frozen=True)
class ResolvedCounterClassAvailability:
    product_class_id: uuid.UUID
    product_class_code: str
    product_class_name: str
    expected_quantity_before_deferred_attr: Decimal
    pending_class_capture_quantity: Decimal
    available_quantity: Decimal
    display_order: int


@dataclass(frozen=True)
class ResolvedAttributionLine:
    identity: ProductIdentity
    attributed_quantity: Decimal
    attribution_source: str
    notes: str | None


@dataclass(frozen=True)
class ResolvedClassReconciliation:
    product_class_id: uuid.UUID
    product_class_code: str
    product_class_name: str
    pending_quantity: Decimal
    auto_attributed_quantity: Decimal
    final_attributed_quantity: Decimal
    discrepancy_quantity: Decimal
    resolution_status: str
    attribution_lines: list[ResolvedAttributionLine]
    notes: str | None


@dataclass(frozen=True)
class ResolvedDiscrepancy:
    identity: ProductIdentity
    expected_quantity: Decimal
    counted_quantity: Decimal
    discrepancy_quantity: Decimal
    resolution_type: str
    reason_code: str | None
    notes: str | None
    generated_document_id: uuid.UUID | None = None


@dataclass(frozen=True)
class CashCloseReconciliationComputation:
    products: list[ResolvedProductState]
    counter_class_availability: list[ResolvedCounterClassAvailability]
    class_reconciliations: list[ResolvedClassReconciliation]
    discrepancy_resolutions: list[ResolvedDiscrepancy]
    blockers: list[CashCloseIssueView]


@dataclass(frozen=True)
class CashClosePreparedPreview:
    active_cash_session: CashSessionView
    close_mode: str
    counter_empty_confirmed: bool
    baseline_snapshot: CashCloseBaselineSnapshotSummaryView
    pending_class_capture: CashClosePendingClassCaptureSummaryView
    financial_summary: CashCloseFinancialSummary
    payment_method_rows: list[CashClosePaymentMethodRowView]
    counted_cash_amount: Decimal | None
    cash_variance_amount: Decimal | None
    warnings: list[CashCloseIssueView]
    blockers: list[CashCloseIssueView]
    reconciliation_status: str
    computation: CashCloseReconciliationComputation
    notes: str | None


class CashCloseQueryService:
    def __init__(
        self,
        workstation_access: WorkstationAccessService | None = None,
        cash_session_query: CashSessionQueryService | None = None,
    ) -> None:
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._cash_session_query = cash_session_query or CashSessionQueryService()

    def get_bootstrap(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
    ) -> CashCloseBootstrapResponse:
        context_state = _resolve_cash_close_context(
            session,
            workstation_access=self._workstation_access,
            cash_session_query=self._cash_session_query,
            current_user=current_user,
            workstation_code=workstation_code,
        )
        local_timestamp = datetime.now(tz=UTC).astimezone(
            ZoneInfo(context_state.workstation_context.branch_timezone)
        )
        baseline_snapshot = _get_baseline_snapshot_summary(
            session,
            branch_id=context_state.workstation_context.branch_id,
        )
        pending_rows = _get_pending_class_capture_rows(
            session,
            cash_session_id=(
                context_state.current_open_cash_session.id
                if context_state.current_open_cash_session is not None
                else None
            ),
        )
        pending_summary = _build_pending_class_capture_summary(pending_rows)
        blockers = _build_context_blockers(
            current_user=current_user,
            context_state=context_state,
            baseline_snapshot=baseline_snapshot,
        )
        warnings = _build_warnings(
            session,
            context_state=context_state,
            counted_cash_amount=None,
            cash_variance_amount=None,
        )

        return CashCloseBootstrapResponse(
            user=current_user,
            branch=BranchSummary(
                id=context_state.workstation_context.branch_id,
                code=context_state.workstation_context.branch_code,
                name=context_state.workstation_context.branch_name,
                timezone=context_state.workstation_context.branch_timezone,
                is_active=context_state.workstation_context.branch_is_active,
            ),
            workstation=WorkstationSummary(
                id=context_state.workstation_context.workstation_id,
                code=context_state.workstation_context.workstation_code,
                name=context_state.workstation_context.workstation_name,
                is_active=context_state.workstation_context.workstation_is_active,
            ),
            local_timestamp=local_timestamp,
            current_open_cash_session=context_state.current_open_cash_session,
            branch_brand_key=_get_branch_brand_key(context_state.workstation_context.branch_code),
            blockers=blockers,
            warnings=warnings,
            can_start_close=len(blockers) == 0,
            payment_method_catalog=_get_payment_method_catalog(),
            baseline_snapshot=baseline_snapshot,
            pending_class_capture=pending_summary,
        )

    def get_summary(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
    ) -> CashCloseSummaryResponse:
        context_state = _resolve_cash_close_context(
            session,
            workstation_access=self._workstation_access,
            cash_session_query=self._cash_session_query,
            current_user=current_user,
            workstation_code=workstation_code,
        )
        active_cash_session = _require_previewable_cash_session(
            current_user=current_user,
            context_state=context_state,
        )
        baseline_snapshot = _get_baseline_snapshot_summary(
            session,
            branch_id=context_state.workstation_context.branch_id,
        )
        pending_rows = _get_pending_class_capture_rows(
            session,
            cash_session_id=active_cash_session.id,
        )
        pending_summary = _build_pending_class_capture_summary(pending_rows)
        financial_summary = _get_financial_summary(
            session,
            cash_session_id=active_cash_session.id,
            opening_amount=active_cash_session.opening_amount,
        )
        blockers = _build_context_blockers(
            current_user=current_user,
            context_state=context_state,
            baseline_snapshot=baseline_snapshot,
        )
        warnings = _build_warnings(
            session,
            context_state=context_state,
            counted_cash_amount=None,
            cash_variance_amount=None,
        )

        return CashCloseSummaryResponse(
            cash_session=active_cash_session,
            currency_code=financial_summary.currency_code,
            opening_amount=active_cash_session.opening_amount,
            total_cash_in=financial_summary.total_cash_in,
            total_cash_out=financial_summary.total_cash_out,
            expected_cash_amount=financial_summary.expected_cash_amount,
            movement_breakdown=financial_summary.movement_breakdown,
            blockers=blockers,
            warnings=warnings,
            can_start_close=len(blockers) == 0,
            baseline_snapshot=baseline_snapshot,
            pending_class_capture=pending_summary,
            reconciliation_status=_resolve_query_reconciliation_status(blockers),
        )

    def get_reconciliation(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
    ) -> CashCloseReconciliationResponse:
        context_state = _resolve_cash_close_context(
            session,
            workstation_access=self._workstation_access,
            cash_session_query=self._cash_session_query,
            current_user=current_user,
            workstation_code=workstation_code,
        )
        active_cash_session = _require_previewable_cash_session(
            current_user=current_user,
            context_state=context_state,
        )
        baseline_snapshot = _get_baseline_snapshot_summary(
            session,
            branch_id=context_state.workstation_context.branch_id,
        )
        pending_rows = _get_pending_class_capture_rows(
            session,
            cash_session_id=active_cash_session.id,
        )
        pending_summary = _build_pending_class_capture_summary(pending_rows)
        blockers = _build_context_blockers(
            current_user=current_user,
            context_state=context_state,
            baseline_snapshot=baseline_snapshot,
        )
        warnings = _build_warnings(
            session,
            context_state=context_state,
            counted_cash_amount=None,
            cash_variance_amount=None,
        )
        computation = _compute_reconciliation(
            session,
            cash_session=active_cash_session,
            workstation_id=context_state.workstation_context.workstation_id,
            branch_id=context_state.workstation_context.branch_id,
            counted_product_lines=[],
            counter_empty_confirmed=False,
            manual_reconciliation_overrides=[],
            discrepancy_resolutions=[],
        )
        merged_blockers = _merge_issues(blockers, computation.blockers)

        return CashCloseReconciliationResponse(
            cash_session=active_cash_session,
            baseline_snapshot=baseline_snapshot,
            pending_class_capture=pending_summary,
            blockers=merged_blockers,
            warnings=warnings,
            can_commit=False,
            relevant_products=_to_product_views(computation.products),
            counter_class_availability=_to_counter_class_availability_views(
                computation.counter_class_availability
            ),
            class_reconciliations=_to_class_reconciliation_views(computation.class_reconciliations),
            reconciliation_status=_resolve_query_reconciliation_status(merged_blockers),
        )

    def preview_close(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: CashClosePreviewRequest,
    ) -> CashClosePreviewResponse:
        prepared = self._prepare_preview(
            session,
            current_user=current_user,
            command=command,
        )
        return CashClosePreviewResponse(
            cash_session=prepared.active_cash_session,
            close_mode=prepared.close_mode,
            counter_empty_confirmed=prepared.counter_empty_confirmed,
            currency_code=prepared.financial_summary.currency_code,
            opening_amount=prepared.active_cash_session.opening_amount,
            total_cash_in=prepared.financial_summary.total_cash_in,
            total_cash_out=prepared.financial_summary.total_cash_out,
            expected_cash_amount=prepared.financial_summary.expected_cash_amount,
            counted_cash_amount=prepared.counted_cash_amount,
            cash_variance_amount=prepared.cash_variance_amount,
            payment_method_rows=prepared.payment_method_rows,
            movement_breakdown=prepared.financial_summary.movement_breakdown,
            blockers=prepared.blockers,
            warnings=prepared.warnings,
            can_start_close=len(prepared.blockers) == 0,
            baseline_snapshot=prepared.baseline_snapshot,
            pending_class_capture=prepared.pending_class_capture,
            reconciliation_status=prepared.reconciliation_status,
            counted_product_lines=_to_product_views(prepared.computation.products),
            class_reconciliations=_to_class_reconciliation_views(
                prepared.computation.class_reconciliations
            ),
            discrepancy_resolutions=_to_discrepancy_views(
                prepared.computation.discrepancy_resolutions
            ),
            generated_discrepancy_documents=[],
            notes=prepared.notes,
        )

    def get_close_detail(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        close_id: uuid.UUID,
    ) -> CashCloseDetailResponse:
        close_record = session.execute(
            select(CashSessionClose).where(CashSessionClose.id == close_id)
        ).scalar_one_or_none()
        if close_record is None:
            raise CashCloseNotFoundError("No se encontro el reporte del cierre solicitado.")

        branch_assignment_id = session.execute(
            select(UserBranchAssignment.id).where(
                UserBranchAssignment.user_id == current_user.id,
                UserBranchAssignment.branch_id == close_record.branch_id,
                UserBranchAssignment.is_active.is_(True),
            )
        ).scalar_one_or_none()
        if branch_assignment_id is None:
            raise CashCloseNotFoundError("No se encontro el reporte del cierre solicitado.")

        cash_session_view = self._cash_session_query.get_session_by_id(
            session,
            cash_session_id=close_record.cash_session_id,
        )
        branch = session.execute(
            select(Branch).where(Branch.id == close_record.branch_id)
        ).scalar_one()
        workstation = session.execute(
            select(Workstation).where(Workstation.id == close_record.workstation_id)
        ).scalar_one()
        opened_by = session.execute(
            select(User).where(User.id == cash_session_view.user_id)
        ).scalar_one()
        closed_by = (
            session.execute(
                select(User).where(User.id == close_record.closed_by_user_id)
            ).scalar_one()
            if close_record.closed_by_user_id is not None
            else None
        )

        payment_method_rows = [
            dict(row)
            for row in session.execute(
                select(
                    CashSessionClosePaymentMethodCount.payment_method_code,
                    CashSessionClosePaymentMethodCount.currency_code,
                    CashSessionClosePaymentMethodCount.counted_amount,
                    CashSessionClosePaymentMethodCount.expected_amount,
                    CashSessionClosePaymentMethodCount.variance_amount,
                ).where(CashSessionClosePaymentMethodCount.cash_session_close_id == close_record.id)
            )
            .mappings()
            .all()
        ]
        counted_product_rows = (
            session.execute(
                select(
                    CashSessionCloseProductCount.product_id,
                    CashSessionCloseProductCount.product_code_snapshot,
                    CashSessionCloseProductCount.product_name_snapshot,
                    CashSessionCloseProductCount.product_class_id,
                    CashSessionCloseProductCount.product_class_code_snapshot,
                    CashSessionCloseProductCount.product_class_name_snapshot,
                    CashSessionCloseProductCount.quantity,
                    CashSessionCloseProductCount.notes,
                )
                .where(CashSessionCloseProductCount.cash_session_close_id == close_record.id)
                .order_by(
                    CashSessionCloseProductCount.product_class_code_snapshot.asc(),
                    CashSessionCloseProductCount.product_code_snapshot.asc(),
                )
            )
            .mappings()
            .all()
        )
        class_rows = (
            session.execute(
                select(
                    CashSessionCloseClassReconciliation.id,
                    CashSessionCloseClassReconciliation.product_class_id,
                    CashSessionCloseClassReconciliation.product_class_code_snapshot,
                    CashSessionCloseClassReconciliation.product_class_name_snapshot,
                    CashSessionCloseClassReconciliation.expected_quantity,
                    CashSessionCloseClassReconciliation.auto_attributed_quantity,
                    CashSessionCloseClassReconciliation.attributed_quantity,
                    CashSessionCloseClassReconciliation.variance_quantity,
                    CashSessionCloseClassReconciliation.resolution_status,
                    CashSessionCloseClassReconciliation.notes,
                )
                .where(CashSessionCloseClassReconciliation.cash_session_close_id == close_record.id)
                .order_by(CashSessionCloseClassReconciliation.product_class_code_snapshot.asc())
            )
            .mappings()
            .all()
        )
        attribution_rows = (
            session.execute(
                select(
                    CashSessionCloseReconciliationAttribution.class_reconciliation_id,
                    CashSessionCloseReconciliationAttribution.product_id,
                    CashSessionCloseReconciliationAttribution.product_code_snapshot,
                    CashSessionCloseReconciliationAttribution.product_name_snapshot,
                    CashSessionCloseReconciliationAttribution.product_class_id,
                    CashSessionCloseReconciliationAttribution.product_class_code_snapshot,
                    CashSessionCloseReconciliationAttribution.product_class_name_snapshot,
                    CashSessionCloseReconciliationAttribution.attributed_quantity,
                    CashSessionCloseReconciliationAttribution.notes,
                )
                .where(
                    CashSessionCloseReconciliationAttribution.cash_session_close_id
                    == close_record.id
                )
                .order_by(CashSessionCloseReconciliationAttribution.product_code_snapshot.asc())
            )
            .mappings()
            .all()
        )
        discrepancy_rows = (
            session.execute(
                select(
                    CashSessionCloseDiscrepancyResolution.product_id,
                    CashSessionCloseDiscrepancyResolution.product_code_snapshot,
                    CashSessionCloseDiscrepancyResolution.product_name_snapshot,
                    CashSessionCloseDiscrepancyResolution.product_class_id,
                    CashSessionCloseDiscrepancyResolution.product_class_code_snapshot,
                    CashSessionCloseDiscrepancyResolution.product_class_name_snapshot,
                    CashSessionCloseDiscrepancyResolution.expected_quantity,
                    CashSessionCloseDiscrepancyResolution.counted_quantity,
                    CashSessionCloseDiscrepancyResolution.discrepancy_quantity,
                    CashSessionCloseDiscrepancyResolution.resolution_type,
                    CashSessionCloseDiscrepancyResolution.reason_code,
                    CashSessionCloseDiscrepancyResolution.notes,
                    CashSessionCloseDiscrepancyResolution.generated_document_id,
                )
                .where(
                    CashSessionCloseDiscrepancyResolution.cash_session_close_id == close_record.id
                )
                .order_by(CashSessionCloseDiscrepancyResolution.product_code_snapshot.asc())
            )
            .mappings()
            .all()
        )
        warning_rows = (
            session.execute(
                select(CashSessionCloseIssue.code, CashSessionCloseIssue.message).where(
                    CashSessionCloseIssue.cash_session_close_id == close_record.id,
                    CashSessionCloseIssue.issue_level == CASH_CLOSE_ISSUE_LEVEL_WARNING,
                )
            )
            .mappings()
            .all()
        )
        generated_document_ids = [
            row["generated_document_id"]
            for row in discrepancy_rows
            if row["generated_document_id"] is not None
        ]
        generated_documents = (
            session.execute(
                select(
                    OperationDocument.id,
                    OperationDocument.document_type,
                    OperationDocument.status,
                ).where(OperationDocument.id.in_(generated_document_ids))
            )
            .mappings()
            .all()
            if len(generated_document_ids) > 0
            else []
        )

        attribution_by_class: dict[uuid.UUID, list[CashCloseAttributionLineView]] = defaultdict(
            list
        )
        for row in attribution_rows:
            attribution_by_class[row["class_reconciliation_id"]].append(
                CashCloseAttributionLineView(
                    product_id=row["product_id"],
                    product_code=row["product_code_snapshot"],
                    product_name=row["product_name_snapshot"],
                    product_class_id=row["product_class_id"],
                    product_class_code=row["product_class_code_snapshot"],
                    product_class_name=row["product_class_name_snapshot"],
                    attributed_quantity=row["attributed_quantity"],
                    attribution_source="FINAL",
                    notes=row["notes"],
                )
            )

        class_reconciliations = [
            CashCloseClassReconciliationView(
                product_class_id=row["product_class_id"],
                product_class_code=row["product_class_code_snapshot"],
                product_class_name=row["product_class_name_snapshot"],
                pending_quantity=row["expected_quantity"],
                auto_attributed_quantity=row["auto_attributed_quantity"] or ZERO_QUANTITY,
                final_attributed_quantity=row["attributed_quantity"] or ZERO_QUANTITY,
                discrepancy_quantity=row["variance_quantity"] or ZERO_QUANTITY,
                resolution_status=row["resolution_status"],
                attribution_lines=attribution_by_class[row["id"]],
                notes=row["notes"],
            )
            for row in class_rows
        ]
        pending_summary = CashClosePendingClassCaptureSummaryView(
            has_pending_class_capture=len(class_reconciliations) > 0,
            pending_class_capture_classes_count=len(class_reconciliations),
            pending_class_capture_total_quantity=_quantize_quantity(
                sum((row.pending_quantity for row in class_reconciliations), ZERO_QUANTITY)
            ),
        )

        return CashCloseDetailResponse(
            id=close_record.id,
            cash_session=cash_session_view,
            close_mode=close_record.close_mode,
            counter_empty_confirmed=close_record.counter_empty_confirmed,
            branch=BranchSummary(
                id=branch.id,
                code=branch.code,
                name=branch.name,
                timezone=branch.timezone,
                is_active=branch.is_active,
            ),
            workstation=WorkstationSummary(
                id=workstation.id,
                code=workstation.code,
                name=workstation.name,
                is_active=workstation.is_active,
            ),
            branch_brand_key=_get_branch_brand_key(branch.code),
            opened_by=AuthenticatedUser.model_validate(opened_by),
            closed_by=(
                AuthenticatedUser.model_validate(closed_by) if closed_by is not None else None
            ),
            opened_at=cash_session_view.opened_at,
            closed_at=close_record.committed_at_utc or cash_session_view.opened_at,
            currency_code=_financial_currency_or_default(
                [row["currency_code"] for row in payment_method_rows]
            ),
            opening_amount=close_record.opening_amount,
            total_cash_in=close_record.total_cash_in,
            total_cash_out=close_record.total_cash_out,
            expected_cash_amount=close_record.expected_cash_amount,
            counted_cash_amount=close_record.counted_cash_amount,
            cash_variance_amount=close_record.cash_variance_amount,
            payment_method_rows=_to_payment_method_rows(
                payment_method_rows,
                expected_cash_amount=close_record.expected_cash_amount,
            ),
            movement_breakdown=_get_financial_summary(
                session,
                cash_session_id=close_record.cash_session_id,
                opening_amount=close_record.opening_amount,
            ).movement_breakdown,
            pending_class_capture=pending_summary,
            reconciliation_status=close_record.reconciliation_status,
            counted_product_lines=[
                CashCloseReconciliationProductView(
                    product_id=row["product_id"],
                    product_code=row["product_code_snapshot"],
                    product_name=row["product_name_snapshot"],
                    product_class_id=row["product_class_id"],
                    product_class_code=row["product_class_code_snapshot"],
                    product_class_name=row["product_class_name_snapshot"],
                    expected_quantity_before_deferred_attr=ZERO_QUANTITY,
                    counted_quantity=row["quantity"],
                    final_expected_quantity=None,
                    discrepancy_quantity=None,
                    notes=row["notes"],
                )
                for row in counted_product_rows
            ],
            class_reconciliations=class_reconciliations,
            discrepancy_resolutions=[
                CashCloseDiscrepancyResolutionView(
                    product_id=row["product_id"],
                    product_code=row["product_code_snapshot"],
                    product_name=row["product_name_snapshot"],
                    product_class_id=row["product_class_id"],
                    product_class_code=row["product_class_code_snapshot"],
                    product_class_name=row["product_class_name_snapshot"],
                    expected_quantity=row["expected_quantity"],
                    counted_quantity=row["counted_quantity"],
                    discrepancy_quantity=row["discrepancy_quantity"],
                    resolution_type=row["resolution_type"],
                    reason_code=row["reason_code"],
                    notes=row["notes"],
                    generated_document_id=row["generated_document_id"],
                )
                for row in discrepancy_rows
            ],
            generated_discrepancy_documents=[
                CashCloseGeneratedDocumentView(
                    id=row["id"],
                    document_type=row["document_type"],
                    status=row["status"],
                )
                for row in generated_documents
            ],
            warnings=[
                CashCloseIssueView(code=row["code"], message=row["message"]) for row in warning_rows
            ],
            notes=close_record.notes,
        )

    def _prepare_preview(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: CashClosePreviewRequest,
    ) -> CashClosePreparedPreview:
        context_state = _resolve_cash_close_context(
            session,
            workstation_access=self._workstation_access,
            cash_session_query=self._cash_session_query,
            current_user=current_user,
            workstation_code=command.workstation_code,
        )
        active_cash_session = _require_previewable_cash_session(
            current_user=current_user,
            context_state=context_state,
        )
        baseline_snapshot = _get_baseline_snapshot_summary(
            session,
            branch_id=context_state.workstation_context.branch_id,
        )
        pending_rows = _get_pending_class_capture_rows(
            session,
            cash_session_id=active_cash_session.id,
        )
        pending_summary = _build_pending_class_capture_summary(pending_rows)
        financial_summary = _get_financial_summary(
            session,
            cash_session_id=active_cash_session.id,
            opening_amount=active_cash_session.opening_amount,
        )
        close_mode = _normalize_close_mode(command.close_mode)
        counter_empty_confirmed = command.counter_empty_confirmed
        payment_method_rows, counted_cash_amount, has_counted_monetary_input = (
            _build_preview_payment_method_rows(
                close_mode=close_mode,
                counted_payment_methods=command.counted_payment_methods,
                expected_cash_amount=financial_summary.expected_cash_amount,
            )
        )
        cash_variance_amount = (
            _quantize_money(counted_cash_amount - financial_summary.expected_cash_amount)
            if counted_cash_amount is not None
            else None
        )
        warnings = _build_warnings(
            session,
            context_state=context_state,
            counted_cash_amount=counted_cash_amount,
            cash_variance_amount=cash_variance_amount,
        )
        blockers = _build_context_blockers(
            current_user=current_user,
            context_state=context_state,
            baseline_snapshot=baseline_snapshot,
        )
        blockers = _merge_issues(blockers, _build_physical_count_blockers(command))

        computation = _compute_reconciliation(
            session,
            cash_session=active_cash_session,
            workstation_id=context_state.workstation_context.workstation_id,
            branch_id=context_state.workstation_context.branch_id,
            counted_product_lines=command.counted_product_lines,
            counter_empty_confirmed=counter_empty_confirmed,
            manual_reconciliation_overrides=command.manual_reconciliation_overrides,
            discrepancy_resolutions=command.discrepancy_resolutions,
        )
        blockers = _merge_issues(blockers, computation.blockers)
        is_ready_to_close = (
            has_counted_monetary_input
            and (
                counter_empty_confirmed
                or len(computation.products) == 0
                or len(command.counted_product_lines) > 0
            )
            and len(blockers) == 0
        )

        return CashClosePreparedPreview(
            active_cash_session=active_cash_session,
            close_mode=close_mode,
            counter_empty_confirmed=counter_empty_confirmed,
            baseline_snapshot=baseline_snapshot,
            pending_class_capture=pending_summary,
            financial_summary=financial_summary,
            payment_method_rows=payment_method_rows,
            counted_cash_amount=counted_cash_amount,
            cash_variance_amount=cash_variance_amount,
            warnings=warnings,
            blockers=blockers,
            reconciliation_status=_resolve_preview_reconciliation_status(
                blockers,
                is_ready_to_close=is_ready_to_close,
            ),
            computation=computation,
            notes=command.notes,
        )


class CashCloseCommandService:
    def __init__(
        self,
        workstation_access: WorkstationAccessService | None = None,
        cash_session_query: CashSessionQueryService | None = None,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
        query_service: CashCloseQueryService | None = None,
    ) -> None:
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._cash_session_query = cash_session_query or CashSessionQueryService()
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()
        self._query_service = query_service or CashCloseQueryService(
            workstation_access=self._workstation_access,
            cash_session_query=self._cash_session_query,
        )

    def commit_close(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: CashClosePreviewRequest,
        request_id: str | None,
    ) -> CashCloseDetailResponse:
        prepared = self._query_service._prepare_preview(
            session,
            current_user=current_user,
            command=command,
        )
        commit_blockers = _build_commit_blockers(
            command=command,
            prepared=prepared,
        )
        if len(commit_blockers) > 0:
            raise CashCloseValidationError(_format_blocker_error(commit_blockers))

        committed_at = datetime.now(tz=UTC)
        resolved_request_id = request_id or str(uuid.uuid4())
        has_count_capture = prepared.close_mode == CASH_CLOSE_MODE_WITH_COUNT
        active_cash_session = session.execute(
            select(CashSession).where(CashSession.id == prepared.active_cash_session.id)
        ).scalar_one()

        close_row = CashSessionClose(
            cash_session_id=active_cash_session.id,
            branch_id=active_cash_session.branch_id,
            workstation_id=active_cash_session.workstation_id,
            closed_by_user_id=current_user.id,
            status=CASH_CLOSE_STATUS_COMMITTED,
            close_mode=prepared.close_mode,
            counter_empty_confirmed=prepared.counter_empty_confirmed,
            opening_amount=prepared.active_cash_session.opening_amount,
            total_cash_in=prepared.financial_summary.total_cash_in,
            total_cash_out=prepared.financial_summary.total_cash_out,
            expected_cash_amount=prepared.financial_summary.expected_cash_amount,
            counted_cash_amount=prepared.counted_cash_amount,
            cash_variance_amount=prepared.cash_variance_amount,
            reconciliation_status=(
                CASH_CLOSE_RECONCILIATION_STATUS_READY
                if has_count_capture
                else CASH_CLOSE_RECONCILIATION_STATUS_NOT_EVALUATED
            ),
            notes=prepared.notes,
            started_at_utc=committed_at,
            committed_at_utc=committed_at,
        )

        try:
            session.add(close_row)
            session.flush()

            for row in prepared.payment_method_rows:
                if row.counted_amount is None:
                    continue
                session.add(
                    CashSessionClosePaymentMethodCount(
                        cash_session_close_id=close_row.id,
                        payment_method_code=row.payment_method_code,
                        currency_code=row.currency_code,
                        counted_amount=row.counted_amount,
                        expected_amount=row.expected_amount,
                        variance_amount=row.variance_amount,
                    )
                )

            if has_count_capture:
                for product_state in prepared.computation.products:
                    if product_state.counted_quantity is None:
                        continue
                    session.add(
                        CashSessionCloseProductCount(
                            cash_session_close_id=close_row.id,
                            product_id=product_state.identity.product_id,
                            product_code_snapshot=product_state.identity.product_code,
                            product_name_snapshot=product_state.identity.product_name,
                            product_class_id=product_state.identity.product_class_id,
                            product_class_code_snapshot=product_state.identity.product_class_code,
                            product_class_name_snapshot=product_state.identity.product_class_name,
                            quantity=product_state.counted_quantity,
                            bucket_code=OPERATION_BUCKET_COUNTER,
                            notes=product_state.notes,
                        )
                    )

                for class_state in prepared.computation.class_reconciliations:
                    class_row = CashSessionCloseClassReconciliation(
                        cash_session_close_id=close_row.id,
                        product_class_id=class_state.product_class_id,
                        product_class_code_snapshot=class_state.product_class_code,
                        product_class_name_snapshot=class_state.product_class_name,
                        expected_quantity=class_state.pending_quantity,
                        auto_attributed_quantity=class_state.auto_attributed_quantity,
                        attributed_quantity=class_state.final_attributed_quantity,
                        variance_quantity=class_state.discrepancy_quantity,
                        resolution_status=class_state.resolution_status,
                        notes=class_state.notes,
                    )
                    session.add(class_row)
                    session.flush()

                    for attribution in class_state.attribution_lines:
                        session.add(
                            CashSessionCloseReconciliationAttribution(
                                cash_session_close_id=close_row.id,
                                class_reconciliation_id=class_row.id,
                                product_id=attribution.identity.product_id,
                                product_code_snapshot=attribution.identity.product_code,
                                product_name_snapshot=attribution.identity.product_name,
                                product_class_id=attribution.identity.product_class_id,
                                product_class_code_snapshot=attribution.identity.product_class_code,
                                product_class_name_snapshot=attribution.identity.product_class_name,
                                attributed_quantity=attribution.attributed_quantity,
                                notes=attribution.notes,
                            )
                        )

            generated_documents: list[OperationDocument] = []
            discrepancy_payload_rows: list[dict[str, str | None]] = []
            if has_count_capture:
                for discrepancy in prepared.computation.discrepancy_resolutions:
                    generated_document = _create_discrepancy_document(
                        session,
                        discrepancy=discrepancy,
                        branch_id=active_cash_session.branch_id,
                        workstation_id=active_cash_session.workstation_id,
                        actor_id=current_user.id,
                        close_id=close_row.id,
                        committed_at=committed_at,
                    )
                    generated_documents.append(generated_document)
                    session.add(
                        CashSessionCloseDiscrepancyResolution(
                            cash_session_close_id=close_row.id,
                            product_id=discrepancy.identity.product_id,
                            product_code_snapshot=discrepancy.identity.product_code,
                            product_name_snapshot=discrepancy.identity.product_name,
                            product_class_id=discrepancy.identity.product_class_id,
                            product_class_code_snapshot=discrepancy.identity.product_class_code,
                            product_class_name_snapshot=discrepancy.identity.product_class_name,
                            expected_quantity=discrepancy.expected_quantity,
                            counted_quantity=discrepancy.counted_quantity,
                            discrepancy_quantity=discrepancy.discrepancy_quantity,
                            resolution_type=discrepancy.resolution_type,
                            reason_code=discrepancy.reason_code or "",
                            notes=discrepancy.notes,
                            generated_document_id=generated_document.id,
                        )
                    )
                    discrepancy_payload_rows.append(
                        {
                            "product_id": str(discrepancy.identity.product_id),
                            "product_code": discrepancy.identity.product_code,
                            "product_name": discrepancy.identity.product_name,
                            "discrepancy_quantity": str(discrepancy.discrepancy_quantity),
                            "resolution_type": discrepancy.resolution_type,
                            "reason_code": discrepancy.reason_code,
                            "generated_document_id": str(generated_document.id),
                        }
                    )

            for warning in prepared.warnings:
                session.add(
                    CashSessionCloseIssue(
                        cash_session_close_id=close_row.id,
                        issue_level=CASH_CLOSE_ISSUE_LEVEL_WARNING,
                        code=warning.code,
                        message=warning.message,
                    )
                )

            if has_count_capture:
                closing_snapshot = BranchCounterSnapshot(
                    branch_id=active_cash_session.branch_id,
                    source_cash_session_close_id=close_row.id,
                    snapshot_type=BRANCH_COUNTER_SNAPSHOT_TYPE_CLOSE_BASELINE,
                    captured_by_user_id=current_user.id,
                    captured_at_utc=committed_at,
                )
                session.add(closing_snapshot)
                session.flush()
                for product_state in prepared.computation.products:
                    if product_state.counted_quantity is None:
                        continue
                    session.add(
                        BranchCounterSnapshotLine(
                            snapshot_id=closing_snapshot.id,
                            product_id=product_state.identity.product_id,
                            product_code_snapshot=product_state.identity.product_code,
                            product_name_snapshot=product_state.identity.product_name,
                            product_class_id=product_state.identity.product_class_id,
                            product_class_code_snapshot=product_state.identity.product_class_code,
                            product_class_name_snapshot=product_state.identity.product_class_name,
                            quantity=product_state.counted_quantity,
                            bucket_code=OPERATION_BUCKET_COUNTER,
                        )
                    )

            pending_sale_lines = (
                session.execute(
                    select(SaleLine)
                    .select_from(SaleLine)
                    .join(Sale, Sale.id == SaleLine.sale_id)
                    .where(
                        Sale.cash_session_id == active_cash_session.id,
                        SaleLine.capture_mode == "CLASS_CAPTURE",
                        SaleLine.physical_attribution_status
                        == SALE_LINE_PHYSICAL_ATTRIBUTION_PENDING_RECONCILIATION,
                    )
                )
                .scalars()
                .all()
            )
            if has_count_capture:
                for sale_line in pending_sale_lines:
                    sale_line.physical_attribution_status = (
                        SALE_LINE_PHYSICAL_ATTRIBUTION_RECONCILED
                    )

            active_cash_session.status = CASH_SESSION_STATUS_CLOSED
            active_cash_session.closed_at = committed_at

            self._audit_recorder.record(
                session,
                actor_id=current_user.id,
                action="cash_close.committed",
                resource_type="cash_session_close",
                resource_id=str(close_row.id),
                branch_id=active_cash_session.branch_id,
                request_id=resolved_request_id,
                metadata={
                    "cash_session_id": str(active_cash_session.id),
                    "workstation_id": str(active_cash_session.workstation_id),
                    "close_mode": close_row.close_mode,
                    "counter_empty_confirmed": close_row.counter_empty_confirmed,
                    "opening_amount": str(close_row.opening_amount),
                    "expected_cash_amount": str(close_row.expected_cash_amount),
                    "counted_cash_amount": _optional_decimal_to_string(
                        close_row.counted_cash_amount
                    ),
                    "cash_variance_amount": _optional_decimal_to_string(
                        close_row.cash_variance_amount
                    ),
                    "class_reconciliation_count": len(prepared.computation.class_reconciliations),
                    "generated_discrepancy_document_count": len(generated_documents),
                    "warning_codes": [warning.code for warning in prepared.warnings],
                },
            )
            self._outbox_writer.append(
                session,
                aggregate_type="cash_session_close",
                aggregate_id=str(close_row.id),
                event_name=OUTBOX_EVENT_CASH_SESSION_CLOSED_V1,
                payload={
                    "close_id": str(close_row.id),
                    "cash_session_id": str(active_cash_session.id),
                    "branch_id": str(active_cash_session.branch_id),
                    "workstation_id": str(active_cash_session.workstation_id),
                    "closed_by_user_id": str(current_user.id),
                    "close_mode": close_row.close_mode,
                    "counter_empty_confirmed": close_row.counter_empty_confirmed,
                    "expected_cash_amount": str(close_row.expected_cash_amount),
                    "counted_cash_amount": _optional_decimal_to_string(
                        close_row.counted_cash_amount
                    ),
                    "cash_variance_amount": _optional_decimal_to_string(
                        close_row.cash_variance_amount
                    ),
                    "committed_at_utc": committed_at.isoformat(),
                },
                headers={"request_id": resolved_request_id},
            )
            if has_count_capture:
                self._outbox_writer.append(
                    session,
                    aggregate_type="cash_session_close",
                    aggregate_id=str(close_row.id),
                    event_name=OUTBOX_EVENT_CLASS_CAPTURE_RECONCILED_V1,
                    payload={
                        "close_id": str(close_row.id),
                        "cash_session_id": str(active_cash_session.id),
                        "pending_class_capture_classes_count": (
                            prepared.pending_class_capture.pending_class_capture_classes_count
                        ),
                        "pending_class_capture_total_quantity": str(
                            prepared.pending_class_capture.pending_class_capture_total_quantity
                        ),
                        "class_reconciliations": [
                            {
                                "product_class_id": str(class_state.product_class_id),
                                "product_class_code": class_state.product_class_code,
                                "pending_quantity": str(class_state.pending_quantity),
                                "final_attributed_quantity": str(
                                    class_state.final_attributed_quantity
                                ),
                                "resolution_status": class_state.resolution_status,
                            }
                            for class_state in prepared.computation.class_reconciliations
                        ],
                    },
                    headers={"request_id": resolved_request_id},
                )
            if len(discrepancy_payload_rows) > 0:
                self._outbox_writer.append(
                    session,
                    aggregate_type="cash_session_close",
                    aggregate_id=str(close_row.id),
                    event_name=OUTBOX_EVENT_CLOSE_DISCREPANCY_GENERATED_V1,
                    payload={
                        "close_id": str(close_row.id),
                        "cash_session_id": str(active_cash_session.id),
                        "generated_documents": discrepancy_payload_rows,
                    },
                    headers={"request_id": resolved_request_id},
                )

            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise CashCloseValidationError(
                "Cash close commit invariants were violated by a concurrent request."
            ) from error

        return self._query_service.get_close_detail(
            session,
            current_user=current_user,
            close_id=close_row.id,
        )


def _resolve_cash_close_context(
    session: Session,
    *,
    workstation_access: WorkstationAccessService,
    cash_session_query: CashSessionQueryService,
    current_user: AuthenticatedUser,
    workstation_code: str,
) -> CashCloseContextState:
    workstation_context = workstation_access.resolve_context(
        session,
        user_id=current_user.id,
        workstation_code=workstation_code,
    )
    current_open_cash_session = cash_session_query.get_open_session_for_workstation_code(
        session,
        workstation_code=workstation_code,
    )
    latest_workstation_session = (
        session.execute(
            select(CashSession.id, CashSession.status)
            .where(CashSession.workstation_id == workstation_context.workstation_id)
            .order_by(CashSession.opened_at.desc())
            .limit(1)
        )
        .mappings()
        .one_or_none()
    )
    other_open_session_id = session.execute(
        select(CashSession.id)
        .where(
            CashSession.user_id == current_user.id,
            CashSession.status == CASH_SESSION_STATUS_OPEN,
            CashSession.workstation_id != workstation_context.workstation_id,
        )
        .order_by(CashSession.opened_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    return CashCloseContextState(
        workstation_context=workstation_context,
        current_open_cash_session=current_open_cash_session,
        latest_workstation_session_id=(
            latest_workstation_session["id"] if latest_workstation_session is not None else None
        ),
        latest_workstation_session_status=(
            latest_workstation_session["status"] if latest_workstation_session is not None else None
        ),
        user_open_session_on_other_workstation=(
            cash_session_query.get_session_by_id(session, cash_session_id=other_open_session_id)
            if other_open_session_id is not None
            else None
        ),
    )


def _require_previewable_cash_session(
    *,
    current_user: AuthenticatedUser,
    context_state: CashCloseContextState,
) -> CashSessionView:
    current_open_cash_session = context_state.current_open_cash_session
    if current_open_cash_session is None:
        if context_state.user_open_session_on_other_workstation is not None:
            raise CashCloseConflictError(
                "No puedes cerrar desde esta caja porque tu sesion abierta esta en otra estacion."
            )
        if context_state.latest_workstation_session_status == CASH_SESSION_STATUS_CLOSED:
            raise CashCloseConflictError(
                "Esta caja ya tiene un cierre registrado para su ultima sesion abierta."
            )
        raise CashCloseConflictError("No hay una sesion de caja abierta en esta estacion.")

    if current_open_cash_session.user_id != current_user.id:
        raise CashCloseConflictError("La sesion abierta de esta caja pertenece a otro cajero.")

    if (
        current_open_cash_session.branch_id != context_state.workstation_context.branch_id
        or current_open_cash_session.workstation_id
        != context_state.workstation_context.workstation_id
    ):
        raise CashCloseConflictError(
            "La sesion abierta no coincide con la sucursal o la caja actual."
        )

    return current_open_cash_session


def _get_payment_method_catalog() -> list[CashClosePaymentMethodCatalogView]:
    return [
        CashClosePaymentMethodCatalogView(
            payment_method_code=payment_method_code,
            currency_code=CASH_CLOSE_CURRENCY_MXN,
            display_order=display_order,
            is_active=True,
            is_expected_supported=is_expected_supported,
        )
        for payment_method_code, display_order, is_expected_supported in PAYMENT_METHOD_CATALOG
    ]


def _normalize_close_mode(close_mode: str) -> str:
    normalized = close_mode.strip().upper()
    if normalized not in VALID_CASH_CLOSE_MODES:
        raise CashCloseValidationError("El modo de cierre solicitado no es valido.")
    return normalized


def _build_preview_payment_method_rows(
    *,
    close_mode: str,
    counted_payment_methods: Sequence[CashCloseCountedPaymentMethodRequest],
    expected_cash_amount: Decimal,
) -> tuple[list[CashClosePaymentMethodRowView], Decimal | None, bool]:
    catalog = _get_payment_method_catalog()
    input_amounts: dict[str, Decimal] = {}

    for count_row in counted_payment_methods:
        payment_method_code = count_row.payment_method_code.strip().upper()
        if payment_method_code in input_amounts:
            raise CashCloseValidationError(
                "No se puede repetir un metodo de pago en el conteo del cierre."
            )
        if payment_method_code not in VALID_CASH_CLOSE_PAYMENT_METHOD_CODES:
            raise CashCloseValidationError(
                f"El metodo de pago {payment_method_code} no esta disponible para el cierre."
            )
        input_amounts[payment_method_code] = _quantize_money(count_row.counted_amount)

    preview_rows: list[CashClosePaymentMethodRowView] = []
    counted_cash_amount: Decimal | None = ZERO_MONEY
    has_counted_monetary_input = len(input_amounts) > 0

    for catalog_row in catalog:
        counted_amount = input_amounts.get(catalog_row.payment_method_code, ZERO_MONEY)
        expected_amount = (
            expected_cash_amount
            if catalog_row.payment_method_code in EXPECTED_CASH_CLOSE_PAYMENT_METHOD_CODES
            else None
        )
        variance_amount = (
            _quantize_money(counted_amount - expected_amount)
            if expected_amount is not None
            else None
        )
        preview_rows.append(
            CashClosePaymentMethodRowView(
                payment_method_code=catalog_row.payment_method_code,
                currency_code=catalog_row.currency_code,
                display_order=catalog_row.display_order,
                counted_amount=counted_amount,
                expected_amount=expected_amount,
                variance_amount=variance_amount,
                is_expected_supported=catalog_row.is_expected_supported,
            )
        )
        if catalog_row.payment_method_code == CASH_CLOSE_PAYMENT_METHOD_CASH:
            counted_cash_amount = counted_amount

    return preview_rows, counted_cash_amount, has_counted_monetary_input


def _get_financial_summary(
    session: Session,
    *,
    cash_session_id: uuid.UUID,
    opening_amount: Decimal,
) -> CashCloseFinancialSummary:
    records = (
        session.execute(
            select(
                CashMovement.movement_type,
                CashMovement.direction,
                CashMovement.currency_code,
                func.count(CashMovement.id).label("movement_count"),
                func.coalesce(func.sum(CashMovement.amount), 0).label("total_amount"),
            )
            .where(CashMovement.cash_session_id == cash_session_id)
            .group_by(
                CashMovement.movement_type,
                CashMovement.direction,
                CashMovement.currency_code,
            )
            .order_by(CashMovement.direction.asc(), CashMovement.movement_type.asc())
        )
        .mappings()
        .all()
    )

    total_cash_in = ZERO_MONEY
    total_cash_out = ZERO_MONEY
    movement_breakdown: list[CashCloseMovementBreakdownView] = []
    currency_code = CASH_CLOSE_CURRENCY_MXN

    for record in records:
        amount = _quantize_money(Decimal(record["total_amount"]))
        currency_code = record["currency_code"]
        movement_breakdown.append(
            CashCloseMovementBreakdownView(
                movement_type=record["movement_type"],
                direction=record["direction"],
                currency_code=record["currency_code"],
                movement_count=int(record["movement_count"]),
                total_amount=amount,
            )
        )
        if record["direction"] == CASH_MOVEMENT_DIRECTION_IN:
            total_cash_in += amount
        elif record["direction"] == CASH_MOVEMENT_DIRECTION_OUT:
            total_cash_out += amount

    return CashCloseFinancialSummary(
        currency_code=currency_code,
        total_cash_in=_quantize_money(total_cash_in),
        total_cash_out=_quantize_money(total_cash_out),
        expected_cash_amount=_quantize_money(opening_amount + total_cash_in - total_cash_out),
        movement_breakdown=movement_breakdown,
    )


def _get_pending_class_capture_rows(
    session: Session,
    *,
    cash_session_id: uuid.UUID | None,
) -> list[PendingClassCaptureRow]:
    if cash_session_id is None:
        return []

    records = (
        session.execute(
            select(
                ProductClass.id,
                ProductClass.code,
                ProductClass.name,
                ProductClass.display_order,
                func.coalesce(func.sum(SaleLine.quantity), 0).label("pending_quantity"),
            )
            .select_from(SaleLine)
            .join(Sale, Sale.id == SaleLine.sale_id)
            .join(ProductClass, ProductClass.id == SaleLine.product_class_id)
            .where(
                Sale.cash_session_id == cash_session_id,
                SaleLine.capture_mode == "CLASS_CAPTURE",
                SaleLine.physical_attribution_status
                == SALE_LINE_PHYSICAL_ATTRIBUTION_PENDING_RECONCILIATION,
            )
            .group_by(
                ProductClass.id,
                ProductClass.code,
                ProductClass.name,
                ProductClass.display_order,
            )
            .order_by(ProductClass.display_order.asc(), ProductClass.name.asc())
        )
        .mappings()
        .all()
    )

    return [
        PendingClassCaptureRow(
            product_class_id=record["id"],
            product_class_code=record["code"],
            product_class_name=record["name"],
            display_order=record["display_order"],
            pending_quantity=_quantize_quantity(Decimal(record["pending_quantity"])),
        )
        for record in records
    ]


def _build_pending_class_capture_summary(
    rows: Sequence[PendingClassCaptureRow],
) -> CashClosePendingClassCaptureSummaryView:
    total_quantity = _quantize_quantity(sum((row.pending_quantity for row in rows), ZERO_QUANTITY))
    return CashClosePendingClassCaptureSummaryView(
        has_pending_class_capture=total_quantity > 0,
        pending_class_capture_classes_count=len(rows),
        pending_class_capture_total_quantity=total_quantity,
    )


def _get_baseline_snapshot_summary(
    session: Session,
    *,
    branch_id: uuid.UUID,
) -> CashCloseBaselineSnapshotSummaryView:
    record = (
        session.execute(
            select(
                BranchCounterSnapshot.id,
                BranchCounterSnapshot.snapshot_type,
                BranchCounterSnapshot.captured_at_utc,
                BranchCounterSnapshot.source_cash_session_close_id,
            )
            .select_from(BranchCounterSnapshot)
            .outerjoin(
                CashSessionClose,
                CashSessionClose.id == BranchCounterSnapshot.source_cash_session_close_id,
            )
            .where(
                BranchCounterSnapshot.branch_id == branch_id,
                BranchCounterSnapshot.snapshot_type == BRANCH_COUNTER_SNAPSHOT_TYPE_CLOSE_BASELINE,
                or_(
                    BranchCounterSnapshot.source_cash_session_close_id.is_(None),
                    CashSessionClose.status == CASH_CLOSE_STATUS_COMMITTED,
                ),
            )
            .order_by(BranchCounterSnapshot.captured_at_utc.desc())
            .limit(1)
        )
        .mappings()
        .one_or_none()
    )

    if record is None:
        return CashCloseBaselineSnapshotSummaryView(
            is_available=False,
            latest_snapshot_id=None,
            snapshot_type=None,
            captured_at_utc=None,
            source_cash_session_close_id=None,
            is_first_controlled_close=True,
        )

    return CashCloseBaselineSnapshotSummaryView(
        is_available=True,
        latest_snapshot_id=record["id"],
        snapshot_type=record["snapshot_type"],
        captured_at_utc=record["captured_at_utc"],
        source_cash_session_close_id=record["source_cash_session_close_id"],
        is_first_controlled_close=False,
    )


def _build_context_blockers(
    *,
    current_user: AuthenticatedUser,
    context_state: CashCloseContextState,
    baseline_snapshot: CashCloseBaselineSnapshotSummaryView,
) -> list[CashCloseIssueView]:
    blockers: list[CashCloseIssueView] = []

    current_open_cash_session = context_state.current_open_cash_session
    if current_open_cash_session is None:
        if context_state.user_open_session_on_other_workstation is not None:
            _append_issue(
                blockers,
                code=CASH_CLOSE_BLOCKER_INCONSISTENT_SESSION_CONTEXT,
                message=(
                    "No puedes cerrar desde esta caja porque tu sesion abierta esta en otra "
                    "estacion."
                ),
            )
        if context_state.latest_workstation_session_status == CASH_SESSION_STATUS_CLOSED:
            _append_issue(
                blockers,
                code=CASH_CLOSE_BLOCKER_SESSION_ALREADY_CLOSED,
                message=("Esta caja ya tiene un cierre registrado para su ultima sesion abierta."),
            )
        else:
            _append_issue(
                blockers,
                code=CASH_CLOSE_BLOCKER_NO_ACTIVE_OPEN_CASH_SESSION,
                message="No hay una sesion de caja abierta en esta estacion.",
            )
    else:
        if current_open_cash_session.user_id != current_user.id:
            _append_issue(
                blockers,
                code=CASH_CLOSE_BLOCKER_INCONSISTENT_SESSION_CONTEXT,
                message="La sesion abierta de esta caja pertenece a otro cajero.",
            )
        elif (
            current_open_cash_session.branch_id != context_state.workstation_context.branch_id
            or current_open_cash_session.workstation_id
            != context_state.workstation_context.workstation_id
        ):
            _append_issue(
                blockers,
                code=CASH_CLOSE_BLOCKER_INCONSISTENT_SESSION_CONTEXT,
                message="La sesion abierta no coincide con la sucursal o la caja actual.",
            )

    return blockers


def _build_warnings(
    session: Session,
    *,
    context_state: CashCloseContextState,
    counted_cash_amount: Decimal | None,
    cash_variance_amount: Decimal | None,
) -> list[CashCloseIssueView]:
    warnings: list[CashCloseIssueView] = []
    branch_id = context_state.workstation_context.branch_id

    pending_inbound_count = session.execute(
        select(func.count(OperationDocument.id)).where(
            OperationDocument.document_type == OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT,
            OperationDocument.destination_branch_id == branch_id,
            OperationDocument.status == OPERATION_DOCUMENT_STATUS_IN_TRANSIT,
        )
    ).scalar_one()
    if pending_inbound_count > 0:
        warnings.append(
            CashCloseIssueView(
                code=CASH_CLOSE_WARNING_PENDING_INBOUND_TRANSFERS,
                message=(
                    f"Hay {pending_inbound_count} envio(s) pendientes de recibir en esta sucursal."
                ),
            )
        )

    outbound_in_transit_count = session.execute(
        select(func.count(OperationDocument.id)).where(
            OperationDocument.document_type == OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT,
            OperationDocument.source_branch_id == branch_id,
            OperationDocument.status == OPERATION_DOCUMENT_STATUS_IN_TRANSIT,
        )
    ).scalar_one()
    if outbound_in_transit_count > 0:
        warnings.append(
            CashCloseIssueView(
                code=CASH_CLOSE_WARNING_OUTBOUND_TRANSFERS_IN_TRANSIT,
                message=(
                    f"Hay {outbound_in_transit_count} envio(s) saliendo de esta sucursal que "
                    "siguen en transito."
                ),
            )
        )

    if context_state.current_open_cash_session is not None:
        session_duration = datetime.now(tz=UTC) - context_state.current_open_cash_session.opened_at
        if session_duration >= timedelta(hours=LONG_SESSION_DURATION_WARNING_HOURS):
            warnings.append(
                CashCloseIssueView(
                    code=CASH_CLOSE_WARNING_LONG_SESSION_DURATION,
                    message=(
                        "La sesion lleva abierta mas tiempo de lo habitual. Conviene revisar "
                        "el cierre con atencion."
                    ),
                )
            )

    if (
        counted_cash_amount is not None
        and cash_variance_amount is not None
        and abs(cash_variance_amount) >= LARGE_CASH_VARIANCE_WARNING_THRESHOLD
    ):
        warnings.append(
            CashCloseIssueView(
                code=CASH_CLOSE_WARNING_LARGE_CASH_VARIANCE,
                message=(
                    "La diferencia entre el efectivo esperado y el contado es mayor a la "
                    "tolerancia de revision."
                ),
            )
        )

    return warnings


def _compute_reconciliation(
    session: Session,
    *,
    cash_session: CashSessionView,
    workstation_id: uuid.UUID,
    branch_id: uuid.UUID,
    counted_product_lines: Sequence[CashCloseCountedProductLineRequest],
    counter_empty_confirmed: bool,
    manual_reconciliation_overrides: Sequence[CashCloseManualReconciliationOverrideRequest],
    discrepancy_resolutions: Sequence[CashCloseDiscrepancyResolutionRequest],
) -> CashCloseReconciliationComputation:
    blockers: list[CashCloseIssueView] = []
    pending_rows = _get_pending_class_capture_rows(session, cash_session_id=cash_session.id)
    counted_inputs = _parse_counted_product_inputs(counted_product_lines)
    manual_inputs = _parse_manual_override_inputs(manual_reconciliation_overrides)
    discrepancy_inputs = _parse_discrepancy_resolution_inputs(discrepancy_resolutions)

    baseline_snapshot_id = _get_latest_baseline_snapshot_id(session, branch_id=branch_id)
    baseline_quantities = (
        _get_snapshot_counter_quantities(session, snapshot_id=baseline_snapshot_id)
        if baseline_snapshot_id is not None
        else {}
    )
    counter_transfer_quantities = _get_counter_transfer_quantities(
        session,
        workstation_id=workstation_id,
        opened_at=cash_session.opened_at,
    )
    counter_waste_quantities = _get_counter_waste_quantities(
        session,
        workstation_id=workstation_id,
        opened_at=cash_session.opened_at,
    )
    correction_deltas = _get_counter_correction_deltas(
        session,
        workstation_id=workstation_id,
        opened_at=cash_session.opened_at,
    )
    counter_return_quantities = _get_counter_return_quantities(
        session,
        cash_session_id=cash_session.id,
    )
    direct_sale_quantities = _get_product_direct_sale_quantities(
        session,
        cash_session_id=cash_session.id,
    )

    pending_class_ids = {row.product_class_id for row in pending_rows}
    pending_class_product_ids = _get_active_product_ids_for_classes(
        session,
        product_class_ids=pending_class_ids,
    )
    relevant_product_ids = (
        set(baseline_quantities)
        | set(counter_transfer_quantities)
        | set(counter_return_quantities)
        | set(counter_waste_quantities)
        | set(correction_deltas)
        | set(direct_sale_quantities)
        | pending_class_product_ids
        | set(counted_inputs)
    )
    override_product_ids = {
        product_id
        for override in manual_inputs.values()
        for product_id, _ in override.attribution_lines
    }
    resolution_product_ids = set(discrepancy_inputs)
    identities = _resolve_product_identities(
        session,
        product_ids=relevant_product_ids | override_product_ids | resolution_product_ids,
    )
    relevant_identities = _sort_product_identities(
        [identities[product_id] for product_id in relevant_product_ids if product_id in identities]
    )
    if counter_empty_confirmed and len(counted_inputs) == 0:
        counted_inputs = {
            product_id: CountedProductInput(counted_quantity=ZERO_QUANTITY, notes=None)
            for product_id in relevant_product_ids
        }

    expected_before_map: dict[uuid.UUID, Decimal] = defaultdict(lambda: ZERO_QUANTITY)
    for source in (
        baseline_quantities,
        counter_transfer_quantities,
        counter_return_quantities,
        correction_deltas,
    ):
        for product_id, quantity in source.items():
            expected_before_map[product_id] = _quantize_quantity(
                expected_before_map[product_id] + quantity
            )
    for source in (counter_waste_quantities, direct_sale_quantities):
        for product_id, quantity in source.items():
            expected_before_map[product_id] = _quantize_quantity(
                expected_before_map[product_id] - quantity
            )
    for product_id in relevant_product_ids:
        expected_before_map.setdefault(product_id, ZERO_QUANTITY)

    if any(quantity < 0 for quantity in expected_before_map.values()):
        _append_issue(
            blockers,
            code=CASH_CLOSE_BLOCKER_INTERNAL_INTEGRITY_MISMATCH,
            message=("La base esperada del mostrador quedo en negativo para uno o mas productos."),
        )

    counted_complete = len(relevant_product_ids) == 0 or len(counted_inputs) > 0

    auto_candidate_map: dict[uuid.UUID, Decimal] = {}
    if counted_complete:
        for product_id in relevant_product_ids:
            counted_quantity = counted_inputs.get(
                product_id,
                CountedProductInput(counted_quantity=ZERO_QUANTITY, notes=None),
            ).counted_quantity
            auto_candidate_map[product_id] = _quantize_quantity(
                max(expected_before_map[product_id] - counted_quantity, ZERO_QUANTITY)
            )

    class_reconciliations, final_attribution_map, class_blockers = _resolve_class_reconciliations(
        identities=identities,
        pending_rows=pending_rows,
        counted_complete=counted_complete,
        auto_candidate_map=auto_candidate_map,
        manual_inputs=manual_inputs,
    )
    blockers = _merge_issues(blockers, class_blockers)
    can_resolve_discrepancies = counted_complete and len(class_blockers) == 0

    products, resolved_discrepancies, discrepancy_blockers = _resolve_product_discrepancies(
        identities=relevant_identities,
        expected_before_map=expected_before_map,
        counted_inputs=counted_inputs,
        final_attribution_map=final_attribution_map,
        discrepancy_inputs=discrepancy_inputs,
        can_resolve_discrepancies=can_resolve_discrepancies,
    )
    blockers = _merge_issues(blockers, discrepancy_blockers)
    counter_class_availability = _build_counter_class_availability(
        identities=relevant_identities,
        expected_before_map=expected_before_map,
        pending_rows=pending_rows,
    )

    return CashCloseReconciliationComputation(
        products=products,
        counter_class_availability=counter_class_availability,
        class_reconciliations=class_reconciliations,
        discrepancy_resolutions=resolved_discrepancies,
        blockers=blockers,
    )


def _resolve_class_reconciliations(
    *,
    identities: dict[uuid.UUID, ProductIdentity],
    pending_rows: Sequence[PendingClassCaptureRow],
    counted_complete: bool,
    auto_candidate_map: dict[uuid.UUID, Decimal],
    manual_inputs: dict[uuid.UUID, ManualOverrideInput],
) -> tuple[
    list[ResolvedClassReconciliation],
    dict[uuid.UUID, Decimal],
    list[CashCloseIssueView],
]:
    blockers: list[CashCloseIssueView] = []
    class_reconciliations: list[ResolvedClassReconciliation] = []
    final_attribution_map: dict[uuid.UUID, Decimal] = defaultdict(lambda: ZERO_QUANTITY)

    for pending_row in pending_rows:
        class_product_identities = _sort_product_identities(
            [
                identity
                for identity in identities.values()
                if identity.product_class_id == pending_row.product_class_id
            ]
        )
        auto_lines: list[ResolvedAttributionLine] = []
        remaining_auto_quantity = pending_row.pending_quantity
        for identity in class_product_identities:
            if remaining_auto_quantity <= 0:
                break
            candidate_quantity = auto_candidate_map.get(identity.product_id, ZERO_QUANTITY)
            if candidate_quantity <= 0:
                continue
            attributed_quantity = _quantize_quantity(
                min(candidate_quantity, remaining_auto_quantity)
            )
            if attributed_quantity <= 0:
                continue
            auto_lines.append(
                ResolvedAttributionLine(
                    identity=identity,
                    attributed_quantity=attributed_quantity,
                    attribution_source="AUTO",
                    notes=None,
                )
            )
            remaining_auto_quantity = _quantize_quantity(
                remaining_auto_quantity - attributed_quantity
            )
        auto_attributed_quantity = _quantize_quantity(
            sum((line.attributed_quantity for line in auto_lines), ZERO_QUANTITY)
        )
        discrepancy_quantity = _quantize_quantity(
            pending_row.pending_quantity - auto_attributed_quantity
        )
        resolution_status = CASH_CLOSE_CLASS_RESOLUTION_STATUS_COUNT_REQUIRED
        attribution_lines: list[ResolvedAttributionLine] = []
        final_attributed_quantity = ZERO_QUANTITY
        notes: str | None = None
        override_input = manual_inputs.get(pending_row.product_class_id)

        if not counted_complete:
            resolution_status = CASH_CLOSE_CLASS_RESOLUTION_STATUS_COUNT_REQUIRED
        elif override_input is not None:
            override_result = _resolve_manual_override_lines(
                identities=identities,
                pending_row=pending_row,
                override_input=override_input,
            )
            if override_result is None:
                _append_issue(
                    blockers,
                    code=CASH_CLOSE_BLOCKER_INVALID_MANUAL_RECONCILIATION_OVERRIDE,
                    message=(
                        f"La distribucion manual para la clase "
                        f"{pending_row.product_class_name} no es valida."
                    ),
                )
                resolution_status = CASH_CLOSE_CLASS_RESOLUTION_STATUS_UNRESOLVED
                notes = override_input.notes
            else:
                attribution_lines = override_result
                final_attributed_quantity = _quantize_quantity(
                    sum((line.attributed_quantity for line in attribution_lines), ZERO_QUANTITY)
                )
                resolution_status = CASH_CLOSE_CLASS_RESOLUTION_STATUS_MANUAL_RESOLVED
                notes = override_input.notes
        else:
            attribution_lines = auto_lines
            final_attributed_quantity = auto_attributed_quantity
            if auto_attributed_quantity == pending_row.pending_quantity:
                resolution_status = CASH_CLOSE_CLASS_RESOLUTION_STATUS_AUTO_RESOLVED
            else:
                _append_issue(
                    blockers,
                    code=CASH_CLOSE_BLOCKER_UNRESOLVED_CLASS_CAPTURE_MISMATCH,
                    message=(
                        "Hay ventas por clase que todavia no estan repartidas por producto exacto."
                    ),
                )
                resolution_status = CASH_CLOSE_CLASS_RESOLUTION_STATUS_UNRESOLVED

        if resolution_status in {
            CASH_CLOSE_CLASS_RESOLUTION_STATUS_AUTO_RESOLVED,
            CASH_CLOSE_CLASS_RESOLUTION_STATUS_MANUAL_RESOLVED,
        }:
            for line in attribution_lines:
                final_attribution_map[line.identity.product_id] = _quantize_quantity(
                    final_attribution_map[line.identity.product_id] + line.attributed_quantity
                )

        class_reconciliations.append(
            ResolvedClassReconciliation(
                product_class_id=pending_row.product_class_id,
                product_class_code=pending_row.product_class_code,
                product_class_name=pending_row.product_class_name,
                pending_quantity=pending_row.pending_quantity,
                auto_attributed_quantity=auto_attributed_quantity,
                final_attributed_quantity=final_attributed_quantity,
                discrepancy_quantity=discrepancy_quantity,
                resolution_status=resolution_status,
                attribution_lines=attribution_lines,
                notes=notes,
            )
        )

    return class_reconciliations, dict(final_attribution_map), blockers


def _resolve_product_discrepancies(
    *,
    identities: Sequence[ProductIdentity],
    expected_before_map: dict[uuid.UUID, Decimal],
    counted_inputs: dict[uuid.UUID, CountedProductInput],
    final_attribution_map: dict[uuid.UUID, Decimal],
    discrepancy_inputs: dict[uuid.UUID, DiscrepancyResolutionInput],
    can_resolve_discrepancies: bool,
) -> tuple[list[ResolvedProductState], list[ResolvedDiscrepancy], list[CashCloseIssueView]]:
    blockers: list[CashCloseIssueView] = []
    products: list[ResolvedProductState] = []
    required_discrepancies: list[ResolvedDiscrepancy] = []

    for identity in identities:
        counted_input = counted_inputs.get(identity.product_id)
        counted_quantity = counted_input.counted_quantity if counted_input is not None else None
        final_expected_quantity: Decimal | None = None
        discrepancy_quantity: Decimal | None = None

        if counted_quantity is not None and can_resolve_discrepancies:
            final_expected_quantity = _quantize_quantity(
                expected_before_map[identity.product_id]
                - final_attribution_map.get(identity.product_id, ZERO_QUANTITY)
            )
            discrepancy_quantity = _quantize_quantity(counted_quantity - final_expected_quantity)
            if final_expected_quantity < 0:
                _append_issue(
                    blockers,
                    code=CASH_CLOSE_BLOCKER_INTERNAL_INTEGRITY_MISMATCH,
                    message=(
                        "La cantidad final esperada quedo en negativo para uno o mas "
                        "productos despues de la conciliacion."
                    ),
                )
            if discrepancy_quantity != 0:
                required_discrepancies.append(
                    ResolvedDiscrepancy(
                        identity=identity,
                        expected_quantity=final_expected_quantity,
                        counted_quantity=counted_quantity,
                        discrepancy_quantity=discrepancy_quantity,
                        resolution_type=(
                            CASH_CLOSE_DISCREPANCY_RESOLUTION_TYPE_CLOSE_COUNTER_ADJUSTMENT
                            if discrepancy_quantity > 0
                            else CASH_CLOSE_DISCREPANCY_RESOLUTION_TYPE_CLOSE_WASTE_ADJUSTMENT
                        ),
                        reason_code=None,
                        notes=None,
                    )
                )

        products.append(
            ResolvedProductState(
                identity=identity,
                expected_quantity_before_deferred_attr=expected_before_map[identity.product_id],
                counted_quantity=counted_quantity,
                final_expected_quantity=final_expected_quantity,
                discrepancy_quantity=discrepancy_quantity,
                notes=counted_input.notes if counted_input is not None else None,
            )
        )

    resolved_discrepancies: list[ResolvedDiscrepancy] = []
    if not can_resolve_discrepancies:
        return products, resolved_discrepancies, blockers

    required_product_ids = {item.identity.product_id for item in required_discrepancies}
    extra_resolution_ids = set(discrepancy_inputs) - required_product_ids
    if len(extra_resolution_ids) > 0:
        _append_issue(
            blockers,
            code=CASH_CLOSE_BLOCKER_INVALID_DISCREPANCY_RESOLUTION,
            message=(
                "Se capturaron resoluciones para productos que no tienen diferencia en el cierre."
            ),
        )

    for required in required_discrepancies:
        provided = discrepancy_inputs.get(required.identity.product_id)
        if provided is None:
            resolved_discrepancies.append(
                ResolvedDiscrepancy(
                    identity=required.identity,
                    expected_quantity=required.expected_quantity,
                    counted_quantity=required.counted_quantity,
                    discrepancy_quantity=required.discrepancy_quantity,
                    resolution_type=required.resolution_type,
                    reason_code=_resolve_default_discrepancy_reason_code(
                        required.discrepancy_quantity
                    ),
                    notes=None,
                )
            )
            continue
        if (
            provided.resolution_type not in VALID_CASH_CLOSE_DISCREPANCY_RESOLUTION_TYPES
            or provided.reason_code not in VALID_CASH_CLOSE_DISCREPANCY_REASON_CODES
            or provided.quantity != abs(required.discrepancy_quantity)
            or provided.resolution_type != required.resolution_type
        ):
            _append_issue(
                blockers,
                code=CASH_CLOSE_BLOCKER_INVALID_DISCREPANCY_RESOLUTION,
                message=(
                    f"La resolucion capturada para {required.identity.product_name} no "
                    "coincide con la diferencia final detectada."
                ),
            )
            resolved_discrepancies.append(required)
            continue

        resolved_discrepancies.append(
            ResolvedDiscrepancy(
                identity=required.identity,
                expected_quantity=required.expected_quantity,
                counted_quantity=required.counted_quantity,
                discrepancy_quantity=required.discrepancy_quantity,
                resolution_type=required.resolution_type,
                reason_code=provided.reason_code,
                notes=provided.notes,
            )
        )

    return products, resolved_discrepancies, blockers


def _resolve_default_discrepancy_reason_code(discrepancy_quantity: Decimal) -> str:
    if discrepancy_quantity > 0:
        return CASH_CLOSE_DISCREPANCY_REASON_COUNTER_OVERAGE

    return CASH_CLOSE_DISCREPANCY_REASON_COUNTER_SHORTAGE


def _parse_counted_product_inputs(
    counted_product_lines: Sequence[CashCloseCountedProductLineRequest],
) -> dict[uuid.UUID, CountedProductInput]:
    inputs: dict[uuid.UUID, CountedProductInput] = {}
    for line in counted_product_lines:
        if line.product_id in inputs:
            raise CashCloseValidationError(
                "No se puede repetir el mismo producto dentro del conteo final."
            )
        inputs[line.product_id] = CountedProductInput(
            counted_quantity=_quantize_quantity(line.counted_quantity),
            notes=line.notes,
        )
    return inputs


def _parse_manual_override_inputs(
    overrides: Sequence[CashCloseManualReconciliationOverrideRequest],
) -> dict[uuid.UUID, ManualOverrideInput]:
    inputs: dict[uuid.UUID, ManualOverrideInput] = {}
    for override in overrides:
        if override.product_class_id in inputs:
            raise CashCloseValidationError(
                "No se puede repetir una misma clase en la distribucion manual."
            )
        seen_product_ids: set[uuid.UUID] = set()
        attribution_lines: list[tuple[uuid.UUID, Decimal]] = []
        for line in override.attribution_lines:
            if line.product_id in seen_product_ids:
                raise CashCloseValidationError(
                    "No se puede repetir un producto dentro de la misma distribucion manual."
                )
            seen_product_ids.add(line.product_id)
            attribution_lines.append(
                (line.product_id, _quantize_quantity(line.attributed_quantity))
            )
        inputs[override.product_class_id] = ManualOverrideInput(
            product_class_id=override.product_class_id,
            attribution_lines=attribution_lines,
            notes=override.notes,
        )
    return inputs


def _parse_discrepancy_resolution_inputs(
    resolutions: Sequence[CashCloseDiscrepancyResolutionRequest],
) -> dict[uuid.UUID, DiscrepancyResolutionInput]:
    inputs: dict[uuid.UUID, DiscrepancyResolutionInput] = {}
    for resolution in resolutions:
        if resolution.product_id in inputs:
            raise CashCloseValidationError(
                "No se puede repetir un producto dentro de las resoluciones de diferencia."
            )
        inputs[resolution.product_id] = DiscrepancyResolutionInput(
            product_id=resolution.product_id,
            resolution_type=resolution.resolution_type.strip(),
            reason_code=resolution.reason_code.strip(),
            quantity=_quantize_quantity(resolution.quantity),
            notes=resolution.notes,
        )
    return inputs


def _get_latest_baseline_snapshot_id(
    session: Session,
    *,
    branch_id: uuid.UUID,
) -> uuid.UUID | None:
    return session.execute(
        select(BranchCounterSnapshot.id)
        .outerjoin(
            CashSessionClose,
            CashSessionClose.id == BranchCounterSnapshot.source_cash_session_close_id,
        )
        .where(
            BranchCounterSnapshot.branch_id == branch_id,
            BranchCounterSnapshot.snapshot_type == BRANCH_COUNTER_SNAPSHOT_TYPE_CLOSE_BASELINE,
            or_(
                BranchCounterSnapshot.source_cash_session_close_id.is_(None),
                CashSessionClose.status == CASH_CLOSE_STATUS_COMMITTED,
            ),
        )
        .order_by(BranchCounterSnapshot.captured_at_utc.desc())
        .limit(1)
    ).scalar_one_or_none()


def _get_snapshot_counter_quantities(
    session: Session,
    *,
    snapshot_id: uuid.UUID,
) -> dict[uuid.UUID, Decimal]:
    records = (
        session.execute(
            select(
                BranchCounterSnapshotLine.product_id,
                BranchCounterSnapshotLine.quantity,
            ).where(
                BranchCounterSnapshotLine.snapshot_id == snapshot_id,
                BranchCounterSnapshotLine.bucket_code == OPERATION_BUCKET_COUNTER,
            )
        )
        .mappings()
        .all()
    )
    return {record["product_id"]: _quantize_quantity(record["quantity"]) for record in records}


def _get_counter_transfer_quantities(
    session: Session,
    *,
    workstation_id: uuid.UUID,
    opened_at: datetime,
) -> dict[uuid.UUID, Decimal]:
    return _get_operation_line_totals(
        session,
        workstation_id=workstation_id,
        opened_at=opened_at,
        document_type=OPERATION_DOCUMENT_TYPE_COUNTER_TRANSFER,
        source_bucket_code=None,
    )


def _get_counter_waste_quantities(
    session: Session,
    *,
    workstation_id: uuid.UUID,
    opened_at: datetime,
) -> dict[uuid.UUID, Decimal]:
    return _get_operation_line_totals(
        session,
        workstation_id=workstation_id,
        opened_at=opened_at,
        document_type=OPERATION_DOCUMENT_TYPE_WASTE_RECORD,
        source_bucket_code=OPERATION_BUCKET_COUNTER,
    )


def _get_operation_line_totals(
    session: Session,
    *,
    workstation_id: uuid.UUID,
    opened_at: datetime,
    document_type: str,
    source_bucket_code: str | None,
) -> dict[uuid.UUID, Decimal]:
    statement = (
        select(
            OperationDocumentLine.product_id,
            func.coalesce(func.sum(OperationDocumentLine.quantity), 0).label("quantity"),
        )
        .select_from(OperationDocumentLine)
        .join(
            OperationDocument,
            OperationDocument.id == OperationDocumentLine.operation_document_id,
        )
        .where(
            OperationDocument.workstation_id == workstation_id,
            OperationDocument.document_type == document_type,
            OperationDocument.status == OPERATION_DOCUMENT_STATUS_COMMITTED,
            OperationDocument.committed_at_utc >= opened_at,
        )
        .group_by(OperationDocumentLine.product_id)
    )
    if source_bucket_code is not None:
        statement = statement.where(OperationDocument.source_bucket_code == source_bucket_code)

    records = session.execute(statement).mappings().all()
    return {
        record["product_id"]: _quantize_quantity(Decimal(record["quantity"])) for record in records
    }


def _get_counter_correction_deltas(
    session: Session,
    *,
    workstation_id: uuid.UUID,
    opened_at: datetime,
) -> dict[uuid.UUID, Decimal]:
    target_document = OperationDocument.__table__.alias("target_document")
    records = (
        session.execute(
            select(
                CorrectionDocumentLine.product_id,
                CorrectionDocumentLine.delta_quantity,
                target_document.c.document_type.label("target_document_type"),
                target_document.c.source_bucket_code.label("target_source_bucket_code"),
            )
            .select_from(CorrectionDocumentLine)
            .join(
                CorrectionDocument,
                CorrectionDocument.id == CorrectionDocumentLine.correction_document_id,
            )
            .join(target_document, target_document.c.id == CorrectionDocument.target_document_id)
            .where(
                CorrectionDocument.workstation_id == workstation_id,
                CorrectionDocument.status == CORRECTION_STATUS_COMMITTED,
                CorrectionDocument.committed_at_utc >= opened_at,
            )
        )
        .mappings()
        .all()
    )
    totals: dict[uuid.UUID, Decimal] = defaultdict(lambda: ZERO_QUANTITY)
    for record in records:
        delta_quantity = _quantize_quantity(record["delta_quantity"])
        if record["target_document_type"] == OPERATION_DOCUMENT_TYPE_COUNTER_TRANSFER:
            totals[record["product_id"]] = _quantize_quantity(
                totals[record["product_id"]] + delta_quantity
            )
        elif (
            record["target_document_type"] == OPERATION_DOCUMENT_TYPE_WASTE_RECORD
            and record["target_source_bucket_code"] == OPERATION_BUCKET_COUNTER
        ):
            totals[record["product_id"]] = _quantize_quantity(
                totals[record["product_id"]] - delta_quantity
            )
    return dict(totals)


def _get_counter_return_quantities(
    session: Session,
    *,
    cash_session_id: uuid.UUID,
) -> dict[uuid.UUID, Decimal]:
    records = (
        session.execute(
            select(
                SaleReturnLine.returned_product_id.label("product_id"),
                func.coalesce(func.sum(SaleReturnLine.returned_quantity), 0).label("quantity"),
            )
            .select_from(SaleReturnLine)
            .join(SaleReturn, SaleReturn.id == SaleReturnLine.sale_return_id)
            .where(
                SaleReturn.cash_session_id == cash_session_id,
                SaleReturn.status == RETURN_STATUS_COMMITTED,
                SaleReturnLine.disposition_code == RETURN_DISPOSITION_RESTOCK_COUNTER,
            )
            .group_by(SaleReturnLine.returned_product_id)
        )
        .mappings()
        .all()
    )
    return {
        record["product_id"]: _quantize_quantity(Decimal(record["quantity"]))
        for record in records
        if record["product_id"] is not None
    }


def _get_product_direct_sale_quantities(
    session: Session,
    *,
    cash_session_id: uuid.UUID,
) -> dict[uuid.UUID, Decimal]:
    records = (
        session.execute(
            select(
                SaleLine.product_id,
                func.coalesce(func.sum(SaleLine.quantity), 0).label("quantity"),
            )
            .select_from(SaleLine)
            .join(Sale, Sale.id == SaleLine.sale_id)
            .where(
                Sale.cash_session_id == cash_session_id,
                SaleLine.capture_mode == "PRODUCT_DIRECT",
                SaleLine.product_id.is_not(None),
            )
            .group_by(SaleLine.product_id)
        )
        .mappings()
        .all()
    )
    return {
        record["product_id"]: _quantize_quantity(Decimal(record["quantity"]))
        for record in records
        if record["product_id"] is not None
    }


def _get_active_product_ids_for_classes(
    session: Session,
    *,
    product_class_ids: set[uuid.UUID],
) -> set[uuid.UUID]:
    if len(product_class_ids) == 0:
        return set()
    records = session.execute(
        select(Product.id).where(
            Product.product_class_id.in_(product_class_ids),
            Product.is_active.is_(True),
            Product.is_sellable.is_(True),
        )
    ).all()
    return {record[0] for record in records}


def _build_counter_class_availability(
    *,
    identities: Sequence[ProductIdentity],
    expected_before_map: Mapping[uuid.UUID, Decimal],
    pending_rows: Sequence[PendingClassCaptureRow],
) -> list[ResolvedCounterClassAvailability]:
    expected_totals: dict[uuid.UUID, Decimal] = defaultdict(lambda: ZERO_QUANTITY)
    pending_totals: dict[uuid.UUID, Decimal] = {
        row.product_class_id: row.pending_quantity for row in pending_rows
    }
    metadata: dict[uuid.UUID, tuple[str, str, int]] = {}

    for identity in identities:
        expected_totals[identity.product_class_id] = _quantize_quantity(
            expected_totals[identity.product_class_id]
            + expected_before_map.get(identity.product_id, ZERO_QUANTITY)
        )
        metadata.setdefault(
            identity.product_class_id,
            (
                identity.product_class_code,
                identity.product_class_name,
                identity.class_display_order,
            ),
        )

    for row in pending_rows:
        metadata.setdefault(
            row.product_class_id,
            (row.product_class_code, row.product_class_name, row.display_order),
        )

    rows: list[ResolvedCounterClassAvailability] = []
    for product_class_id, (class_code, class_name, display_order) in metadata.items():
        expected_quantity = _quantize_quantity(expected_totals.get(product_class_id, ZERO_QUANTITY))
        pending_quantity = _quantize_quantity(pending_totals.get(product_class_id, ZERO_QUANTITY))
        available_quantity = _quantize_quantity(
            max(expected_quantity - pending_quantity, ZERO_QUANTITY)
        )
        if expected_quantity == ZERO_QUANTITY and pending_quantity == ZERO_QUANTITY:
            continue
        rows.append(
            ResolvedCounterClassAvailability(
                product_class_id=product_class_id,
                product_class_code=class_code,
                product_class_name=class_name,
                expected_quantity_before_deferred_attr=expected_quantity,
                pending_class_capture_quantity=pending_quantity,
                available_quantity=available_quantity,
                display_order=display_order,
            )
        )

    return sorted(rows, key=lambda row: (row.display_order, row.product_class_name))


def _resolve_product_identities(
    session: Session,
    *,
    product_ids: set[uuid.UUID],
) -> dict[uuid.UUID, ProductIdentity]:
    if len(product_ids) == 0:
        return {}
    records = (
        session.execute(
            select(
                Product.id,
                Product.code,
                Product.name,
                Product.display_order,
                ProductClass.id.label("product_class_id"),
                ProductClass.code.label("product_class_code"),
                ProductClass.name.label("product_class_name"),
                ProductClass.display_order.label("product_class_display_order"),
            )
            .select_from(Product)
            .join(ProductClass, ProductClass.id == Product.product_class_id)
            .where(
                Product.id.in_(product_ids),
                Product.is_active.is_(True),
                Product.is_sellable.is_(True),
                ProductClass.is_active.is_(True),
                ProductClass.is_sellable.is_(True),
            )
        )
        .mappings()
        .all()
    )
    resolved = {
        record["id"]: ProductIdentity(
            product_id=record["id"],
            product_code=record["code"],
            product_name=record["name"],
            product_class_id=record["product_class_id"],
            product_class_code=record["product_class_code"],
            product_class_name=record["product_class_name"],
            product_display_order=record["display_order"],
            class_display_order=record["product_class_display_order"],
        )
        for record in records
    }
    missing_product_ids = product_ids - set(resolved)
    if len(missing_product_ids) > 0:
        missing_id = next(iter(missing_product_ids))
        raise CashCloseValidationError(
            f"El producto {missing_id} no esta disponible para este cierre."
        )
    return resolved


def _resolve_manual_override_lines(
    *,
    identities: dict[uuid.UUID, ProductIdentity],
    pending_row: PendingClassCaptureRow,
    override_input: ManualOverrideInput,
) -> list[ResolvedAttributionLine] | None:
    attribution_lines: list[ResolvedAttributionLine] = []
    total_quantity = ZERO_QUANTITY
    for product_id, quantity in override_input.attribution_lines:
        identity = identities.get(product_id)
        if identity is None or identity.product_class_id != pending_row.product_class_id:
            return None
        attribution_lines.append(
            ResolvedAttributionLine(
                identity=identity,
                attributed_quantity=quantity,
                attribution_source="MANUAL",
                notes=override_input.notes,
            )
        )
        total_quantity = _quantize_quantity(total_quantity + quantity)
    if total_quantity != pending_row.pending_quantity:
        return None
    return _sort_attribution_lines(attribution_lines)


def _create_discrepancy_document(
    session: Session,
    *,
    discrepancy: ResolvedDiscrepancy,
    branch_id: uuid.UUID,
    workstation_id: uuid.UUID,
    actor_id: uuid.UUID,
    close_id: uuid.UUID,
    committed_at: datetime,
) -> OperationDocument:
    if (
        discrepancy.resolution_type
        == CASH_CLOSE_DISCREPANCY_RESOLUTION_TYPE_CLOSE_COUNTER_ADJUSTMENT
    ):
        document_type = OPERATION_DOCUMENT_TYPE_CLOSE_COUNTER_ADJUSTMENT
        source_bucket_code = OPERATION_BUCKET_BACKROOM
        destination_bucket_code = OPERATION_BUCKET_COUNTER
    else:
        document_type = OPERATION_DOCUMENT_TYPE_CLOSE_WASTE_ADJUSTMENT
        source_bucket_code = OPERATION_BUCKET_COUNTER
        destination_bucket_code = OPERATION_BUCKET_WASTE

    document = OperationDocument(
        document_type=document_type,
        status=OPERATION_DOCUMENT_STATUS_COMMITTED,
        source_branch_id=branch_id,
        destination_branch_id=None,
        source_bucket_code=source_bucket_code,
        destination_bucket_code=destination_bucket_code,
        workstation_id=workstation_id,
        created_by_user_id=actor_id,
        notes=(
            f"Generated by cash close {close_id}. "
            f"Reason {discrepancy.reason_code}. {discrepancy.notes or ''}"
        ).strip(),
        committed_at_utc=committed_at,
    )
    session.add(document)
    session.flush()
    session.add(
        OperationDocumentLine(
            operation_document_id=document.id,
            line_number=1,
            product_id=discrepancy.identity.product_id,
            product_code_snapshot=discrepancy.identity.product_code,
            product_name_snapshot=discrepancy.identity.product_name,
            product_class_id=discrepancy.identity.product_class_id,
            product_class_code_snapshot=discrepancy.identity.product_class_code,
            product_class_name_snapshot=discrepancy.identity.product_class_name,
            quantity=abs(discrepancy.discrepancy_quantity),
            expected_quantity=None,
            received_quantity=None,
            notes=discrepancy.notes,
        )
    )
    return document


def _append_issue(
    issues: list[CashCloseIssueView],
    *,
    code: str,
    message: str,
) -> None:
    if any(issue.code == code for issue in issues):
        return
    issues.append(CashCloseIssueView(code=code, message=message))


def _merge_issues(*issue_groups: Sequence[CashCloseIssueView]) -> list[CashCloseIssueView]:
    merged: list[CashCloseIssueView] = []
    for issue_group in issue_groups:
        for issue in issue_group:
            _append_issue(merged, code=issue.code, message=issue.message)
    return merged


def _resolve_query_reconciliation_status(blockers: Sequence[CashCloseIssueView]) -> str:
    if len(blockers) > 0:
        return CASH_CLOSE_RECONCILIATION_STATUS_BLOCKED
    return CASH_CLOSE_RECONCILIATION_STATUS_PENDING


def _resolve_preview_reconciliation_status(
    blockers: Sequence[CashCloseIssueView],
    *,
    is_ready_to_close: bool,
) -> str:
    if len(blockers) > 0:
        return CASH_CLOSE_RECONCILIATION_STATUS_BLOCKED
    if is_ready_to_close:
        return CASH_CLOSE_RECONCILIATION_STATUS_READY
    return CASH_CLOSE_RECONCILIATION_STATUS_PENDING


def _build_physical_count_blockers(
    command: CashClosePreviewRequest,
) -> list[CashCloseIssueView]:
    blockers: list[CashCloseIssueView] = []
    if not command.counter_empty_confirmed:
        return blockers

    if (
        len(command.counted_product_lines) > 0
        or len(command.manual_reconciliation_overrides) > 0
        or len(command.discrepancy_resolutions) > 0
    ):
        _append_issue(
            blockers,
            code=CASH_CLOSE_BLOCKER_INVALID_COUNT_PAYLOAD,
            message=(
                "El cierre con mostrador vacio no puede incluir productos ni "
                "conciliaciones fisicas capturadas."
            ),
        )

    return blockers


def _build_commit_blockers(
    *,
    command: CashClosePreviewRequest,
    prepared: CashClosePreparedPreview,
) -> list[CashCloseIssueView]:
    blockers = list(prepared.blockers)
    has_counted_monetary_input = len(command.counted_payment_methods) > 0

    if not has_counted_monetary_input:
        _append_issue(
            blockers,
            code=CASH_CLOSE_BLOCKER_MISSING_COUNTED_PAYMENT_TOTALS,
            message="Falta capturar el conteo monetario para poder cerrar.",
        )

    if (
        not prepared.counter_empty_confirmed
        and len(prepared.computation.products) > 0
        and len(command.counted_product_lines) == 0
    ):
        _append_issue(
            blockers,
            code=CASH_CLOSE_BLOCKER_MISSING_COUNTED_CLOSING_STOCK,
            message=("Falta capturar el conteo final del mostrador antes de cerrar el turno."),
        )

    return blockers


def _sort_product_identities(identities: list[ProductIdentity]) -> list[ProductIdentity]:
    return sorted(
        identities,
        key=lambda identity: (
            identity.class_display_order,
            identity.product_class_name.lower(),
            identity.product_display_order,
            identity.product_name.lower(),
        ),
    )


def _sort_attribution_lines(
    lines: list[ResolvedAttributionLine],
) -> list[ResolvedAttributionLine]:
    return sorted(
        lines,
        key=lambda line: (
            line.identity.class_display_order,
            line.identity.product_display_order,
            line.identity.product_name.lower(),
        ),
    )


def _to_payment_method_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    expected_cash_amount: Decimal,
) -> list[CashClosePaymentMethodRowView]:
    rows_by_code = {str(row["payment_method_code"]): row for row in rows}
    result: list[CashClosePaymentMethodRowView] = []
    for catalog_row in _get_payment_method_catalog():
        row = rows_by_code.get(catalog_row.payment_method_code)
        counted_amount = (
            _quantize_money(Decimal(str(row["counted_amount"])))
            if row is not None and row["counted_amount"] is not None
            else ZERO_MONEY
        )
        expected_amount = (
            _quantize_money(Decimal(str(row["expected_amount"])))
            if row is not None and row["expected_amount"] is not None
            else (
                expected_cash_amount
                if catalog_row.payment_method_code == CASH_CLOSE_PAYMENT_METHOD_CASH
                else None
            )
        )
        variance_amount = (
            _quantize_money(Decimal(str(row["variance_amount"])))
            if row is not None and row["variance_amount"] is not None
            else (
                _quantize_money(counted_amount - expected_cash_amount)
                if catalog_row.payment_method_code == CASH_CLOSE_PAYMENT_METHOD_CASH
                else None
            )
        )
        result.append(
            CashClosePaymentMethodRowView(
                payment_method_code=catalog_row.payment_method_code,
                currency_code=CASH_CLOSE_CURRENCY_MXN,
                display_order=catalog_row.display_order,
                counted_amount=counted_amount,
                expected_amount=expected_amount,
                variance_amount=variance_amount,
                is_expected_supported=catalog_row.is_expected_supported,
            )
        )
    return result


def _to_product_views(
    products: Sequence[ResolvedProductState],
) -> list[CashCloseReconciliationProductView]:
    return [
        CashCloseReconciliationProductView(
            product_id=product.identity.product_id,
            product_code=product.identity.product_code,
            product_name=product.identity.product_name,
            product_class_id=product.identity.product_class_id,
            product_class_code=product.identity.product_class_code,
            product_class_name=product.identity.product_class_name,
            expected_quantity_before_deferred_attr=product.expected_quantity_before_deferred_attr,
            counted_quantity=product.counted_quantity,
            final_expected_quantity=product.final_expected_quantity,
            discrepancy_quantity=product.discrepancy_quantity,
            notes=product.notes,
        )
        for product in products
    ]


def _to_counter_class_availability_views(
    rows: Sequence[ResolvedCounterClassAvailability],
) -> list[CashCloseCounterClassAvailabilityView]:
    return [
        CashCloseCounterClassAvailabilityView(
            product_class_id=row.product_class_id,
            product_class_code=row.product_class_code,
            product_class_name=row.product_class_name,
            expected_quantity_before_deferred_attr=row.expected_quantity_before_deferred_attr,
            pending_class_capture_quantity=row.pending_class_capture_quantity,
            available_quantity=row.available_quantity,
        )
        for row in rows
    ]


def _to_class_reconciliation_views(
    class_reconciliations: Sequence[ResolvedClassReconciliation],
) -> list[CashCloseClassReconciliationView]:
    return [
        CashCloseClassReconciliationView(
            product_class_id=class_state.product_class_id,
            product_class_code=class_state.product_class_code,
            product_class_name=class_state.product_class_name,
            pending_quantity=class_state.pending_quantity,
            auto_attributed_quantity=class_state.auto_attributed_quantity,
            final_attributed_quantity=class_state.final_attributed_quantity,
            discrepancy_quantity=class_state.discrepancy_quantity,
            resolution_status=class_state.resolution_status,
            attribution_lines=[
                CashCloseAttributionLineView(
                    product_id=line.identity.product_id,
                    product_code=line.identity.product_code,
                    product_name=line.identity.product_name,
                    product_class_id=line.identity.product_class_id,
                    product_class_code=line.identity.product_class_code,
                    product_class_name=line.identity.product_class_name,
                    attributed_quantity=line.attributed_quantity,
                    attribution_source=line.attribution_source,
                    notes=line.notes,
                )
                for line in class_state.attribution_lines
            ],
            notes=class_state.notes,
        )
        for class_state in class_reconciliations
    ]


def _to_discrepancy_views(
    discrepancy_resolutions: Sequence[ResolvedDiscrepancy],
) -> list[CashCloseDiscrepancyResolutionView]:
    return [
        CashCloseDiscrepancyResolutionView(
            product_id=resolution.identity.product_id,
            product_code=resolution.identity.product_code,
            product_name=resolution.identity.product_name,
            product_class_id=resolution.identity.product_class_id,
            product_class_code=resolution.identity.product_class_code,
            product_class_name=resolution.identity.product_class_name,
            expected_quantity=resolution.expected_quantity,
            counted_quantity=resolution.counted_quantity,
            discrepancy_quantity=resolution.discrepancy_quantity,
            resolution_type=resolution.resolution_type,
            reason_code=resolution.reason_code,
            notes=resolution.notes,
            generated_document_id=resolution.generated_document_id,
        )
        for resolution in discrepancy_resolutions
    ]


def _format_blocker_error(blockers: Sequence[CashCloseIssueView]) -> str:
    return "No se puede cerrar el turno: " + "; ".join(blocker.message for blocker in blockers)


def _get_branch_brand_key(branch_code: str) -> str | None:
    return BRANCH_BRAND_MAPPING.get(branch_code)


def _financial_currency_or_default(currencies: Sequence[str]) -> str:
    return currencies[0] if len(currencies) > 0 else CASH_CLOSE_CURRENCY_MXN


def _optional_decimal_to_string(amount: Decimal | None) -> str | None:
    return str(amount) if amount is not None else None


def _quantize_money(amount: Decimal) -> Decimal:
    return amount.quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)


def _quantize_quantity(amount: Decimal) -> Decimal:
    return amount.quantize(QUANTITY_QUANTIZER, rounding=ROUND_HALF_UP)
