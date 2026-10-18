from __future__ import annotations

from dataclasses import replace
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response, status
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
from zeromerma_api.modules.cash.application.idempotency import CashSessionOpenService
from zeromerma_api.modules.cash.application.schemas import (
    CashSessionOpenResultView,
    CashSessionView,
    OpenCashSessionRequest,
)
from zeromerma_api.modules.cash.application.services import (
    CashSessionQueryService,
)
from zeromerma_api.modules.cash.domain.exceptions import CashSessionConflictError
from zeromerma_api.modules.idempotency.application.canonicalization import (
    IDEMPOTENCY_KEY_PATTERN,
    parse_idempotency_key,
)
from zeromerma_api.modules.idempotency.presentation.http import (
    idempotency_response,
    require_idempotency_key,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user
from zeromerma_api.presentation.errors import error_responses

_REPLAY_RESPONSE = {
    "headers": {"Idempotency-Replayed": {"$ref": "#/components/headers/IdempotencyReplayed"}}
}

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


@router.post(
    "/open",
    response_model=CashSessionOpenResultView,
    status_code=status.HTTP_201_CREATED,
    responses={201: _REPLAY_RESPONSE, 409: {**error_responses()[409], **_REPLAY_RESPONSE}},
)
def open_cash_session(
    payload: OpenCashSessionRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    try:
        result = CashSessionOpenService().open(
            session,
            current_user=current_user,
            command=payload,
            key=key,
            request_id=request.headers.get("X-Request-ID"),
        )
        return idempotency_response(result, request)
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


@router.get(
    "/confirmations/{idempotency_key}",
    response_model=CashSessionOpenResultView,
    responses={200: _REPLAY_RESPONSE, 409: {**error_responses()[409], **_REPLAY_RESPONSE}},
)
def recover_cash_session_opening(
    idempotency_key: Annotated[str, Path(pattern=IDEMPOTENCY_KEY_PATTERN)],
    workstation_code: Annotated[str, Query(min_length=1)],
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    result = CashSessionOpenService().recover(
        session,
        current_user=current_user,
        key=parse_idempotency_key(idempotency_key),
        workstation_code=workstation_code,
    )
    if result.status_code < 300:
        result = replace(result, status_code=200)
    return idempotency_response(result, request)
