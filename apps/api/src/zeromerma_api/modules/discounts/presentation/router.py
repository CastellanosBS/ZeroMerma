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
from zeromerma_api.modules.discounts.application.schemas import (
    CreateOperationalDiscountRequest,
    DiscountsBootstrapResponse,
    DiscountsListResponse,
    OperationalDiscountDetailResponse,
)
from zeromerma_api.modules.discounts.application.services import (
    DiscountsCommandService,
    DiscountsQueryService,
)
from zeromerma_api.modules.discounts.domain.exceptions import (
    OperationalDiscountConflictError,
    OperationalDiscountError,
    OperationalDiscountNotFoundError,
    OperationalDiscountValidationError,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user

router = APIRouter(prefix="/v1/discounts", tags=["discounts"])


def _to_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, (WorkstationNotFoundError, OperationalDiscountNotFoundError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))

    if isinstance(error, BranchAssignmentRequiredError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))

    if isinstance(
        error,
        (BranchInactiveError, WorkstationInactiveError, OperationalDiscountConflictError),
    ):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

    if isinstance(
        error,
        (
            BranchAccessError,
            OperationalDiscountValidationError,
            OperationalDiscountError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/bootstrap", response_model=DiscountsBootstrapResponse)
def get_discounts_bootstrap(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> DiscountsBootstrapResponse:
    try:
        return DiscountsQueryService().get_bootstrap(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
        )
    except (BranchAccessError, OperationalDiscountError) as error:
        raise _to_http_exception(error) from error


@router.get("", response_model=DiscountsListResponse)
def list_discounts(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    scope: Annotated[str | None, Query(min_length=1)] = None,
    created_by_user_id: UUID | None = None,
    query: Annotated[str | None, Query(min_length=1)] = None,
    category: Annotated[str | None, Query(min_length=1)] = None,
    payment_method: Annotated[str | None, Query(min_length=1)] = None,
) -> DiscountsListResponse:
    try:
        return DiscountsQueryService().list_discounts(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            scope=scope,
            created_by_user_id=created_by_user_id,
            query=query,
            category_filter=category,
            payment_method_filter=payment_method,
        )
    except (BranchAccessError, OperationalDiscountError) as error:
        raise _to_http_exception(error) from error


@router.get("/{discount_id}", response_model=OperationalDiscountDetailResponse)
def get_discount_detail(
    discount_id: UUID,
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> OperationalDiscountDetailResponse:
    try:
        return DiscountsQueryService().get_discount_detail(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            discount_id=discount_id,
        )
    except (BranchAccessError, OperationalDiscountError) as error:
        raise _to_http_exception(error) from error


@router.post(
    "",
    response_model=OperationalDiscountDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_discount(
    payload: CreateOperationalDiscountRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> OperationalDiscountDetailResponse:
    try:
        return DiscountsCommandService().create_discount(
            session,
            current_user=current_user,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except (BranchAccessError, OperationalDiscountError) as error:
        raise _to_http_exception(error) from error
