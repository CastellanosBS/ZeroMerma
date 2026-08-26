from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.modules.configuration.application.admin_schemas import (
    AdminSettingDetailView,
    AdminSettingResetRequest,
    AdminSettingsListResponse,
    AdminSettingUpdateRequest,
)
from zeromerma_api.modules.configuration.application.admin_services import AdminSettingService
from zeromerma_api.modules.configuration.domain.exceptions import (
    SettingAdminError,
    SettingNotFoundError,
    SettingReadonlyError,
    SettingSensitiveConfirmationError,
    SettingValidationError,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.application.services import user_can_access_surface
from zeromerma_api.modules.identity.domain.constants import IDENTITY_SURFACE_BACKOFFICE
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user

admin_router = APIRouter(prefix="/v1/admin/settings", tags=["admin-settings"])


def _require_backoffice_user(current_user: AuthenticatedUser) -> None:
    if not user_can_access_surface(current_user, IDENTITY_SURFACE_BACKOFFICE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Backoffice access is required.",
        )


def _to_admin_http_exception(error: SettingAdminError) -> HTTPException:
    if isinstance(error, SettingNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, SettingReadonlyError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, SettingSensitiveConfirmationError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, SettingValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@admin_router.get("", response_model=AdminSettingsListResponse)
def list_admin_settings(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    search: Annotated[str | None, Query(min_length=1)] = None,
    category: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status", min_length=1)] = None,
    sensitivity: Annotated[str | None, Query(min_length=1)] = None,
    readonly: Annotated[str | None, Query(min_length=1)] = None,
    scope: Annotated[str | None, Query(min_length=1)] = None,
    affected_module: Annotated[str | None, Query(min_length=1)] = None,
) -> AdminSettingsListResponse:
    _require_backoffice_user(current_user)
    return AdminSettingService().list_settings(
        session,
        affected_module=affected_module,
        category=category,
        readonly=readonly,
        scope=scope,
        search=search,
        sensitivity=sensitivity,
        status_filter=status_filter,
    )


@admin_router.get("/{setting_key:path}", response_model=AdminSettingDetailView)
def get_admin_setting_detail(
    setting_key: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminSettingDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminSettingService().get_setting_detail(session, key=setting_key)
    except SettingAdminError as error:
        raise _to_admin_http_exception(error) from error


@admin_router.patch("/{setting_key:path}", response_model=AdminSettingDetailView)
def update_admin_setting(
    setting_key: str,
    payload: AdminSettingUpdateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminSettingDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminSettingService().update_setting(
            session,
            change_note=payload.change_note,
            confirm_sensitive=payload.confirm_sensitive,
            current_user=current_user,
            key=setting_key,
            request_id=request.headers.get("X-Request-ID"),
            value=payload.value,
        )
    except SettingAdminError as error:
        raise _to_admin_http_exception(error) from error


@admin_router.post("/{setting_key:path}/reset", response_model=AdminSettingDetailView)
def reset_admin_setting(
    setting_key: str,
    payload: AdminSettingResetRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminSettingDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminSettingService().reset_setting(
            session,
            change_note=payload.change_note,
            confirm_sensitive=payload.confirm_sensitive,
            current_user=current_user,
            key=setting_key,
            request_id=request.headers.get("X-Request-ID"),
        )
    except SettingAdminError as error:
        raise _to_admin_http_exception(error) from error
