from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.modules.branches.application.admin_schemas import (
    AdminBranchCreateRequest,
    AdminBranchDetailView,
    AdminBranchesListResponse,
    AdminBranchUpdateRequest,
    AdminWorkstationCreateRequest,
    AdminWorkstationDetailView,
    AdminWorkstationsListResponse,
    AdminWorkstationUpdateRequest,
)
from zeromerma_api.modules.branches.application.admin_services import (
    AdminBranchService,
    AdminWorkstationService,
)
from zeromerma_api.modules.branches.application.schemas import PosBootstrapResponse
from zeromerma_api.modules.branches.application.services import PosBootstrapService
from zeromerma_api.modules.branches.domain.exceptions import (
    BranchAccessError,
    BranchAdminError,
    BranchAssignmentRequiredError,
    BranchConflictError,
    BranchInactiveError,
    BranchNotFoundError,
    BranchValidationError,
    BrandNotFoundError,
    WorkstationAdminNotFoundError,
    WorkstationConflictError,
    WorkstationInactiveError,
    WorkstationNotFoundError,
    WorkstationValidationError,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.application.services import user_can_access_surface
from zeromerma_api.modules.identity.domain.constants import IDENTITY_SURFACE_BACKOFFICE
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user

router = APIRouter(prefix="/v1/pos", tags=["pos"])
admin_router = APIRouter(prefix="/v1/admin/branches", tags=["admin-branches"])
admin_workstations_router = APIRouter(prefix="/v1/admin/workstations", tags=["admin-workstations"])


def _to_http_exception(error: BranchAccessError) -> HTTPException:
    if isinstance(error, WorkstationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))

    if isinstance(error, BranchAssignmentRequiredError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))

    if isinstance(error, (BranchInactiveError, WorkstationInactiveError)):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def _require_backoffice_user(current_user: AuthenticatedUser) -> None:
    if not user_can_access_surface(current_user, IDENTITY_SURFACE_BACKOFFICE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Backoffice access is required.",
        )


def _to_admin_http_exception(error: BranchAdminError) -> HTTPException:
    if isinstance(error, (BranchNotFoundError, BrandNotFoundError, WorkstationAdminNotFoundError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, (BranchConflictError, WorkstationConflictError)):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, (BranchValidationError, WorkstationValidationError)):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/bootstrap", response_model=PosBootstrapResponse)
def bootstrap(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> PosBootstrapResponse:
    try:
        return PosBootstrapService().get_bootstrap(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
        )
    except BranchAccessError as error:
        raise _to_http_exception(error) from error


@admin_router.get("", response_model=AdminBranchesListResponse)
def list_admin_branches(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    brand_id: UUID | None = None,
    status_filter: Annotated[str | None, Query(alias="status", min_length=1)] = None,
    has_active_workstations: Annotated[str | None, Query(min_length=1)] = None,
    warning_state: Annotated[str | None, Query(min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AdminBranchesListResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminBranchService().list_branches(
            session,
            brand_id=brand_id,
            status_filter=status_filter,
            has_active_workstations=has_active_workstations,
            warning_state=warning_state,
            search=search,
            page=page,
            page_size=page_size,
        )
    except BranchAdminError as error:
        raise _to_admin_http_exception(error) from error


@admin_router.get("/{branch_id}", response_model=AdminBranchDetailView)
def get_admin_branch_detail(
    branch_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminBranchDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminBranchService().get_branch_detail(session, branch_id=branch_id)
    except BranchAdminError as error:
        raise _to_admin_http_exception(error) from error


@admin_router.post("", response_model=AdminBranchDetailView, status_code=status.HTTP_201_CREATED)
def create_admin_branch(
    payload: AdminBranchCreateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminBranchDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminBranchService().create_branch(
            session,
            current_user=current_user,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except BranchAdminError as error:
        raise _to_admin_http_exception(error) from error


@admin_router.patch("/{branch_id}", response_model=AdminBranchDetailView)
def update_admin_branch(
    branch_id: UUID,
    payload: AdminBranchUpdateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminBranchDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminBranchService().update_branch(
            session,
            current_user=current_user,
            branch_id=branch_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except BranchAdminError as error:
        raise _to_admin_http_exception(error) from error


@admin_workstations_router.get("", response_model=AdminWorkstationsListResponse)
def list_admin_workstations(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    branch_id: UUID | None = None,
    status_filter: Annotated[str | None, Query(alias="status", min_length=1)] = None,
    cash_session_state: Annotated[str | None, Query(min_length=1)] = None,
    readiness: Annotated[str | None, Query(min_length=1)] = None,
    warning_state: Annotated[str | None, Query(min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AdminWorkstationsListResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminWorkstationService().list_workstations(
            session,
            branch_id=branch_id,
            status_filter=status_filter,
            cash_session_state=cash_session_state,
            readiness=readiness,
            warning_state=warning_state,
            search=search,
            page=page,
            page_size=page_size,
        )
    except BranchAdminError as error:
        raise _to_admin_http_exception(error) from error


@admin_workstations_router.get("/{workstation_id}", response_model=AdminWorkstationDetailView)
def get_admin_workstation_detail(
    workstation_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminWorkstationDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminWorkstationService().get_workstation_detail(
            session,
            workstation_id=workstation_id,
        )
    except BranchAdminError as error:
        raise _to_admin_http_exception(error) from error


@admin_workstations_router.post(
    "",
    response_model=AdminWorkstationDetailView,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_workstation(
    payload: AdminWorkstationCreateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminWorkstationDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminWorkstationService().create_workstation(
            session,
            current_user=current_user,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except BranchAdminError as error:
        raise _to_admin_http_exception(error) from error


@admin_workstations_router.patch("/{workstation_id}", response_model=AdminWorkstationDetailView)
def update_admin_workstation(
    workstation_id: UUID,
    payload: AdminWorkstationUpdateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminWorkstationDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminWorkstationService().update_workstation(
            session,
            current_user=current_user,
            workstation_id=workstation_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except BranchAdminError as error:
        raise _to_admin_http_exception(error) from error

