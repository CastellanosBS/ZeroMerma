from __future__ import annotations

from datetime import date
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
from zeromerma_api.modules.catalog.domain.exceptions import (
    CatalogError,
    ProductClassNotFoundError,
    ProductNotFoundError,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user
from zeromerma_api.modules.returns.application.schemas import (
    ReturnCommitRequest,
    ReturnOriginalSaleDetailResponse,
    ReturnsBootstrapResponse,
    ReturnsClassProductsResponse,
    ReturnsHistoryResponse,
    ReturnsSearchSalesResponse,
    SaleReturnDetailResponse,
)
from zeromerma_api.modules.returns.application.services import (
    ReturnsCommandService,
    ReturnsQueryService,
)
from zeromerma_api.modules.returns.domain.exceptions import (
    SaleReturnConflictError,
    SaleReturnError,
    SaleReturnNotFoundError,
    SaleReturnValidationError,
)

router = APIRouter(prefix="/v1/returns", tags=["returns"])


def _to_http_exception(error: Exception) -> HTTPException:
    if isinstance(
        error,
        (
            WorkstationNotFoundError,
            ProductClassNotFoundError,
            ProductNotFoundError,
            SaleReturnNotFoundError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))

    if isinstance(error, BranchAssignmentRequiredError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))

    if isinstance(error, (BranchInactiveError, WorkstationInactiveError, SaleReturnConflictError)):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

    if isinstance(
        error,
        (BranchAccessError, CatalogError, SaleReturnValidationError, SaleReturnError),
    ):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/bootstrap", response_model=ReturnsBootstrapResponse)
def get_returns_bootstrap(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> ReturnsBootstrapResponse:
    try:
        return ReturnsQueryService().get_bootstrap(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
        )
    except (BranchAccessError, CatalogError, SaleReturnError) as error:
        raise _to_http_exception(error) from error


@router.get("/search-sales", response_model=ReturnsSearchSalesResponse)
def search_return_sales(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    scope: Annotated[str | None, Query(min_length=1)] = None,
    query: Annotated[str | None, Query(min_length=1)] = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> ReturnsSearchSalesResponse:
    try:
        return ReturnsQueryService().search_sales(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            scope=scope,
            query=query,
            date_from=date_from,
            date_to=date_to,
        )
    except (BranchAccessError, CatalogError, SaleReturnError) as error:
        raise _to_http_exception(error) from error


@router.get("/history", response_model=ReturnsHistoryResponse)
def list_return_history(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    scope: Annotated[str | None, Query(min_length=1)] = None,
    query: Annotated[str | None, Query(min_length=1)] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    created_by_user_id: UUID | None = None,
    reason_code: Annotated[str | None, Query(min_length=1)] = None,
) -> ReturnsHistoryResponse:
    try:
        return ReturnsQueryService().list_return_history(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            scope=scope,
            query=query,
            date_from=date_from,
            date_to=date_to,
            created_by_user_id=created_by_user_id,
            reason_code=reason_code,
        )
    except (BranchAccessError, CatalogError, SaleReturnError) as error:
        raise _to_http_exception(error) from error


@router.get("/sales/{sale_id}", response_model=ReturnOriginalSaleDetailResponse)
def get_return_sale_detail(
    sale_id: UUID,
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> ReturnOriginalSaleDetailResponse:
    try:
        return ReturnsQueryService().get_original_sale_detail(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            sale_id=sale_id,
        )
    except (BranchAccessError, CatalogError, SaleReturnError) as error:
        raise _to_http_exception(error) from error


@router.get("/classes/{class_id}/products", response_model=ReturnsClassProductsResponse)
def get_returns_class_products(
    class_id: UUID,
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    query: Annotated[str | None, Query(min_length=1)] = None,
) -> ReturnsClassProductsResponse:
    try:
        return ReturnsQueryService().get_class_products(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            class_id=class_id,
            query=query,
        )
    except (BranchAccessError, CatalogError, SaleReturnError) as error:
        raise _to_http_exception(error) from error


@router.post(
    "/commit",
    response_model=SaleReturnDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def commit_sale_return(
    payload: ReturnCommitRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> SaleReturnDetailResponse:
    try:
        return ReturnsCommandService().commit_return(
            session,
            current_user=current_user,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except (BranchAccessError, CatalogError, SaleReturnError) as error:
        raise _to_http_exception(error) from error


@router.get("/{return_id}", response_model=SaleReturnDetailResponse)
def get_sale_return_detail(
    return_id: UUID,
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> SaleReturnDetailResponse:
    try:
        return ReturnsQueryService().get_sale_return_detail(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            return_id=return_id,
        )
    except (BranchAccessError, CatalogError, SaleReturnError) as error:
        raise _to_http_exception(error) from error
