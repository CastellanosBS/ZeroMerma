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
from zeromerma_api.modules.waste.application.admin_schemas import (
    AdminWasteCreateRequest,
    AdminWasteDetailView,
    AdminWasteListResponse,
    AdminWasteReasonView,
)
from zeromerma_api.modules.waste.application.admin_services import AdminWasteService
from zeromerma_api.modules.waste.domain.exceptions import WasteNotFoundError, WasteValidationError

admin_router = APIRouter(prefix="/v1/admin/waste", tags=["admin-waste"])


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
    if isinstance(error, WasteNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, WasteValidationError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected waste error.",
    )


def _parse_optional_datetime(value: str | None, *, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    if len(value) == 10:
        parsed = datetime.fromisoformat(value)
        if end_of_day:
            parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
        return parsed.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


@admin_router.get("", response_model=AdminWasteListResponse)
def list_admin_waste(
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    branch_id: Annotated[UUID | None, Query()] = None,
    class_id: Annotated[UUID | None, Query()] = None,
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
    evidence_state: Annotated[str | None, Query()] = None,
    impact_level: Annotated[str | None, Query()] = None,
    location_code: Annotated[str | None, Query(min_length=1)] = None,
    operator_user_id: Annotated[UUID | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    product_id: Annotated[UUID | None, Query()] = None,
    product_kind: Annotated[str | None, Query(min_length=1)] = None,
    reason_code: Annotated[str | None, Query(min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    warning_state: Annotated[str | None, Query()] = None,
) -> AdminWasteListResponse:
    _ = current_user
    try:
        return AdminWasteService().list_waste(
            session,
            branch_id=branch_id,
            class_id=class_id,
            date_from=_parse_optional_datetime(date_from),
            date_to=_parse_optional_datetime(date_to, end_of_day=True),
            evidence_state=evidence_state,
            impact_level=impact_level,
            location_code=location_code,
            operator_user_id=operator_user_id,
            page=page,
            page_size=page_size,
            product_id=product_id,
            product_kind=product_kind,
            reason_code=reason_code,
            search=search,
            status_filter=status_filter,
            warning_state=warning_state,
        )
    except (WasteNotFoundError, WasteValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.get("/reasons", response_model=list[AdminWasteReasonView])
def list_admin_waste_reasons(
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
) -> list[AdminWasteReasonView]:
    _ = current_user
    return AdminWasteService().list_reasons(session)


@admin_router.get("/{waste_id}", response_model=AdminWasteDetailView)
def get_admin_waste_detail(
    waste_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminWasteDetailView:
    _ = current_user
    try:
        return AdminWasteService().get_waste_detail(session, waste_id=waste_id)
    except (WasteNotFoundError, WasteValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post("", response_model=AdminWasteDetailView, status_code=status.HTTP_201_CREATED)
def create_admin_waste(
    command: AdminWasteCreateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminWasteDetailView:
    try:
        return AdminWasteService().create_waste(
            session,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (WasteNotFoundError, WasteValidationError) as error:
        raise _to_http_exception(error) from error

