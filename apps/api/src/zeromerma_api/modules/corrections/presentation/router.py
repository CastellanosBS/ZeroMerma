from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
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
from zeromerma_api.modules.corrections.application.schemas import (
    CorrectionBootstrapResponse,
    CorrectionCommitRequest,
    CorrectionDocumentView,
    CorrectionSearchResponse,
    CorrectionsHistoryResponse,
    CorrectionsProductsResponse,
    CorrectionTargetDetailResponse,
)
from zeromerma_api.modules.corrections.application.services import (
    CorrectionCommandService,
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
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user
from zeromerma_api.modules.operations.domain.exceptions import OperationError

router = APIRouter(prefix="/v1/corrections", tags=["corrections"])


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


@router.post("/commit", response_model=CorrectionDocumentView, status_code=status.HTTP_201_CREATED)
def commit_correction(
    payload: CorrectionCommitRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> CorrectionDocumentView:
    try:
        return CorrectionCommandService().commit_correction(
            session,
            current_user=current_user,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except (BranchAccessError, CatalogError, OperationError, CorrectionError) as error:
        raise _to_http_exception(error) from error
