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
from zeromerma_api.modules.quality.application.cleaning_schemas import (
    AdminCleaningLogCancelRequest,
    AdminCleaningLogCompleteRequest,
    AdminCleaningLogCreateRequest,
    AdminCleaningLogDetailView,
    AdminCleaningLogListResponse,
    AdminCleaningTemplateView,
)
from zeromerma_api.modules.quality.application.cleaning_services import AdminCleaningLogService
from zeromerma_api.modules.quality.application.equipment_schemas import (
    AdminEquipmentCreateRequest,
    AdminEquipmentDetailView,
    AdminEquipmentListResponse,
    AdminEquipmentStatusRequest,
    AdminEquipmentUpdateRequest,
    AdminMaintenanceCancelRequest,
    AdminMaintenanceCompleteRequest,
    AdminMaintenanceCreateRequest,
)
from zeromerma_api.modules.quality.application.equipment_services import (
    AdminEquipmentMaintenanceService,
)
from zeromerma_api.modules.quality.application.incident_schemas import (
    AdminIncidentCreateRequest,
    AdminIncidentDetailView,
    AdminIncidentFollowUpCreateRequest,
    AdminIncidentListResponse,
    AdminIncidentResolveRequest,
    AdminIncidentStatusRequest,
    AdminIncidentUpdateRequest,
)
from zeromerma_api.modules.quality.application.incident_services import AdminIncidentService
from zeromerma_api.modules.quality.application.sanitary_schemas import (
    AdminSanitaryTemplateView,
    AdminSanitaryVerificationCancelRequest,
    AdminSanitaryVerificationCompleteRequest,
    AdminSanitaryVerificationCreateRequest,
    AdminSanitaryVerificationDetailView,
    AdminSanitaryVerificationListResponse,
)
from zeromerma_api.modules.quality.application.sanitary_services import (
    AdminSanitaryVerificationService,
)
from zeromerma_api.modules.quality.domain.exceptions import (
    CleaningLogNotFoundError,
    CleaningLogValidationError,
    EquipmentMaintenanceValidationError,
    EquipmentNotFoundError,
    IncidentNotFoundError,
    IncidentValidationError,
    MaintenanceRecordNotFoundError,
    SanitaryVerificationNotFoundError,
    SanitaryVerificationValidationError,
)

admin_cleaning_logs_router = APIRouter(
    prefix="/v1/admin/cleaning-logs",
    tags=["admin-cleaning-logs"],
)

admin_sanitary_verifications_router = APIRouter(
    prefix="/v1/admin/sanitary-verifications",
    tags=["admin-sanitary-verifications"],
)

admin_equipment_maintenance_router = APIRouter(
    prefix="/v1/admin/equipment-maintenance",
    tags=["admin-equipment-maintenance"],
)

admin_incidents_router = APIRouter(
    prefix="/v1/admin/incidents",
    tags=["admin-incidents"],
)


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
    if isinstance(error, CleaningLogNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, CleaningLogValidationError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected cleaning log error.",
    )


def _to_sanitary_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, SanitaryVerificationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, SanitaryVerificationValidationError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected sanitary verification error.",
    )


def _to_equipment_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, (EquipmentNotFoundError, MaintenanceRecordNotFoundError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, EquipmentMaintenanceValidationError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected equipment maintenance error.",
    )


def _to_incident_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, IncidentNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, IncidentValidationError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected incident error.",
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
    return parsed.astimezone(UTC)


