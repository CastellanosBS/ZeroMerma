from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.modules.branches.application.schemas import PosBootstrapResponse
from zeromerma_api.modules.branches.application.services import PosBootstrapService
from zeromerma_api.modules.branches.domain.exceptions import (
    BranchAccessError,
    BranchAssignmentRequiredError,
    BranchInactiveError,
    WorkstationInactiveError,
    WorkstationNotFoundError,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user

router = APIRouter(prefix="/v1/pos", tags=["pos"])


def _to_http_exception(error: BranchAccessError) -> HTTPException:
    if isinstance(error, WorkstationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))

    if isinstance(error, BranchAssignmentRequiredError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))

    if isinstance(error, (BranchInactiveError, WorkstationInactiveError)):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/bootstrap", response_model=PosBootstrapResponse)
def bootstrap(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> PosBootstrapResponse:
    try:
        return PosBootstrapService().get_bootstrap(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
        )
    except BranchAccessError as error:
        raise _to_http_exception(error) from error
