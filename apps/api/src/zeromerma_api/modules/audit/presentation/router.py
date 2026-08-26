from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.modules.audit.application.admin_schemas import (
    AdminAuditEventDetailView,
    AdminAuditEventsListResponse,
    AdminAuditExportResponse,
)
from zeromerma_api.modules.audit.application.admin_services import AdminAuditService
from zeromerma_api.modules.audit.domain.exceptions import AuditEventNotFoundError
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.application.services import user_can_access_surface
from zeromerma_api.modules.identity.domain.constants import IDENTITY_SURFACE_BACKOFFICE
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user

admin_router = APIRouter(prefix="/v1/admin/audit", tags=["admin-audit"])


def _require_backoffice_user(current_user: AuthenticatedUser) -> None:
    if not user_can_access_surface(current_user, IDENTITY_SURFACE_BACKOFFICE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Backoffice access is required.",
        )


@admin_router.get("", response_model=AdminAuditEventsListResponse)
def list_admin_audit_events(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    actor_user_id: UUID | None = None,
    actor_email: Annotated[str | None, Query(min_length=1)] = None,
    module: Annotated[str | None, Query(min_length=1)] = None,
    action: Annotated[str | None, Query(min_length=1)] = None,
    entity_type: Annotated[str | None, Query(min_length=1)] = None,
    entity_id: Annotated[str | None, Query(min_length=1)] = None,
    branch_id: UUID | None = None,
    workstation: Annotated[str | None, Query(min_length=1)] = None,
    severity: Annotated[str | None, Query(min_length=1)] = None,
    sensitive: Annotated[str | None, Query(min_length=1)] = None,
    result: Annotated[str | None, Query(min_length=1)] = None,
    source_app: Annotated[str | None, Query(min_length=1)] = None,
    related_reference: Annotated[str | None, Query(min_length=1)] = None,
    warning_state: Annotated[str | None, Query(min_length=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AdminAuditEventsListResponse:
    _require_backoffice_user(current_user)
    return AdminAuditService().list_events(
        session,
        date_from=date_from,
        date_to=date_to,
        search=search,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        module=module,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        branch_id=branch_id,
        workstation=workstation,
        severity=severity,
        sensitive=sensitive,
        result=result,
        source_app=source_app,
        related_reference=related_reference,
        warning_state=warning_state,
        page=page,
        page_size=page_size,
    )


@admin_router.get("/export", response_model=AdminAuditExportResponse)
def export_admin_audit_events(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    actor_user_id: UUID | None = None,
    actor_email: Annotated[str | None, Query(min_length=1)] = None,
    module: Annotated[str | None, Query(min_length=1)] = None,
    action: Annotated[str | None, Query(min_length=1)] = None,
    entity_type: Annotated[str | None, Query(min_length=1)] = None,
    entity_id: Annotated[str | None, Query(min_length=1)] = None,
    branch_id: UUID | None = None,
    workstation: Annotated[str | None, Query(min_length=1)] = None,
    severity: Annotated[str | None, Query(min_length=1)] = None,
    sensitive: Annotated[str | None, Query(min_length=1)] = None,
    result: Annotated[str | None, Query(min_length=1)] = None,
    source_app: Annotated[str | None, Query(min_length=1)] = None,
    related_reference: Annotated[str | None, Query(min_length=1)] = None,
    warning_state: Annotated[str | None, Query(min_length=1)] = None,
) -> AdminAuditExportResponse:
    _require_backoffice_user(current_user)
    return AdminAuditService().export_events(
        session,
        date_from=date_from,
        date_to=date_to,
        search=search,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        module=module,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        branch_id=branch_id,
        workstation=workstation,
        severity=severity,
        sensitive=sensitive,
        result=result,
        source_app=source_app,
        related_reference=related_reference,
        warning_state=warning_state,
    )


@admin_router.get("/{event_id}", response_model=AdminAuditEventDetailView)
def get_admin_audit_event_detail(
    event_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminAuditEventDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminAuditService().get_event_detail(session, event_id=event_id)
    except AuditEventNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
