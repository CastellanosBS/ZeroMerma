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
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user
from zeromerma_api.modules.payments.application.schemas import (
    CreateOperationalPaymentRequest,
    OperationalPaymentDetailResponse,
    PaymentsBootstrapResponse,
    PaymentsListResponse,
)
from zeromerma_api.modules.payments.application.services import (
    PaymentsCommandService,
    PaymentsQueryService,
)
from zeromerma_api.modules.payments.domain.exceptions import (
    OperationalPaymentConflictError,
    OperationalPaymentError,
    OperationalPaymentNotFoundError,
    OperationalPaymentValidationError,
)

router = APIRouter(prefix="/v1/payments", tags=["payments"])


def _to_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, (WorkstationNotFoundError, OperationalPaymentNotFoundError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))

    if isinstance(error, BranchAssignmentRequiredError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))

    if isinstance(
        error,
        (BranchInactiveError, WorkstationInactiveError, OperationalPaymentConflictError),
    ):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

    if isinstance(
        error,
        (
            BranchAccessError,
            OperationalPaymentValidationError,
            OperationalPaymentError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/bootstrap", response_model=PaymentsBootstrapResponse)
def get_payments_bootstrap(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> PaymentsBootstrapResponse:
    try:
        return PaymentsQueryService().get_bootstrap(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
        )
    except (BranchAccessError, OperationalPaymentError) as error:
        raise _to_http_exception(error) from error


@router.get("", response_model=PaymentsListResponse)
def list_payments(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    scope: Annotated[str | None, Query(min_length=1)] = None,
    created_by_user_id: UUID | None = None,
    query: Annotated[str | None, Query(min_length=1)] = None,
    category: Annotated[str | None, Query(min_length=1)] = None,
    payment_method: Annotated[str | None, Query(min_length=1)] = None,
) -> PaymentsListResponse:
    try:
        return PaymentsQueryService().list_payments(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            scope=scope,
            created_by_user_id=created_by_user_id,
            query=query,
            category_filter=category,
            payment_method_filter=payment_method,
        )
    except (BranchAccessError, OperationalPaymentError) as error:
        raise _to_http_exception(error) from error


@router.get("/{payment_id}", response_model=OperationalPaymentDetailResponse)
def get_payment_detail(
    payment_id: UUID,
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> OperationalPaymentDetailResponse:
    try:
        return PaymentsQueryService().get_payment_detail(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            payment_id=payment_id,
        )
    except (BranchAccessError, OperationalPaymentError) as error:
        raise _to_http_exception(error) from error


@router.post(
    "",
    response_model=OperationalPaymentDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payment(
    payload: CreateOperationalPaymentRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> OperationalPaymentDetailResponse:
    try:
        return PaymentsCommandService().create_payment(
            session,
            current_user=current_user,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except (BranchAccessError, OperationalPaymentError) as error:
        raise _to_http_exception(error) from error
