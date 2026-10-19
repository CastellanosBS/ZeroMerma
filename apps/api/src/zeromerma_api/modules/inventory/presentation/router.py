from __future__ import annotations

from dataclasses import replace
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response, status
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
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
from zeromerma_api.modules.inventory.application.admin_schemas import (
    AdminInventoryAdjustmentRequest,
    AdminInventoryAdjustmentResultView,
    AdminInventoryDetailView,
    AdminInventoryListResponse,
    AdminInventoryMovementsResponse,
)
from zeromerma_api.modules.inventory.application.admin_services import AdminInventoryService
from zeromerma_api.modules.inventory.application.idempotency import AdminInventoryAdjustmentService
from zeromerma_api.modules.inventory.domain.exceptions import (
    InventoryError,
    InventoryNotFoundError,
    InventoryValidationError,
)
from zeromerma_api.presentation.errors import error_responses

_REPLAY_RESPONSE = {
    "headers": {"Idempotency-Replayed": {"$ref": "#/components/headers/IdempotencyReplayed"}}
}

admin_router = APIRouter(prefix="/v1/admin/inventory", tags=["admin-inventory"])


def _require_backoffice_user(current_user: AuthenticatedUser) -> None:
    if not user_can_access_surface(current_user, IDENTITY_SURFACE_BACKOFFICE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Backoffice access is required.",
        )


def _to_http_exception(error: InventoryError) -> HTTPException:
    if isinstance(error, InventoryNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, InventoryValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@admin_router.get("", response_model=AdminInventoryListResponse)
def list_admin_inventory(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    branch_id: UUID | None = None,
    class_id: UUID | None = None,
    location_code: Annotated[str | None, Query(min_length=1)] = None,
    product_kind: Annotated[str | None, Query(min_length=1)] = None,
    product_status: Annotated[str | None, Query(min_length=1)] = None,
    stock_state: Annotated[str | None, Query(min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AdminInventoryListResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminInventoryService().list_inventory(
            session,
            branch_id=branch_id,
            class_id=class_id,
            location_code=location_code,
            product_kind=product_kind,
            product_status=product_status,
            stock_state=stock_state,
            search=search,
            page=page,
            page_size=page_size,
        )
    except InventoryError as error:
        raise _to_http_exception(error) from error


@admin_router.get("/{balance_id}", response_model=AdminInventoryDetailView)
def get_admin_inventory_detail(
    balance_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminInventoryDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminInventoryService().get_inventory_detail(session, balance_id=balance_id)
    except InventoryError as error:
        raise _to_http_exception(error) from error


@admin_router.get("/{balance_id}/movements", response_model=AdminInventoryMovementsResponse)
def list_admin_inventory_movements(
    balance_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AdminInventoryMovementsResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminInventoryService().list_movements(
            session,
            balance_id=balance_id,
            page=page,
            page_size=page_size,
        )
    except InventoryError as error:
        raise _to_http_exception(error) from error


@admin_router.post(
    "/adjustments",
    response_model=AdminInventoryAdjustmentResultView,
    status_code=status.HTTP_201_CREATED,
    responses={201: _REPLAY_RESPONSE, 409: {**error_responses()[409], **_REPLAY_RESPONSE}},
)
def create_admin_inventory_adjustment(
    payload: AdminInventoryAdjustmentRequest,
    request: Request,
    idempotency_key: Annotated[UUID, Depends(require_idempotency_key)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    _require_backoffice_user(current_user)
    try:
        result = AdminInventoryAdjustmentService().commit(
            session,
            current_user=current_user,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
            key=idempotency_key,
        )
        return idempotency_response(result, request)
    except InventoryError as error:
        raise _to_http_exception(error) from error


@admin_router.get(
    "/adjustments/confirmations/{idempotency_key}",
    response_model=AdminInventoryAdjustmentResultView,
    responses={200: _REPLAY_RESPONSE, 409: {**error_responses()[409], **_REPLAY_RESPONSE}},
)
def recover_create_admin_inventory_adjustment(
    idempotency_key: Annotated[str, Path(pattern=IDEMPOTENCY_KEY_PATTERN)],
    branch_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    result = AdminInventoryAdjustmentService().recover(
        session,
        current_user=current_user,
        key=parse_idempotency_key(idempotency_key),
        branch_id=branch_id,
    )
    if result.status_code < 300:
        result = replace(result, status_code=200)
    return idempotency_response(result, request)
