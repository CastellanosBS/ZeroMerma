from __future__ import annotations

from dataclasses import replace
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
from zeromerma_api.modules.catalog.domain.exceptions import (
    CatalogError,
    ProductClassNotFoundError,
    ProductNotFoundError,
    ProductSelectionNotAllowedError,
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
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user
from zeromerma_api.modules.sales.application.idempotency import SaleConfirmationService
from zeromerma_api.modules.sales.application.schemas import (
    ConfirmSaleRequest,
    SaleConfirmationView,
    SaleDetailView,
)
from zeromerma_api.modules.sales.application.services import SaleQueryService
from zeromerma_api.modules.sales.domain.exceptions import (
    InsufficientCashPaymentError,
    OpenCashSessionRequiredError,
    SaleError,
    SaleNotFoundError,
    SaleValidationError,
    UnsupportedPaymentMethodError,
)

router = APIRouter(prefix="/v1/sales", tags=["sales"])


def _to_http_exception(error: Exception) -> HTTPException:
    if isinstance(
        error,
        (
            WorkstationNotFoundError,
            ProductClassNotFoundError,
            ProductNotFoundError,
            SaleNotFoundError,
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
            ProductSelectionNotAllowedError,
            OpenCashSessionRequiredError,
            UnsupportedPaymentMethodError,
            InsufficientCashPaymentError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

    if isinstance(error, (BranchAccessError, CatalogError, SaleValidationError, SaleError)):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.post(
    "/confirm",
    response_model=SaleConfirmationView,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "headers": {
                "Idempotency-Replayed": {"$ref": "#/components/headers/IdempotencyReplayed"}
            }
        }
    },
)
def confirm_sale(
    payload: ConfirmSaleRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    try:
        result = SaleConfirmationService().confirm(
            session,
            current_user=current_user,
            command=payload,
            key=key,
            request_id=request.headers.get("X-Request-ID"),
        )
        return idempotency_response(result, request)
    except (BranchAccessError, CatalogError, SaleError) as error:
        raise _to_http_exception(error) from error


@router.get(
    "/confirmations/{idempotency_key}",
    response_model=SaleConfirmationView,
    responses={
        200: {
            "headers": {
                "Idempotency-Replayed": {"$ref": "#/components/headers/IdempotencyReplayed"}
            }
        }
    },
)
def recover_sale_confirmation(
    idempotency_key: Annotated[
        str, Path(min_length=36, max_length=36, pattern=IDEMPOTENCY_KEY_PATTERN)
    ],
    workstation_code: Annotated[str, Query(min_length=1, max_length=64)],
    cash_session_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    result = SaleConfirmationService().recover(
        session,
        current_user=current_user,
        key=parse_idempotency_key(idempotency_key),
        workstation_code=workstation_code,
        cash_session_id=cash_session_id,
    )
    recovered = (
        replace(result, status_code=status.HTTP_200_OK) if result.status == "COMPLETED" else result
    )
    return idempotency_response(recovered, request)


@router.get("/{sale_id}", response_model=SaleDetailView)
def get_sale(
    sale_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> SaleDetailView:
    try:
        return SaleQueryService().get_sale_by_id(
            session,
            sale_id=sale_id,
            user_id=current_user.id,
        )
    except SaleError as error:
        raise _to_http_exception(error) from error