@admin_cleaning_logs_router.get("", response_model=AdminCleaningLogListResponse)
def list_admin_cleaning_logs(
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    area_name: Annotated[str | None, Query(min_length=1)] = None,
    area_type: Annotated[str | None, Query(min_length=1)] = None,
    branch_id: Annotated[UUID | None, Query()] = None,
    cleaning_type: Annotated[str | None, Query(min_length=1)] = None,
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
    evidence_state: Annotated[str | None, Query(min_length=1)] = None,
    observation_state: Annotated[str | None, Query(min_length=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    responsible_user_id: Annotated[UUID | None, Query()] = None,
    risk_level: Annotated[str | None, Query(min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    shift_code: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    template_id: Annotated[UUID | None, Query()] = None,
    warning_state: Annotated[str | None, Query(min_length=1)] = None,
) -> AdminCleaningLogListResponse:
    _ = current_user
    try:
        return AdminCleaningLogService().list_logs(
            session,
            area_name=area_name,
            area_type=area_type,
            branch_id=branch_id,
            cleaning_type=cleaning_type,
            date_from=_parse_optional_datetime(date_from),
            date_to=_parse_optional_datetime(date_to, end_of_day=True),
            evidence_state=evidence_state,
            observation_state=observation_state,
            page=page,
            page_size=page_size,
            responsible_user_id=responsible_user_id,
            risk_level=risk_level,
            search=search,
            shift_code=shift_code,
            status_filter=status_filter,
            template_id=template_id,
            warning_state=warning_state,
        )
    except (CleaningLogNotFoundError, CleaningLogValidationError) as error:
        raise _to_http_exception(error) from error


@admin_cleaning_logs_router.get("/templates", response_model=list[AdminCleaningTemplateView])
def list_admin_cleaning_templates(
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
) -> list[AdminCleaningTemplateView]:
    _ = current_user
    return AdminCleaningLogService().list_templates(session)


@admin_cleaning_logs_router.get("/{cleaning_log_id}", response_model=AdminCleaningLogDetailView)
def get_admin_cleaning_log_detail(
    cleaning_log_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminCleaningLogDetailView:
    _ = current_user
    try:
        return AdminCleaningLogService().get_detail(session, cleaning_log_id=cleaning_log_id)
    except (CleaningLogNotFoundError, CleaningLogValidationError) as error:
        raise _to_http_exception(error) from error


@admin_cleaning_logs_router.post(
    "",
    response_model=AdminCleaningLogDetailView,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_cleaning_log(
    command: AdminCleaningLogCreateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminCleaningLogDetailView:
    try:
        return AdminCleaningLogService().create_log(
            session,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (CleaningLogNotFoundError, CleaningLogValidationError) as error:
        raise _to_http_exception(error) from error


@admin_cleaning_logs_router.post(
    "/{cleaning_log_id}/complete",
    response_model=AdminCleaningLogDetailView,
)
def complete_admin_cleaning_log(
    cleaning_log_id: UUID,
    command: AdminCleaningLogCompleteRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminCleaningLogDetailView:
    try:
        return AdminCleaningLogService().complete_log(
            session,
            cleaning_log_id=cleaning_log_id,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (CleaningLogNotFoundError, CleaningLogValidationError) as error:
        raise _to_http_exception(error) from error


@admin_cleaning_logs_router.post(
    "/{cleaning_log_id}/cancel",
    response_model=AdminCleaningLogDetailView,
)
def cancel_admin_cleaning_log(
    cleaning_log_id: UUID,
    command: AdminCleaningLogCancelRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminCleaningLogDetailView:
    try:
        return AdminCleaningLogService().cancel_log(
            session,
            cleaning_log_id=cleaning_log_id,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (CleaningLogNotFoundError, CleaningLogValidationError) as error:
        raise _to_http_exception(error) from error


@admin_sanitary_verifications_router.get(
    "",
    response_model=AdminSanitaryVerificationListResponse,
)
def list_admin_sanitary_verifications(
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    area_name: Annotated[str | None, Query(min_length=1)] = None,
    area_type: Annotated[str | None, Query(min_length=1)] = None,
    branch_id: Annotated[UUID | None, Query()] = None,
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
    evidence_state: Annotated[str | None, Query(min_length=1)] = None,
    incident_state: Annotated[str | None, Query(min_length=1)] = None,
    inspector_user_id: Annotated[UUID | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    process_name: Annotated[str | None, Query(min_length=1)] = None,
    process_type: Annotated[str | None, Query(min_length=1)] = None,
    result: Annotated[str | None, Query(min_length=1)] = None,
    risk_level: Annotated[str | None, Query(min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    template_id: Annotated[UUID | None, Query()] = None,
    warning_state: Annotated[str | None, Query(min_length=1)] = None,
) -> AdminSanitaryVerificationListResponse:
    _ = current_user
    try:
        return AdminSanitaryVerificationService().list_verifications(
            session,
            area_name=area_name,
            area_type=area_type,
            branch_id=branch_id,
            date_from=_parse_optional_datetime(date_from),
            date_to=_parse_optional_datetime(date_to, end_of_day=True),
            evidence_state=evidence_state,
            incident_state=incident_state,
            inspector_user_id=inspector_user_id,
            page=page,
            page_size=page_size,
            process_name=process_name,
            process_type=process_type,
            result=result,
            risk_level=risk_level,
            search=search,
            status_filter=status_filter,
            template_id=template_id,
            warning_state=warning_state,
        )
    except (SanitaryVerificationNotFoundError, SanitaryVerificationValidationError) as error:
        raise _to_sanitary_http_exception(error) from error


@admin_sanitary_verifications_router.get(
    "/templates",
    response_model=list[AdminSanitaryTemplateView],
)
def list_admin_sanitary_templates(
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
) -> list[AdminSanitaryTemplateView]:
    _ = current_user
    return AdminSanitaryVerificationService().list_templates(session)


@admin_sanitary_verifications_router.get(
    "/{verification_id}",
    response_model=AdminSanitaryVerificationDetailView,
)
def get_admin_sanitary_verification_detail(
    verification_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminSanitaryVerificationDetailView:
    _ = current_user
    try:
        return AdminSanitaryVerificationService().get_detail(
            session,
            verification_id=verification_id,
        )
    except (SanitaryVerificationNotFoundError, SanitaryVerificationValidationError) as error:
        raise _to_sanitary_http_exception(error) from error


@admin_sanitary_verifications_router.post(
    "",
    response_model=AdminSanitaryVerificationDetailView,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_sanitary_verification(
    command: AdminSanitaryVerificationCreateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminSanitaryVerificationDetailView:
    try:
        return AdminSanitaryVerificationService().create_verification(
            session,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (SanitaryVerificationNotFoundError, SanitaryVerificationValidationError) as error:
        raise _to_sanitary_http_exception(error) from error


@admin_sanitary_verifications_router.post(
    "/{verification_id}/start",
    response_model=AdminSanitaryVerificationDetailView,
)
def start_admin_sanitary_verification(
    verification_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminSanitaryVerificationDetailView:
    try:
        return AdminSanitaryVerificationService().start_verification(
            session,
            verification_id=verification_id,
            current_user=current_user,
            request_id=request_id,
        )
    except (SanitaryVerificationNotFoundError, SanitaryVerificationValidationError) as error:
        raise _to_sanitary_http_exception(error) from error


@admin_sanitary_verifications_router.post(
    "/{verification_id}/complete",
    response_model=AdminSanitaryVerificationDetailView,
)
def complete_admin_sanitary_verification(
    verification_id: UUID,
    command: AdminSanitaryVerificationCompleteRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminSanitaryVerificationDetailView:
    try:
        return AdminSanitaryVerificationService().complete_verification(
            session,
            verification_id=verification_id,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (SanitaryVerificationNotFoundError, SanitaryVerificationValidationError) as error:
        raise _to_sanitary_http_exception(error) from error


@admin_sanitary_verifications_router.post(
    "/{verification_id}/cancel",
    response_model=AdminSanitaryVerificationDetailView,
)
def cancel_admin_sanitary_verification(
    verification_id: UUID,
    command: AdminSanitaryVerificationCancelRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminSanitaryVerificationDetailView:
    try:
        return AdminSanitaryVerificationService().cancel_verification(
            session,
            verification_id=verification_id,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (SanitaryVerificationNotFoundError, SanitaryVerificationValidationError) as error:
        raise _to_sanitary_http_exception(error) from error


@admin_incidents_router.get("", response_model=AdminIncidentListResponse)
def list_admin_incidents(
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    area_name: Annotated[str | None, Query(min_length=1)] = None,
    branch_id: Annotated[UUID | None, Query()] = None,
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
    due_state: Annotated[str | None, Query(min_length=1)] = None,
    evidence_state: Annotated[str | None, Query(min_length=1)] = None,
    incident_type: Annotated[str | None, Query(min_length=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    related_document_state: Annotated[str | None, Query(min_length=1)] = None,
    reported_by_user_id: Annotated[UUID | None, Query()] = None,
    responsible_user_id: Annotated[UUID | None, Query()] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    severity: Annotated[str | None, Query(min_length=1)] = None,
    source_type: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    warning_state: Annotated[str | None, Query(min_length=1)] = None,
) -> AdminIncidentListResponse:
    _ = current_user
    try:
        return AdminIncidentService().list_incidents(
            session,
            area_name=area_name,
            branch_id=branch_id,
            date_from=_parse_optional_datetime(date_from),
            date_to=_parse_optional_datetime(date_to, end_of_day=True),
            due_state=due_state,
            evidence_state=evidence_state,
            incident_type=incident_type,
            page=page,
            page_size=page_size,
            related_document_state=related_document_state,
            reported_by_user_id=reported_by_user_id,
            responsible_user_id=responsible_user_id,
            search=search,
            severity=severity,
            source_type=source_type,
            status_filter=status_filter,
            warning_state=warning_state,
        )
    except (IncidentNotFoundError, IncidentValidationError) as error:
        raise _to_incident_http_exception(error) from error


@admin_incidents_router.get("/{incident_id}", response_model=AdminIncidentDetailView)
def get_admin_incident_detail(
    incident_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminIncidentDetailView:
    _ = current_user
    try:
        return AdminIncidentService().get_detail(session, incident_id=incident_id)
    except (IncidentNotFoundError, IncidentValidationError) as error:
        raise _to_incident_http_exception(error) from error


@admin_incidents_router.post(
    "",
    response_model=AdminIncidentDetailView,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_incident(
    command: AdminIncidentCreateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminIncidentDetailView:
    try:
        return AdminIncidentService().create_incident(
            session,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (IncidentNotFoundError, IncidentValidationError) as error:
        raise _to_incident_http_exception(error) from error


@admin_incidents_router.patch("/{incident_id}", response_model=AdminIncidentDetailView)
def update_admin_incident(
    incident_id: UUID,
    command: AdminIncidentUpdateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminIncidentDetailView:
    try:
        return AdminIncidentService().update_incident(
            session,
            incident_id=incident_id,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (IncidentNotFoundError, IncidentValidationError) as error:
        raise _to_incident_http_exception(error) from error


@admin_incidents_router.post(
    "/{incident_id}/follow-ups",
    response_model=AdminIncidentDetailView,
)
def add_admin_incident_follow_up(
    incident_id: UUID,
    command: AdminIncidentFollowUpCreateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminIncidentDetailView:
    try:
        return AdminIncidentService().add_follow_up(
            session,
            incident_id=incident_id,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (IncidentNotFoundError, IncidentValidationError) as error:
        raise _to_incident_http_exception(error) from error


@admin_incidents_router.post("/{incident_id}/status", response_model=AdminIncidentDetailView)
def change_admin_incident_status(
    incident_id: UUID,
    command: AdminIncidentStatusRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminIncidentDetailView:
    try:
        return AdminIncidentService().change_status(
            session,
            incident_id=incident_id,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (IncidentNotFoundError, IncidentValidationError) as error:
        raise _to_incident_http_exception(error) from error


@admin_incidents_router.post("/{incident_id}/resolve", response_model=AdminIncidentDetailView)
def resolve_admin_incident(
    incident_id: UUID,
    command: AdminIncidentResolveRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminIncidentDetailView:
    try:
        return AdminIncidentService().resolve_incident(
            session,
            incident_id=incident_id,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (IncidentNotFoundError, IncidentValidationError) as error:
        raise _to_incident_http_exception(error) from error


@admin_incidents_router.post("/{incident_id}/reopen", response_model=AdminIncidentDetailView)
def reopen_admin_incident(
    incident_id: UUID,
    command: AdminIncidentFollowUpCreateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminIncidentDetailView:
    try:
        return AdminIncidentService().reopen_incident(
            session,
            incident_id=incident_id,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (IncidentNotFoundError, IncidentValidationError) as error:
        raise _to_incident_http_exception(error) from error


@admin_equipment_maintenance_router.get(
    "/equipment",
    response_model=AdminEquipmentListResponse,
)
def list_admin_equipment(
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    area_name: Annotated[str | None, Query(min_length=1)] = None,
    area_type: Annotated[str | None, Query(min_length=1)] = None,
    branch_id: Annotated[UUID | None, Query()] = None,
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
    equipment_type: Annotated[str | None, Query(min_length=1)] = None,
    incident_state: Annotated[str | None, Query(min_length=1)] = None,
    maintenance_status: Annotated[str | None, Query(min_length=1)] = None,
    maintenance_type: Annotated[str | None, Query(min_length=1)] = None,
    operational_status: Annotated[str | None, Query(min_length=1)] = None,
    overdue_state: Annotated[str | None, Query(min_length=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    provider_name: Annotated[str | None, Query(min_length=1)] = None,
    risk_level: Annotated[str | None, Query(min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    technician_name: Annotated[str | None, Query(min_length=1)] = None,
) -> AdminEquipmentListResponse:
    _ = current_user
    try:
        return AdminEquipmentMaintenanceService().list_equipment(
            session,
            area_name=area_name,
            area_type=area_type,
            branch_id=branch_id,
            date_from=_parse_optional_datetime(date_from),
            date_to=_parse_optional_datetime(date_to, end_of_day=True),
            equipment_type=equipment_type,
            incident_state=incident_state,
            maintenance_status=maintenance_status,
            maintenance_type=maintenance_type,
            operational_status=operational_status,
            overdue_state=overdue_state,
            page=page,
            page_size=page_size,
            provider_name=provider_name,
            risk_level=risk_level,
            search=search,
            technician_name=technician_name,
        )
    except (
        EquipmentNotFoundError,
        MaintenanceRecordNotFoundError,
        EquipmentMaintenanceValidationError,
    ) as error:
        raise _to_equipment_http_exception(error) from error


@admin_equipment_maintenance_router.get(
    "/equipment/{equipment_id}",
    response_model=AdminEquipmentDetailView,
)
def get_admin_equipment_detail(
    equipment_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminEquipmentDetailView:
    _ = current_user
    try:
        return AdminEquipmentMaintenanceService().get_detail(session, equipment_id=equipment_id)
    except (
        EquipmentNotFoundError,
        MaintenanceRecordNotFoundError,
        EquipmentMaintenanceValidationError,
    ) as error:
        raise _to_equipment_http_exception(error) from error


@admin_equipment_maintenance_router.post(
    "/equipment",
    response_model=AdminEquipmentDetailView,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_equipment(
    command: AdminEquipmentCreateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminEquipmentDetailView:
    try:
        return AdminEquipmentMaintenanceService().create_equipment(
            session,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (
        EquipmentNotFoundError,
        MaintenanceRecordNotFoundError,
        EquipmentMaintenanceValidationError,
    ) as error:
        raise _to_equipment_http_exception(error) from error


@admin_equipment_maintenance_router.patch(
    "/equipment/{equipment_id}",
    response_model=AdminEquipmentDetailView,
)
def update_admin_equipment(
    equipment_id: UUID,
    command: AdminEquipmentUpdateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminEquipmentDetailView:
    try:
        return AdminEquipmentMaintenanceService().update_equipment(
            session,
            equipment_id=equipment_id,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (
        EquipmentNotFoundError,
        MaintenanceRecordNotFoundError,
        EquipmentMaintenanceValidationError,
    ) as error:
        raise _to_equipment_http_exception(error) from error


@admin_equipment_maintenance_router.post(
    "/equipment/{equipment_id}/status",
    response_model=AdminEquipmentDetailView,
)
def change_admin_equipment_status(
    equipment_id: UUID,
    command: AdminEquipmentStatusRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminEquipmentDetailView:
    try:
        return AdminEquipmentMaintenanceService().change_equipment_status(
            session,
            equipment_id=equipment_id,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (
        EquipmentNotFoundError,
        MaintenanceRecordNotFoundError,
        EquipmentMaintenanceValidationError,
    ) as error:
        raise _to_equipment_http_exception(error) from error


@admin_equipment_maintenance_router.post(
    "/maintenance",
    response_model=AdminEquipmentDetailView,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_equipment_maintenance(
    command: AdminMaintenanceCreateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminEquipmentDetailView:
    try:
        return AdminEquipmentMaintenanceService().create_maintenance(
            session,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (
        EquipmentNotFoundError,
        MaintenanceRecordNotFoundError,
        EquipmentMaintenanceValidationError,
    ) as error:
        raise _to_equipment_http_exception(error) from error


@admin_equipment_maintenance_router.post(
    "/maintenance/{maintenance_id}/start",
    response_model=AdminEquipmentDetailView,
)
def start_admin_equipment_maintenance(
    maintenance_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminEquipmentDetailView:
    try:
        return AdminEquipmentMaintenanceService().start_maintenance(
            session,
            maintenance_id=maintenance_id,
            current_user=current_user,
            request_id=request_id,
        )
    except (
        EquipmentNotFoundError,
        MaintenanceRecordNotFoundError,
        EquipmentMaintenanceValidationError,
    ) as error:
        raise _to_equipment_http_exception(error) from error


@admin_equipment_maintenance_router.post(
    "/maintenance/{maintenance_id}/complete",
    response_model=AdminEquipmentDetailView,
)
def complete_admin_equipment_maintenance(
    maintenance_id: UUID,
    command: AdminMaintenanceCompleteRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminEquipmentDetailView:
    try:
        return AdminEquipmentMaintenanceService().complete_maintenance(
            session,
            maintenance_id=maintenance_id,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (
        EquipmentNotFoundError,
        MaintenanceRecordNotFoundError,
        EquipmentMaintenanceValidationError,
    ) as error:
        raise _to_equipment_http_exception(error) from error


@admin_equipment_maintenance_router.post(
    "/maintenance/{maintenance_id}/cancel",
    response_model=AdminEquipmentDetailView,
)
def cancel_admin_equipment_maintenance(
    maintenance_id: UUID,
    command: AdminMaintenanceCancelRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminEquipmentDetailView:
    try:
        return AdminEquipmentMaintenanceService().cancel_maintenance(
            session,
            maintenance_id=maintenance_id,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (
        EquipmentNotFoundError,
        MaintenanceRecordNotFoundError,
        EquipmentMaintenanceValidationError,
    ) as error:
        raise _to_equipment_http_exception(error) from error

