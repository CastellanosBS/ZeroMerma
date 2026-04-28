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
from zeromerma_api.modules.orders.application.schemas import (
    CancelCustomerOrderRequest,
    CreateCustomerOrderRequest,
    CustomerOrderDetailResponse,
    DeliverCustomerOrderRequest,
    OrderActionRequest,
    OrdersBootstrapResponse,
    OrdersCatalogResponse,
    OrdersClassProductsResponse,
    OrdersListResponse,
)
from zeromerma_api.modules.orders.application.services import (
    OrdersCommandService,
    OrdersQueryService,
)
from zeromerma_api.modules.orders.domain.exceptions import (
    OrderError,
    OrderNotFoundError,
    OrderStateConflictError,
    OrderValidationError,
)

router = APIRouter(prefix="/v1/orders", tags=["orders"])


def _to_http_exception(error: Exception) -> HTTPException:
    if isinstance(
        error,
        (
            WorkstationNotFoundError,
            ProductClassNotFoundError,
            ProductNotFoundError,
            OrderNotFoundError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))

    if isinstance(error, BranchAssignmentRequiredError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))

    if isinstance(error, (BranchInactiveError, WorkstationInactiveError, OrderStateConflictError)):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

    if isinstance(error, (BranchAccessError, CatalogError, OrderValidationError, OrderError)):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/bootstrap", response_model=OrdersBootstrapResponse)
def get_orders_bootstrap(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> OrdersBootstrapResponse:
    try:
        return OrdersQueryService().get_bootstrap(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
        )
    except (BranchAccessError, CatalogError, OrderError) as error:
        raise _to_http_exception(error) from error


@router.get("", response_model=OrdersListResponse)
def list_orders(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    status_filter: Annotated[str | None, Query(alias="status", min_length=1)] = None,
    query: Annotated[str | None, Query(min_length=1)] = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> OrdersListResponse:
    try:
        return OrdersQueryService().list_orders(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            status_filter=status_filter,
            query=query,
            date_from=date_from,
            date_to=date_to,
        )
    except (BranchAccessError, CatalogError, OrderError) as error:
        raise _to_http_exception(error) from error


@router.get("/catalog", response_model=OrdersCatalogResponse)
def get_orders_catalog(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    query: Annotated[str | None, Query(min_length=1)] = None,
) -> OrdersCatalogResponse:
    try:
        return OrdersQueryService().get_catalog(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            query=query,
        )
    except (BranchAccessError, CatalogError, OrderError) as error:
        raise _to_http_exception(error) from error


@router.get("/classes/{class_id}/products", response_model=OrdersClassProductsResponse)
def get_orders_class_products(
    class_id: UUID,
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    query: Annotated[str | None, Query(min_length=1)] = None,
) -> OrdersClassProductsResponse:
    try:
        return OrdersQueryService().get_class_products(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            class_id=class_id,
            query=query,
        )
    except (BranchAccessError, CatalogError, OrderError) as error:
        raise _to_http_exception(error) from error


@router.get("/{order_id}", response_model=CustomerOrderDetailResponse)
def get_order_detail(
    order_id: UUID,
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> CustomerOrderDetailResponse:
    try:
        return OrdersQueryService().get_order_detail(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            order_id=order_id,
        )
    except (BranchAccessError, CatalogError, OrderError) as error:
        raise _to_http_exception(error) from error


@router.post("", response_model=CustomerOrderDetailResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: CreateCustomerOrderRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> CustomerOrderDetailResponse:
    try:
        return OrdersCommandService().create_order(
            session,
            current_user=current_user,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except (BranchAccessError, CatalogError, OrderError) as error:
        raise _to_http_exception(error) from error


@router.post("/{order_id}/mark-ready", response_model=CustomerOrderDetailResponse)
def mark_order_ready(
    order_id: UUID,
    payload: OrderActionRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> CustomerOrderDetailResponse:
    try:
        return OrdersCommandService().mark_ready(
            session,
            current_user=current_user,
            order_id=order_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except (BranchAccessError, CatalogError, OrderError) as error:
        raise _to_http_exception(error) from error


@router.post("/{order_id}/deliver", response_model=CustomerOrderDetailResponse)
def deliver_order(
    order_id: UUID,
    payload: DeliverCustomerOrderRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> CustomerOrderDetailResponse:
    try:
        return OrdersCommandService().deliver_order(
            session,
            current_user=current_user,
            order_id=order_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except (BranchAccessError, CatalogError, OrderError) as error:
        raise _to_http_exception(error) from error


@router.post("/{order_id}/cancel", response_model=CustomerOrderDetailResponse)
def cancel_order(
    order_id: UUID,
    payload: CancelCustomerOrderRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> CustomerOrderDetailResponse:
    try:
        return OrdersCommandService().cancel_order(
            session,
            current_user=current_user,
            order_id=order_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except (BranchAccessError, CatalogError, OrderError) as error:
        raise _to_http_exception(error) from error
