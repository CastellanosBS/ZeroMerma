from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
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
)
from zeromerma_api.modules.production.application.admin_services import AdminProductionService
from zeromerma_api.modules.production.domain.exceptions import (
    ProductionNotFoundError,
    ProductionValidationError,
)

admin_router = APIRouter(prefix="/v1/admin/production", tags=["admin-production"])


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
    response_model=AdminProductionDetailView,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_production(
    command: AdminProductionCreateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminProductionDetailView:
    try:
        return AdminProductionService().create_production(
            session,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (ProductionNotFoundError, ProductionValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.patch("/{production_id}", response_model=AdminProductionDetailView)
def update_admin_production(
    production_id: UUID,
    command: AdminProductionUpdateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminProductionDetailView:
    try:
        return AdminProductionService().update_production(
            session,
            command=command,
            current_user=current_user,
            production_id=production_id,
            request_id=request_id,
        )
    except (ProductionNotFoundError, ProductionValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post("/{production_id}/start", response_model=AdminProductionDetailView)
def start_admin_production(
    production_id: UUID,
    command: AdminProductionStartRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminProductionDetailView:
    try:
        return AdminProductionService().start_production(
            session,
            command=command,
            current_user=current_user,
            production_id=production_id,
            request_id=request_id,
        )
    except (ProductionNotFoundError, ProductionValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post("/{production_id}/complete", response_model=AdminProductionDetailView)
def complete_admin_production(
    production_id: UUID,
    command: AdminProductionCompleteRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminProductionDetailView:
    try:
        return AdminProductionService().complete_production(
            session,
            command=command,
            current_user=current_user,
            production_id=production_id,
            request_id=request_id,
        )
    except (ProductionNotFoundError, ProductionValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post("/{production_id}/cancel", response_model=AdminProductionDetailView)
def cancel_admin_production(
    production_id: UUID,
    command: AdminProductionCancelRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminProductionDetailView:
    try:
        return AdminProductionService().cancel_production(
            session,
            command=command,
            current_user=current_user,
            production_id=production_id,
            request_id=request_id,
        )
    except (ProductionNotFoundError, ProductionValidationError) as error:
        raise _to_http_exception(error) from error

