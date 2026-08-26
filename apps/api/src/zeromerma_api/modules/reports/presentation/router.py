from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.application.services import user_can_access_surface
from zeromerma_api.modules.identity.domain.constants import IDENTITY_SURFACE_BACKOFFICE
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user
from zeromerma_api.modules.reports.application.admin_schemas import (
    AdminReportDefinitionsResponse,
    AdminReportExportRequest,
    AdminReportExportResponse,
    AdminReportPreviewRequest,
    AdminReportPreviewResponse,
)
from zeromerma_api.modules.reports.application.admin_services import AdminReportService
from zeromerma_api.modules.reports.domain.exceptions import (
    ReportNotFoundError,
    ReportUnavailableError,
    ReportValidationError,
)

admin_router = APIRouter(prefix="/v1/admin/reports", tags=["admin-reports"])


def _require_backoffice_user(current_user: AuthenticatedUser) -> None:
    if not user_can_access_surface(current_user, IDENTITY_SURFACE_BACKOFFICE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Backoffice access is required.",
        )


@admin_router.get("", response_model=AdminReportDefinitionsResponse)
def list_admin_reports(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    search: Annotated[str | None, Query(min_length=1)] = None,
    category: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status", min_length=1)] = None,
    export_support: Annotated[str | None, Query(min_length=1)] = None,
    sensitivity: Annotated[str | None, Query(min_length=1)] = None,
    source_module: Annotated[str | None, Query(min_length=1)] = None,
) -> AdminReportDefinitionsResponse:
    _require_backoffice_user(current_user)
    return AdminReportService().list_reports(
        session,
        category=category,
        export_support=export_support,
        search=search,
        sensitivity=sensitivity,
        source_module=source_module,
        status_filter=status_filter,
    )


@admin_router.post("/{report_code}/preview", response_model=AdminReportPreviewResponse)
def preview_admin_report(
    report_code: str,
    command: AdminReportPreviewRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminReportPreviewResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminReportService().generate_preview(
            session,
            filters=command.filters,
            report_code=report_code,
        )
    except ReportNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ReportUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ReportValidationError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@admin_router.post("/{report_code}/export", response_model=AdminReportExportResponse)
def export_admin_report(
    report_code: str,
    command: AdminReportExportRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminReportExportResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminReportService().export_report(
            session,
            current_user=current_user,
            export_format=command.format,
            filters=command.filters,
            report_code=report_code,
            request_id=request_id,
        )
    except ReportNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ReportUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ReportValidationError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
