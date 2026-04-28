from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
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
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user
from zeromerma_api.modules.sales.application.schemas import ConfirmSaleRequest, SaleDetailView
from zeromerma_api.modules.sales.application.services import SaleCommandService, SaleQueryService
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


@router.post("/confirm", response_model=SaleDetailView, status_code=status.HTTP_201_CREATED)
def confirm_sale(
    payload: ConfirmSaleRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> SaleDetailView:
    try:
        return SaleCommandService().confirm_sale(
            session,
            current_user=current_user,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except (BranchAccessError, CatalogError, SaleError) as error:
        raise _to_http_exception(error) from error


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

