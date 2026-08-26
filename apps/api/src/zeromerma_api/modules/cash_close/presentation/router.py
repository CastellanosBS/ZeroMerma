from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.modules.branches.domain.exceptions import (
    BranchAccessError,
    BranchAssignmentRequiredError,
    BranchInactiveError,
    WorkstationInactiveError,
    WorkstationNotFoundError,
)
from zeromerma_api.modules.cash.domain.exceptions import CashSessionError
from zeromerma_api.modules.cash_close.application.admin_schemas import (
    AdminCashCutDetailView,
    AdminCashCutsListResponse,
)
from zeromerma_api.modules.cash_close.application.admin_services import AdminCashCutService
from zeromerma_api.modules.cash_close.application.cash_flow_schemas import (
    AdminCashFlowListResponse,
    AdminCashFlowMovementDetailView,
)
from zeromerma_api.modules.cash_close.application.cash_flow_services import (
    AdminCashFlowService,
)
from zeromerma_api.modules.cash_close.application.reconciliation_schemas import (
    AdminPendingDiscrepanciesResponse,
    AdminReconciliationCreateRequest,
    AdminReconciliationDetailView,
    AdminReconciliationListResponse,
    AdminReconciliationResolveRequest,
)
from zeromerma_api.modules.cash_close.application.reconciliation_services import (
    AdminReconciliationService,
)
from zeromerma_api.modules.cash_close.application.schemas import (
    CashCloseBootstrapResponse,
    CashCloseDetailResponse,
    CashClosePreviewRequest,
    CashClosePreviewResponse,
    CashCloseReconciliationResponse,
    CashCloseSummaryResponse,
)
from zeromerma_api.modules.cash_close.application.services import (
    CashCloseCommandService,
    CashCloseQueryService,
)
from zeromerma_api.modules.cash_close.domain.exceptions import (
    CashCloseConflictError,
    CashCloseError,
    CashCloseNotFoundError,
    CashCloseValidationError,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.application.services import user_can_access_surface
from zeromerma_api.modules.identity.domain.constants import IDENTITY_SURFACE_BACKOFFICE
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user

router = APIRouter(prefix="/v1/cash-close", tags=["cash-close"])
admin_router = APIRouter(prefix="/v1/admin/cash-cuts", tags=["admin-cash-cuts"])
admin_reconciliation_router = APIRouter(
    prefix="/v1/admin/reconciliation",
    tags=["admin-reconciliation"],
)
admin_cash_flow_router = APIRouter(prefix="/v1/admin/cash-flow", tags=["admin-cash-flow"])


def _require_backoffice_user(current_user: AuthenticatedUser) -> None:
    if not user_can_access_surface(current_user, IDENTITY_SURFACE_BACKOFFICE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Backoffice access is required.",
        )


def _to_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, WorkstationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))

    if isinstance(error, CashCloseNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))

    if isinstance(error, BranchAssignmentRequiredError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))

    if isinstance(
        error,
        (
            BranchInactiveError,
            WorkstationInactiveError,
            CashCloseConflictError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

    if isinstance(
        error,
        (
            BranchAccessError,
            CashCloseValidationError,
            CashCloseError,
            CashSessionError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@admin_router.get("", response_model=AdminCashCutsListResponse)
def list_admin_cash_cuts(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    branch_id: UUID | None = None,
    workstation_id: UUID | None = None,
    cashier_id: UUID | None = None,
    payment_method: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status", min_length=1)] = None,
    difference_state: Annotated[str | None, Query(min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    has_refunds: bool | None = None,
    has_operational_payments: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AdminCashCutsListResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminCashCutService().list_cash_cuts(
            session,
            branch_id=branch_id,
            cashier_id=cashier_id,
            date_from=date_from,
            date_to=date_to,
            difference_state=difference_state,
            has_operational_payments=has_operational_payments,
            has_refunds=has_refunds,
            page=page,
            page_size=page_size,
            payment_method=payment_method,
            search=search,
            status_filter=status_filter,
            workstation_id=workstation_id,
        )
    except (CashCloseNotFoundError, CashCloseValidationError, CashCloseError) as error:
        raise _to_http_exception(error) from error


@admin_router.get("/{cash_session_id}", response_model=AdminCashCutDetailView)
def get_admin_cash_cut_detail(
    cash_session_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminCashCutDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminCashCutService().get_cash_cut_detail(
            session,
            cash_session_id=cash_session_id,
        )
    except (CashCloseNotFoundError, CashCloseValidationError, CashCloseError) as error:
        raise _to_http_exception(error) from error


@admin_cash_flow_router.get("", response_model=AdminCashFlowListResponse)
def list_admin_cash_flow_movements(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    amount_max: Decimal | None = None,
    amount_min: Decimal | None = None,
    branch_id: UUID | None = None,
    category: Annotated[str | None, Query(min_length=1)] = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    direction: Annotated[str | None, Query(min_length=1)] = None,
    operator_id: UUID | None = None,
    payment_method: Annotated[str | None, Query(min_length=1)] = None,
    reconciliation_state: Annotated[str | None, Query(min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    source_type: Annotated[str | None, Query(min_length=1)] = None,
    workstation_id: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AdminCashFlowListResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminCashFlowService().list_movements(
            session,
            amount_max=amount_max,
            amount_min=amount_min,
            branch_id=branch_id,
            category=category,
            date_from=date_from,
            date_to=date_to,
            direction=direction,
            operator_id=operator_id,
            page=page,
            page_size=page_size,
            payment_method=payment_method,
            reconciliation_state=reconciliation_state,
            search=search,
            source_type=source_type,
            workstation_id=workstation_id,
        )
    except (CashCloseNotFoundError, CashCloseValidationError, CashCloseError) as error:
        raise _to_http_exception(error) from error


@admin_cash_flow_router.get("/{movement_id:path}", response_model=AdminCashFlowMovementDetailView)
def get_admin_cash_flow_movement_detail(
    movement_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminCashFlowMovementDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminCashFlowService().get_movement_detail(
            session,
            movement_id=movement_id,
        )
    except (CashCloseNotFoundError, CashCloseValidationError, CashCloseError) as error:
        raise _to_http_exception(error) from error


@admin_reconciliation_router.get("", response_model=AdminReconciliationListResponse)
def list_admin_reconciliations(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    amount_max: Decimal | None = None,
    amount_min: Decimal | None = None,
    branch_id: UUID | None = None,
    workstation_id: UUID | None = None,
    cashier_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    discrepancy_type: Annotated[str | None, Query(min_length=1)] = None,
    evidence_state: Annotated[str | None, Query(min_length=1)] = None,
    payment_method: Annotated[str | None, Query(min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    source_type: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status", min_length=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AdminReconciliationListResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminReconciliationService().list_reconciliations(
            session,
            amount_max=amount_max,
            amount_min=amount_min,
            branch_id=branch_id,
            cashier_id=cashier_id,
            date_from=date_from,
            date_to=date_to,
            discrepancy_type=discrepancy_type,
            evidence_state=evidence_state,
            page=page,
            page_size=page_size,
            payment_method=payment_method,
            search=search,
            source_type=source_type,
            status_filter=status_filter,
            workstation_id=workstation_id,
        )
    except (CashCloseNotFoundError, CashCloseValidationError, CashCloseError) as error:
        raise _to_http_exception(error) from error


@admin_reconciliation_router.get(
    "/pending",
    response_model=AdminPendingDiscrepanciesResponse,
)
def list_admin_pending_reconciliation_discrepancies(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    amount_max: Decimal | None = None,
    amount_min: Decimal | None = None,
    branch_id: UUID | None = None,
    workstation_id: UUID | None = None,
    cashier_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    discrepancy_type: Annotated[str | None, Query(min_length=1)] = None,
    payment_method: Annotated[str | None, Query(min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    source_type: Annotated[str | None, Query(min_length=1)] = None,
) -> AdminPendingDiscrepanciesResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminReconciliationService().list_pending_discrepancies(
            session,
            amount_max=amount_max,
            amount_min=amount_min,
            branch_id=branch_id,
            cashier_id=cashier_id,
            date_from=date_from,
            date_to=date_to,
            discrepancy_type=discrepancy_type,
            payment_method=payment_method,
            search=search,
            source_type=source_type,
            workstation_id=workstation_id,
        )
    except (CashCloseNotFoundError, CashCloseValidationError, CashCloseError) as error:
        raise _to_http_exception(error) from error


@admin_reconciliation_router.get(
    "/{reconciliation_id}",
    response_model=AdminReconciliationDetailView,
)
def get_admin_reconciliation_detail(
    reconciliation_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminReconciliationDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminReconciliationService().get_reconciliation_detail(
            session,
            reconciliation_id=reconciliation_id,
        )
    except (CashCloseNotFoundError, CashCloseValidationError, CashCloseError) as error:
        raise _to_http_exception(error) from error


@admin_reconciliation_router.post("", response_model=AdminReconciliationDetailView)
def create_admin_reconciliation(
    payload: AdminReconciliationCreateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminReconciliationDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminReconciliationService().create_reconciliation(
            session,
            command=payload,
            current_user=current_user,
            request_id=request_id,
        )
    except (CashCloseNotFoundError, CashCloseValidationError, CashCloseError) as error:
        raise _to_http_exception(error) from error


@admin_reconciliation_router.post(
    "/{reconciliation_id}/resolve",
    response_model=AdminReconciliationDetailView,
)
def resolve_admin_reconciliation(
    reconciliation_id: UUID,
    payload: AdminReconciliationResolveRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminReconciliationDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminReconciliationService().resolve_reconciliation(
            session,
            command=payload,
            current_user=current_user,
            reconciliation_id=reconciliation_id,
            request_id=request_id,
        )
    except (CashCloseNotFoundError, CashCloseValidationError, CashCloseError) as error:
        raise _to_http_exception(error) from error


@router.get("/bootstrap", response_model=CashCloseBootstrapResponse)
def get_cash_close_bootstrap(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> CashCloseBootstrapResponse:
    try:
        return CashCloseQueryService().get_bootstrap(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
        )
    except (BranchAccessError, CashSessionError, CashCloseError) as error:
        raise _to_http_exception(error) from error


@router.get("/summary", response_model=CashCloseSummaryResponse)
def get_cash_close_summary(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> CashCloseSummaryResponse:
    try:
        return CashCloseQueryService().get_summary(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
        )
    except (BranchAccessError, CashSessionError, CashCloseError) as error:
        raise _to_http_exception(error) from error


@router.get("/reconciliation", response_model=CashCloseReconciliationResponse)
def get_cash_close_reconciliation(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> CashCloseReconciliationResponse:
    try:
        return CashCloseQueryService().get_reconciliation(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
        )
    except (BranchAccessError, CashSessionError, CashCloseError) as error:
        raise _to_http_exception(error) from error


@router.post("/preview", response_model=CashClosePreviewResponse)
def preview_cash_close(
    payload: CashClosePreviewRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> CashClosePreviewResponse:
    try:
        return CashCloseQueryService().preview_close(
            session,
            current_user=current_user,
            command=payload,
        )
    except (BranchAccessError, CashSessionError, CashCloseError) as error:
        raise _to_http_exception(error) from error


@router.post("/commit", response_model=CashCloseDetailResponse)
def commit_cash_close(
    payload: CashClosePreviewRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> CashCloseDetailResponse:
    try:
        return CashCloseCommandService().commit_close(
            session,
            current_user=current_user,
            command=payload,
            request_id=None,
        )
    except (BranchAccessError, CashSessionError, CashCloseError) as error:
        raise _to_http_exception(error) from error


@router.get("/{close_id}", response_model=CashCloseDetailResponse)
def get_cash_close_detail(
    close_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> CashCloseDetailResponse:
    try:
        return CashCloseQueryService().get_close_detail(
            session,
            current_user=current_user,
            close_id=close_id,
        )
    except (BranchAccessError, CashSessionError, CashCloseError) as error:
        raise _to_http_exception(error) from error

