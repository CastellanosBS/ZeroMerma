from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response, status
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.modules.branches.domain.exceptions import (
    BranchAccessError,
    BranchAssignmentRequiredError,
    BranchInactiveError,
    WorkstationInactiveError,
    WorkstationNotFoundError,
)
from zeromerma_api.modules.catalog.domain.exceptions import CatalogError, ProductNotFoundError
from zeromerma_api.modules.corrections.application.admin_schemas import (
    AdminCorrectionDetailView,
    AdminCorrectionsListResponse,
)
from zeromerma_api.modules.corrections.application.admin_services import AdminCorrectionsService
from zeromerma_api.modules.corrections.application.idempotency import CorrectionCommitService
from zeromerma_api.modules.corrections.application.schemas import (
    CorrectionBootstrapResponse,
    CorrectionCommitRequest,
    CorrectionCommitResultView,
    CorrectionDocumentView,
    CorrectionSearchResponse,
    CorrectionsHistoryResponse,
    CorrectionsProductsResponse,
    CorrectionTargetDetailResponse,
)
from zeromerma_api.modules.corrections.application.services import (
    CorrectionQueryService,
)
from zeromerma_api.modules.corrections.domain.exceptions import (
    CorrectionConflictError,
    CorrectionError,
    CorrectionIneligibleError,
    CorrectionNotFoundError,
    CorrectionReasonNotFoundError,
    CorrectionValidationError,
)
from zeromerma_api.modules.idempotency.application.canonicalization import (
    IDEMPOTENCY_KEY_PATTERN,
    parse_idempotency_key,
)
from zeromerma_api.modules.idempotency.presentation.http import (
    idempotency_response,
    require_idempotency_key,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.application.services import user_can_access_surface
from zeromerma_api.modules.identity.domain.constants import IDENTITY_SURFACE_BACKOFFICE
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user
from zeromerma_api.modules.operations.domain.exceptions import OperationError
from zeromerma_api.presentation.errors import error_responses

_REPLAY_RESPONSE = {
    "headers": {"Idempotency-Replayed": {"$ref": "#/components/headers/IdempotencyReplayed"}}
}

router = APIRouter(prefix="/v1/corrections", tags=["corrections"])
admin_router = APIRouter(
    prefix="/v1/admin/returns-corrections/corrections",
    tags=["admin-returns-corrections"],
)


def _require_backoffice_user(current_user: AuthenticatedUser) -> AuthenticatedUser:
    if not user_can_access_surface(current_user, IDENTITY_SURFACE_BACKOFFICE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Backoffice access is required.",
        )
    return current_user


def _to_http_exception(error: Exception) -> HTTPException:
    if isinstance(
        error,
        (
            WorkstationNotFoundError,
            ProductNotFoundError,
            CorrectionNotFoundError,
            CorrectionReasonNotFoundError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))

    if isinstance(error, BranchAssignmentRequiredError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))

    if isinstance(
        error,
        (
            BranchInactiveError,
            WorkstationInactiveError,
            CorrectionConflictError,
            CorrectionIneligibleError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

    if isinstance(
        error,
        (
            BranchAccessError,
            CatalogError,
            OperationError,
            CorrectionValidationError,
            CorrectionError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@admin_router.get("", response_model=AdminCorrectionsListResponse)
def list_admin_corrections(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    branch_id: UUID | None = None,
    operator_id: UUID | None = None,
    correction_type: Annotated[str | None, Query(min_length=1)] = None,
    target_document_type: Annotated[str | None, Query(min_length=1)] = None,
    reason_code: Annotated[str | None, Query(min_length=1)] = None,
    net_effect: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status", min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="page_size", ge=1, le=100)] = 25,
) -> AdminCorrectionsListResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminCorrectionsService().list_corrections(
            session,
            branch_id=branch_id,
            correction_type=correction_type,
            date_from=(
                None if date_from is None else datetime.combine(date_from, time.min, tzinfo=UTC)
            ),
            date_to=None if date_to is None else datetime.combine(date_to, time.max, tzinfo=UTC),
            net_effect=net_effect,
            operator_id=operator_id,
            page=page,
            page_size=page_size,
            reason_code=reason_code,
            search=search,
            status_filter=status_filter,
            target_document_type=target_document_type,
        )
    except CorrectionError as error:
        raise _to_http_exception(error) from error


@admin_router.get("/{correction_id}", response_model=AdminCorrectionDetailView)
def get_admin_correction_detail(
    correction_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminCorrectionDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminCorrectionsService().get_correction_detail(
            session,
            correction_id=correction_id,
        )
    except CorrectionError as error:
        raise _to_http_exception(error) from error


@router.get("/bootstrap", response_model=CorrectionBootstrapResponse)
def get_corrections_bootstrap(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> CorrectionBootstrapResponse:
    try:
        return CorrectionQueryService().get_bootstrap(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
        )
    except (BranchAccessError, CatalogError, OperationError, CorrectionError) as error:
        raise _to_http_exception(error) from error


@router.get("/search", response_model=CorrectionSearchResponse)
def search_correction_targets(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    query: Annotated[str | None, Query(min_length=1)] = None,
    document_type: Annotated[str | None, Query(min_length=1)] = None,
) -> CorrectionSearchResponse:
    try:
        return CorrectionQueryService().search_documents(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            query=query,
            document_type=document_type,
        )
    except (BranchAccessError, CatalogError, OperationError, CorrectionError) as error:
        raise _to_http_exception(error) from error


@router.get("/history", response_model=CorrectionsHistoryResponse)
def list_correction_history(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    scope: Annotated[str | None, Query(min_length=1)] = None,
    query: Annotated[str | None, Query(min_length=1)] = None,
    created_by_user_id: UUID | None = None,
    target_document_type: Annotated[str | None, Query(min_length=1)] = None,
    reason_code: Annotated[str | None, Query(min_length=1)] = None,
) -> CorrectionsHistoryResponse:
    try:
        return CorrectionQueryService().list_correction_history(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            scope=scope,
            query=query,
            created_by_user_id=created_by_user_id,
            target_document_type=target_document_type,
            reason_code=reason_code,
        )
    except (BranchAccessError, CatalogError, OperationError, CorrectionError) as error:
        raise _to_http_exception(error) from error


@router.get("/history/{correction_id}", response_model=CorrectionDocumentView)
def get_correction_document_detail(
    correction_id: UUID,
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> CorrectionDocumentView:
    try:
        return CorrectionQueryService().get_correction_document(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            correction_id=correction_id,
        )
    except (BranchAccessError, CatalogError, OperationError, CorrectionError) as error:
        raise _to_http_exception(error) from error


@router.get("/products", response_model=CorrectionsProductsResponse)
def search_correction_products(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    query: Annotated[str | None, Query(min_length=1)] = None,
) -> CorrectionsProductsResponse:
    try:
        return CorrectionQueryService().search_products(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            query=query,
        )
    except (BranchAccessError, CatalogError, OperationError, CorrectionError) as error:
        raise _to_http_exception(error) from error


@router.get("/{target_document_id}", response_model=CorrectionTargetDetailResponse)
def get_correction_target_detail(
    target_document_id: UUID,
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> CorrectionTargetDetailResponse:
    try:
        return CorrectionQueryService().get_target_detail(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            target_document_id=target_document_id,
        )
    except (BranchAccessError, CatalogError, OperationError, CorrectionError) as error:
        raise _to_http_exception(error) from error


@router.post(
    "/commit",
    response_model=CorrectionCommitResultView,
    status_code=status.HTTP_201_CREATED,
    responses={201: _REPLAY_RESPONSE, 409: {**error_responses()[409], **_REPLAY_RESPONSE}},
)
def commit_correction(
    payload: CorrectionCommitRequest,
    request: Request,
    idempotency_key: Annotated[UUID, Depends(require_idempotency_key)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    try:
        result = CorrectionCommitService().commit(
            session,
            current_user=current_user,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
            key=idempotency_key,
        )
        return idempotency_response(result, request)
    except (BranchAccessError, CatalogError, OperationError, CorrectionError) as error:
        raise _to_http_exception(error) from error


@router.get(
    "/confirmations/{idempotency_key}",
    response_model=CorrectionCommitResultView,
    responses={200: _REPLAY_RESPONSE, 409: {**error_responses()[409], **_REPLAY_RESPONSE}},
)
def recover_commit_correction(
    idempotency_key: Annotated[str, Path(pattern=IDEMPOTENCY_KEY_PATTERN)],
    workstation_code: Annotated[str, Query(min_length=1)],
    cash_session_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    result = CorrectionCommitService().recover(
        session,
        current_user=current_user,
        key=parse_idempotency_key(idempotency_key),
        workstation_code=workstation_code,
        cash_session_id=cash_session_id,
    )
    if result.status_code < 300:
        result = replace(result, status_code=200)
    return idempotency_response(result, request)
