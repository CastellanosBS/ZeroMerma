from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.modules.branches.application.access import WorkstationAccessService
from zeromerma_api.modules.branches.domain.exceptions import (
    BranchAccessError,
    BranchAssignmentRequiredError,
    BranchInactiveError,
    WorkstationInactiveError,
    WorkstationNotFoundError,
)
from zeromerma_api.modules.cash.application.schemas import CashSessionView, OpenCashSessionRequest
from zeromerma_api.modules.cash.application.services import (
    CashSessionCommandService,
    CashSessionQueryService,
)
from zeromerma_api.modules.cash.domain.exceptions import CashSessionConflictError
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user

router = APIRouter(prefix="/v1/cash-sessions", tags=["cash-sessions"])


def _to_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, WorkstationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))

    if isinstance(error, BranchAssignmentRequiredError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))

    if isinstance(error, (BranchInactiveError, WorkstationInactiveError, CashSessionConflictError)):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

    if isinstance(error, BranchAccessError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.post("/open", response_model=CashSessionView, status_code=status.HTTP_201_CREATED)
def open_cash_session(
    payload: OpenCashSessionRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> CashSessionView:
    try:
        return CashSessionCommandService().open_session(
            session,
            current_user=current_user,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except (BranchAccessError, CashSessionConflictError) as error:
        raise _to_http_exception(error) from error


@router.get("/current", response_model=CashSessionView | None)
def current_cash_session(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> CashSessionView | None:
    try:
        WorkstationAccessService().resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        return CashSessionQueryService().get_open_session_for_workstation_code(
            session,
            workstation_code=workstation_code,
        )
    except BranchAccessError as error:
        raise _to_http_exception(error) from error
