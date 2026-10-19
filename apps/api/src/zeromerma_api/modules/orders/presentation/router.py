from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
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
)
from zeromerma_api.modules.financial_ledger.application.refund_commands import (
    RefundSettlementService,
)
from zeromerma_api.modules.financial_ledger.application.refund_schemas import (
    FinancialRefundView,
    RefundSettlementCommand,
    RefundSettlementRequest,
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
from zeromerma_api.modules.identity.application.services import user_can_access_surface
from zeromerma_api.modules.identity.domain.constants import IDENTITY_SURFACE_BACKOFFICE
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user
from zeromerma_api.modules.orders.application.admin_schemas import (
    AdminOrderActionRequest,
    AdminOrderDetailView,
    AdminOrdersListResponse,
)
from zeromerma_api.modules.orders.application.admin_services import AdminOrdersService
from zeromerma_api.modules.orders.application.idempotency import OrdersIdempotencyService
from zeromerma_api.modules.orders.application.schemas import (
    AdminOrderCommandCode,
    CancelCustomerOrderRequest,
    CreateCustomerOrderRequest,
    CustomerOrderDetailResponse,
    DeliverCustomerOrderRequest,
    OrderActionRequest,
    OrderCommandCode,
    OrderCommandResultView,
    OrdersBootstrapResponse,
    OrdersCatalogResponse,
    OrdersClassProductsResponse,
    OrdersListResponse,
)
from zeromerma_api.modules.orders.application.services import (
    OrdersQueryService,
)
from zeromerma_api.modules.orders.domain.exceptions import (
    OrderError,
    OrderNotFoundError,
    OrderStateConflictError,
    OrderValidationError,
)

router = APIRouter(prefix="/v1/orders", tags=["orders"])
admin_router = APIRouter(prefix="/v1/admin/orders", tags=["admin-orders"])
_REPLAY_RESPONSE = {
    "headers": {"Idempotency-Replayed": {"$ref": "#/components/headers/IdempotencyReplayed"}}
}


def _require_backoffice_user(current_user: AuthenticatedUser) -> AuthenticatedUser:
    if not user_can_access_surface(current_user, IDENTITY_SURFACE_BACKOFFICE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Backoffice access is required.",
        )
    return current_user


@router.post(
    "/{order_id}/refund-settlements",
    response_model=FinancialRefundView,
    responses={200: _REPLAY_RESPONSE},
)
def settle_orders_refund(
    order_id: UUID,
    payload: RefundSettlementRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    result = RefundSettlementService("ORDER_CANCELLATION").settle(
        session,
        current_user=current_user,
        command=RefundSettlementCommand(source_id=order_id, **payload.model_dump()),
        key=key,
        request_id=request.headers.get("X-Request-ID"),
    )
    return idempotency_response(result, request)


@router.get(
    "/refund-settlements/{idempotency_key}",
    response_model=FinancialRefundView,
    responses={200: _REPLAY_RESPONSE},
)
def recover_orders_refund_settlement(
    idempotency_key: Annotated[
        str, Path(min_length=36, max_length=36, pattern=IDEMPOTENCY_KEY_PATTERN)
    ],
    workstation_code: Annotated[str, Query(min_length=1, max_length=64)],
    cash_session_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    result = RefundSettlementService("ORDER_CANCELLATION").recover(
        session,
        current_user=current_user,
        key=parse_idempotency_key(idempotency_key),
        workstation_code=workstation_code,
        cash_session_id=cash_session_id,
    )
    return idempotency_response(result, request)


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


@admin_router.get("", response_model=AdminOrdersListResponse)
def list_admin_orders(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    branch_id: UUID | None = None,
    cashier_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="page_size", ge=1, le=100)] = 25,
    payment_state: Annotated[str | None, Query(min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status", min_length=1)] = None,
    workstation_id: UUID | None = None,
) -> AdminOrdersListResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminOrdersService().list_orders(
            session,
            branch_id=branch_id,
            cashier_id=cashier_id,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
            payment_state=payment_state,
            search=search,
            status_filter=status_filter,
            workstation_id=workstation_id,
        )
    except OrderError as error:
        raise _to_http_exception(error) from error


@admin_router.get("/{order_id}", response_model=AdminOrderDetailView)
def get_admin_order_detail(
    order_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminOrderDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminOrdersService().get_order_detail(session, order_id=order_id)
    except OrderError as error:
        raise _to_http_exception(error) from error


@admin_router.post(
    "/{order_id}/mark-ready",
    response_model=OrderCommandResultView,
    responses={200: _REPLAY_RESPONSE},
)
def mark_admin_order_ready(
    order_id: UUID,
    payload: AdminOrderActionRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    _require_backoffice_user(current_user)
    try:
        result = OrdersIdempotencyService().execute_admin(
            session,
            current_user=current_user,
            command_code="mark-ready",
            key=key,
            order_id=order_id,
            request_id=request.headers.get("X-Request-ID"),
        )
        return idempotency_response(result, request)
    except OrderError as error:
        raise _to_http_exception(error) from error


@admin_router.post(
    "/{order_id}/deliver", response_model=OrderCommandResultView, responses={200: _REPLAY_RESPONSE}
)
def deliver_admin_order(
    order_id: UUID,
    payload: AdminOrderActionRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    _require_backoffice_user(current_user)
    try:
        result = OrdersIdempotencyService().execute_admin(
            session,
            current_user=current_user,
            command_code="deliver",
            key=key,
            order_id=order_id,
            request_id=request.headers.get("X-Request-ID"),
        )
        return idempotency_response(result, request)
    except OrderError as error:
        raise _to_http_exception(error) from error


@admin_router.post(
    "/{order_id}/cancel", response_model=OrderCommandResultView, responses={200: _REPLAY_RESPONSE}
)
def cancel_admin_order(
    order_id: UUID,
    payload: AdminOrderActionRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    _require_backoffice_user(current_user)
    try:
        result = OrdersIdempotencyService().execute_admin(
            session,
            current_user=current_user,
            command_code="cancel",
            key=key,
            order_id=order_id,
            request_id=request.headers.get("X-Request-ID"),
        )
        return idempotency_response(result, request)
    except OrderError as error:
        raise _to_http_exception(error) from error


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


@router.post(
    "",
    response_model=OrderCommandResultView,
    status_code=status.HTTP_201_CREATED,
    responses={201: _REPLAY_RESPONSE},
)
def create_order(
    payload: CreateCustomerOrderRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    try:
        result = OrdersIdempotencyService().execute_pos(
            session,
            current_user=current_user,
            command_code="create",
            key=key,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
        return idempotency_response(result, request)
    except (BranchAccessError, CatalogError, OrderError) as error:
        raise _to_http_exception(error) from error


@router.post(
    "/{order_id}/mark-ready",
    response_model=OrderCommandResultView,
    responses={200: _REPLAY_RESPONSE},
)
def mark_order_ready(
    order_id: UUID,
    payload: OrderActionRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    try:
        result = OrdersIdempotencyService().execute_pos(
            session,
            current_user=current_user,
            command_code="mark-ready",
            key=key,
            order_id=order_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
        return idempotency_response(result, request)
    except (BranchAccessError, CatalogError, OrderError) as error:
        raise _to_http_exception(error) from error


@router.post(
    "/{order_id}/deliver", response_model=OrderCommandResultView, responses={200: _REPLAY_RESPONSE}
)
def deliver_order(
    order_id: UUID,
    payload: DeliverCustomerOrderRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    try:
        result = OrdersIdempotencyService().execute_pos(
            session,
            current_user=current_user,
            command_code="deliver",
            key=key,
            order_id=order_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
        return idempotency_response(result, request)
    except (BranchAccessError, CatalogError, OrderError) as error:
        raise _to_http_exception(error) from error


@router.post(
    "/{order_id}/cancel", response_model=OrderCommandResultView, responses={200: _REPLAY_RESPONSE}
)
def cancel_order(
    order_id: UUID,
    payload: CancelCustomerOrderRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    try:
        result = OrdersIdempotencyService().execute_pos(
            session,
            current_user=current_user,
            command_code="cancel",
            key=key,
            order_id=order_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
        return idempotency_response(result, request)
    except (BranchAccessError, CatalogError, OrderError) as error:
        raise _to_http_exception(error) from error


@router.get(
    "/commands/{command_code}/{idempotency_key}",
    response_model=OrderCommandResultView,
    responses={200: _REPLAY_RESPONSE},
)
def recover_order_command(
    command_code: OrderCommandCode,
    idempotency_key: Annotated[
        str, Path(min_length=36, max_length=36, pattern=IDEMPOTENCY_KEY_PATTERN)
    ],
    workstation_code: Annotated[str, Query(min_length=1, max_length=64)],
    cash_session_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    result = OrdersIdempotencyService().recover_pos(
        session,
        current_user=current_user,
        command_code=command_code,
        key=parse_idempotency_key(idempotency_key),
        workstation_code=workstation_code,
        cash_session_id=cash_session_id,
    )
    if result.status == "COMPLETED":
        result = replace(result, status_code=status.HTTP_200_OK)
    return idempotency_response(result, request)


@admin_router.get(
    "/commands/{command_code}/{idempotency_key}",
    response_model=OrderCommandResultView,
    responses={200: _REPLAY_RESPONSE},
)
def recover_admin_order_command(
    command_code: AdminOrderCommandCode,
    idempotency_key: Annotated[
        str, Path(min_length=36, max_length=36, pattern=IDEMPOTENCY_KEY_PATTERN)
    ],
    branch_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    result = OrdersIdempotencyService().recover_admin(
        session,
        current_user=current_user,
        command_code=command_code,
        key=parse_idempotency_key(idempotency_key),
        branch_id=branch_id,
    )
    if result.status == "COMPLETED":
        result = replace(result, status_code=status.HTTP_200_OK)
    return idempotency_response(result, request)
