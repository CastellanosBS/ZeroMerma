from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user

router = APIRouter(prefix="/v1/cash-close", tags=["cash-close"])


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
