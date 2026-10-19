from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from fastapi.responses import Response
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
from zeromerma_api.modules.production.application.admin_schemas import (
    AdminProductionCancelRequest,
    AdminProductionCompleteRequest,
    AdminProductionCreateRequest,
    AdminProductionDetailView,
    AdminProductionListResponse,
    AdminProductionStartRequest,
    AdminProductionUpdateRequest,
    ProductionCommandCode,
    ProductionCommandResultView,
)
from zeromerma_api.modules.production.application.admin_services import AdminProductionService
from zeromerma_api.modules.production.application.idempotency import ProductionIdempotencyService
from zeromerma_api.modules.production.domain.exceptions import (
    ProductionNotFoundError,
    ProductionValidationError,
)

admin_router = APIRouter(prefix="/v1/admin/production", tags=["admin-production"])
_REPLAY_RESPONSE = {
    "headers": {"Idempotency-Replayed": {"$ref": "#/components/headers/IdempotencyReplayed"}}
}


def _require_backoffice_user(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    if not user_can_access_surface(current_user, IDENTITY_SURFACE_BACKOFFICE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Backoffice access is required.",
        )
    return current_user


def _to_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, ProductionNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, ProductionValidationError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected production error.",
    )


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


@admin_router.get("", response_model=AdminProductionListResponse)
def list_admin_production(
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    branch_id: Annotated[UUID | None, Query()] = None,
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
    operator_user_id: Annotated[UUID | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    product_id: Annotated[UUID | None, Query()] = None,
    recipe_id: Annotated[UUID | None, Query()] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    status: Annotated[str | None, Query()] = None,
    variance_state: Annotated[str | None, Query()] = None,
    warning_state: Annotated[str | None, Query()] = None,
) -> AdminProductionListResponse:
    _ = current_user
    try:
        return AdminProductionService().list_production(
            session,
            branch_id=branch_id,
            date_from=_parse_optional_datetime(date_from),
            date_to=_parse_optional_datetime(date_to),
            operator_user_id=operator_user_id,
            page=page,
            page_size=page_size,
            product_id=product_id,
            recipe_id=recipe_id,
            search=search,
            status_filter=status,
            variance_state=variance_state,
            warning_state=warning_state,
        )
    except (ProductionNotFoundError, ProductionValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.get("/{production_id}", response_model=AdminProductionDetailView)
def get_admin_production_detail(
    production_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminProductionDetailView:
    _ = current_user
    try:
        return AdminProductionService().get_production_detail(session, production_id=production_id)
    except (ProductionNotFoundError, ProductionValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post(
    "",
    response_model=ProductionCommandResultView,
    status_code=201,
    responses={201: _REPLAY_RESPONSE},
)
def create_admin_production(
    command: AdminProductionCreateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    try:
        result = ProductionIdempotencyService().execute(
            session,
            command_code="create",
            command=command,
            current_user=current_user,
            key=key,
            request_id=request.headers.get("X-Request-ID"),
        )
        return idempotency_response(result, request)
    except (ProductionNotFoundError, ProductionValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.patch(
    "/{production_id}",
    response_model=ProductionCommandResultView,
    status_code=200,
    responses={200: _REPLAY_RESPONSE},
)
def update_admin_production(
    production_id: UUID,
    command: AdminProductionUpdateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    try:
        result = ProductionIdempotencyService().execute(
            session,
            command_code="update",
            command=command,
            current_user=current_user,
            key=key,
            request_id=request.headers.get("X-Request-ID"),
            production_id=production_id,
        )
        return idempotency_response(result, request)
    except (ProductionNotFoundError, ProductionValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post(
    "/{production_id}/start",
    response_model=ProductionCommandResultView,
    status_code=200,
    responses={200: _REPLAY_RESPONSE},
)
def start_admin_production(
    production_id: UUID,
    command: AdminProductionStartRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    try:
        result = ProductionIdempotencyService().execute(
            session,
            command_code="start",
            command=command,
            current_user=current_user,
            key=key,
            request_id=request.headers.get("X-Request-ID"),
            production_id=production_id,
        )
        return idempotency_response(result, request)
    except (ProductionNotFoundError, ProductionValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post(
    "/{production_id}/complete",
    response_model=ProductionCommandResultView,
    status_code=200,
    responses={200: _REPLAY_RESPONSE},
)
def complete_admin_production(
    production_id: UUID,
    command: AdminProductionCompleteRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    try:
        result = ProductionIdempotencyService().execute(
            session,
            command_code="complete",
            command=command,
            current_user=current_user,
            key=key,
            request_id=request.headers.get("X-Request-ID"),
            production_id=production_id,
        )
        return idempotency_response(result, request)
    except (ProductionNotFoundError, ProductionValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post(
    "/{production_id}/cancel",
    response_model=ProductionCommandResultView,
    status_code=200,
    responses={200: _REPLAY_RESPONSE},
)
def cancel_admin_production(
    production_id: UUID,
    command: AdminProductionCancelRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    try:
        result = ProductionIdempotencyService().execute(
            session,
            command_code="cancel",
            command=command,
            current_user=current_user,
            key=key,
            request_id=request.headers.get("X-Request-ID"),
            production_id=production_id,
        )
        return idempotency_response(result, request)
    except (ProductionNotFoundError, ProductionValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.get(
    "/commands/{command_code}/{idempotency_key}",
    response_model=ProductionCommandResultView,
    responses={200: _REPLAY_RESPONSE},
)
def recover_production_command(
    command_code: ProductionCommandCode,
    idempotency_key: Annotated[
        str, Path(min_length=36, max_length=36, pattern=IDEMPOTENCY_KEY_PATTERN)
    ],
    branch_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    result = ProductionIdempotencyService().recover(
        session,
        current_user=current_user,
        command_code=command_code,
        key=parse_idempotency_key(idempotency_key),
        branch_id=branch_id,
    )
    if result.status_code == 201:
        from dataclasses import replace

        result = replace(result, status_code=200)
    return idempotency_response(result, request)
