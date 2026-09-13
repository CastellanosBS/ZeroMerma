from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.modules.identity.application.admin_role_schemas import (
    AdminPermissionsResponse,
    AdminRoleCreateRequest,
    AdminRoleDetailView,
    AdminRolesListResponse,
    AdminRoleStatusChangeRequest,
    AdminRoleUpdateRequest,
    AdminRoleUserAssignmentRequest,
)
from zeromerma_api.modules.identity.application.admin_role_services import AdminRoleService
from zeromerma_api.modules.identity.application.admin_schemas import (
    AdminAssignmentScopeRequest,
    AdminUserBranchAssignmentCommand,
    AdminUserCreateRequest,
    AdminUserDetailView,
    AdminUserLockRequest,
    AdminUserRoleAssignmentRequest,
    AdminUsersListResponse,
    AdminUserStatusChangeRequest,
    AdminUserUpdateRequest,
)
from zeromerma_api.modules.identity.application.admin_services import AdminUserService
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.application.privileged_access import PrivilegedAccessService
from zeromerma_api.modules.identity.application.privileged_schemas import (
    PrivilegedChangeConfirmationRequest,
    PrivilegedChangeCreateRequest,
    PrivilegedChangeView,
)
from zeromerma_api.modules.identity.application.schemas import (
    AuthenticatedUser,
    IdentitySurface,
    LoginRequest,
    LoginResponse,
)
from zeromerma_api.modules.identity.application.services import AuthService, user_can_access_surface
from zeromerma_api.modules.identity.domain.constants import IDENTITY_SURFACE_BACKOFFICE
from zeromerma_api.modules.identity.domain.exceptions import (
    InvalidCredentialsError,
    RoleAdminError,
    RoleConflictError,
    RoleNotFoundError,
    RoleValidationError,
    UserAdminError,
    UserConflictError,
    UserNotFoundError,
    UserValidationError,
)
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user

router = APIRouter(prefix="/v1/auth", tags=["auth"])
admin_router = APIRouter(prefix="/v1/admin/users", tags=["admin-users"])
roles_admin_router = APIRouter(prefix="/v1/admin/roles", tags=["admin-roles"])


def _require_backoffice_user(current_user: AuthenticatedUser) -> None:
    if not user_can_access_surface(current_user, IDENTITY_SURFACE_BACKOFFICE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Backoffice access is required.",
        )


def _to_admin_http_exception(error: UserAdminError) -> HTTPException:
    if isinstance(error, UserNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, UserConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, UserValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def _to_role_admin_http_exception(error: RoleAdminError) -> HTTPException:
    if isinstance(error, RoleNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, RoleConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, RoleValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    session: Annotated[Session, Depends(get_session)],
) -> LoginResponse:
    try:
        access_token, user = AuthService().login(
            session,
            email=payload.email,
            password=payload.password,
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    return LoginResponse(access_token=access_token, user=user)


@router.get("/me", response_model=AuthenticatedUser)
def me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    surface: IdentitySurface | None = None,
) -> AuthenticatedUser:
    chosen = surface or current_user.default_surface
    if chosen not in current_user.allowed_surfaces:
        raise HTTPException(status_code=403, detail="The requested surface is not allowed.")
    return resolve_authorization(session, current_user, surface=chosen)


@admin_router.get("", response_model=AdminUsersListResponse)
def list_admin_users(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    search: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status", min_length=1)] = None,
    app_access: Annotated[str | None, Query(min_length=1)] = None,
    branch_id: UUID | None = None,
    role_id: Annotated[str | None, Query(min_length=1)] = None,
    last_login_state: Annotated[str | None, Query(min_length=1)] = None,
    warning_state: Annotated[str | None, Query(min_length=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AdminUsersListResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminUserService().list_users(
            session,
            current_user=current_user,
            search=search,
            status_filter=status_filter,
            app_access=app_access,
            branch_id=branch_id,
            role_id=role_id,
            last_login_state=last_login_state,
            warning_state=warning_state,
            page=page,
            page_size=page_size,
        )
    except UserAdminError as error:
        raise _to_admin_http_exception(error) from error


@admin_router.get("/{user_id}", response_model=AdminUserDetailView)
def get_admin_user_detail(
    user_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminUserDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminUserService().get_user_detail(
            session,
            user_id=user_id,
            current_user=current_user,
        )
    except UserAdminError as error:
        raise _to_admin_http_exception(error) from error


@admin_router.post("", response_model=AdminUserDetailView, status_code=status.HTTP_201_CREATED)
def create_admin_user(
    payload: AdminUserCreateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminUserDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminUserService().create_user(
            session,
            current_user=current_user,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except UserAdminError as error:
        raise _to_admin_http_exception(error) from error


@admin_router.patch("/{user_id}", response_model=AdminUserDetailView)
def update_admin_user(
    user_id: UUID,
    payload: AdminUserUpdateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminUserDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminUserService().update_user(
            session,
            current_user=current_user,
            user_id=user_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except UserAdminError as error:
        raise _to_admin_http_exception(error) from error


@admin_router.post("/{user_id}/status", response_model=AdminUserDetailView)
def change_admin_user_status(
    user_id: UUID,
    payload: AdminUserStatusChangeRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminUserDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminUserService().change_status(
            session,
            current_user=current_user,
            user_id=user_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except UserAdminError as error:
        raise _to_admin_http_exception(error) from error


@admin_router.post("/{user_id}/lock", response_model=AdminUserDetailView)
def lock_admin_user(
    user_id: UUID,
    payload: AdminUserLockRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminUserDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminUserService().lock_user(
            session,
            current_user=current_user,
            user_id=user_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except UserAdminError as error:
        raise _to_admin_http_exception(error) from error


@admin_router.post("/{user_id}/unlock", response_model=AdminUserDetailView)
def unlock_admin_user(
    user_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminUserDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminUserService().unlock_user(
            session,
            current_user=current_user,
            user_id=user_id,
            request_id=request.headers.get("X-Request-ID"),
        )
    except UserAdminError as error:
        raise _to_admin_http_exception(error) from error


@admin_router.post("/{user_id}/branch-assignments", response_model=AdminUserDetailView)
def add_admin_user_branch_assignment(
    user_id: UUID,
    payload: AdminUserBranchAssignmentCommand,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminUserDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminUserService().add_branch_assignment(
            session,
            current_user=current_user,
            user_id=user_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except UserAdminError as error:
        raise _to_admin_http_exception(error) from error


@admin_router.post(
    "/{user_id}/branch-assignments/{branch_id}/deactivate",
    response_model=AdminUserDetailView,
)
def deactivate_admin_user_branch_assignment(
    user_id: UUID,
    branch_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminUserDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminUserService().deactivate_branch_assignment(
            session,
            current_user=current_user,
            user_id=user_id,
            branch_id=branch_id,
            request_id=request.headers.get("X-Request-ID"),
        )
    except UserAdminError as error:
        raise _to_admin_http_exception(error) from error


@admin_router.post(
    "/{user_id}/branch-assignments/{branch_id}/default",
    response_model=AdminUserDetailView,
)
def set_admin_user_default_branch_assignment(
    user_id: UUID,
    branch_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminUserDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminUserService().set_default_branch_assignment(
            session,
            current_user=current_user,
            user_id=user_id,
            branch_id=branch_id,
            request_id=request.headers.get("X-Request-ID"),
        )
    except UserAdminError as error:
        raise _to_admin_http_exception(error) from error


@admin_router.post("/{user_id}/roles", response_model=AdminUserDetailView)
def assign_admin_user_role(
    user_id: UUID,
    payload: AdminUserRoleAssignmentRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminUserDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminUserService().assign_role(
            session,
            current_user=current_user,
            user_id=user_id,
            role_id=payload.role_id,
            command=AdminAssignmentScopeRequest(
                scope_type=payload.scope_type, branch_ids=payload.branch_ids
            ),
            request_id=request.headers.get("X-Request-ID"),
        )
    except UserAdminError as error:
        raise _to_admin_http_exception(error) from error


@admin_router.post("/{user_id}/roles/{role_id}/remove", response_model=AdminUserDetailView)
def remove_admin_user_role(
    user_id: UUID,
    role_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminUserDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminUserService().remove_role(
            session,
            current_user=current_user,
            user_id=user_id,
            role_id=role_id,
            request_id=request.headers.get("X-Request-ID"),
        )
    except UserAdminError as error:
        raise _to_admin_http_exception(error) from error


@roles_admin_router.get("", response_model=AdminRolesListResponse)
def list_admin_roles(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    search: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status", min_length=1)] = None,
    app_surface: Annotated[str | None, Query(min_length=1)] = None,
    high_privilege: Annotated[str | None, Query(min_length=1)] = None,
    has_users: Annotated[str | None, Query(min_length=1)] = None,
    permission_module: Annotated[str | None, Query(min_length=1)] = None,
    warning_state: Annotated[str | None, Query(min_length=1)] = None,
    system_state: Annotated[str | None, Query(min_length=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AdminRolesListResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminRoleService().list_roles(
            session,
            current_user=current_user,
            search=search,
            status_filter=status_filter,
            app_surface=app_surface,
            high_privilege=high_privilege,
            has_users=has_users,
            permission_module=permission_module,
            warning_state=warning_state,
            system_state=system_state,
            page=page,
            page_size=page_size,
        )
    except RoleAdminError as error:
        raise _to_role_admin_http_exception(error) from error


@roles_admin_router.get("/permissions", response_model=AdminPermissionsResponse)
def list_admin_role_permissions(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminPermissionsResponse:
    _require_backoffice_user(current_user)
    return AdminRoleService().list_permissions(session, current_user=current_user)


@roles_admin_router.post(
    "/privileged-changes", response_model=PrivilegedChangeView, status_code=201
)
def propose_privileged_change(
    payload: PrivilegedChangeCreateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> PrivilegedChangeView:
    _require_backoffice_user(current_user)
    return PrivilegedAccessService().propose(
        session,
        current_user=current_user,
        command=payload,
        request_id=request.headers.get("X-Request-ID"),
    )


@roles_admin_router.get("/privileged-changes/{change_id}", response_model=PrivilegedChangeView)
def get_privileged_change(
    change_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> PrivilegedChangeView:
    _require_backoffice_user(current_user)
    return PrivilegedAccessService().get_change(
        session, current_user=current_user, change_id=change_id
    )


@roles_admin_router.post(
    "/privileged-changes/{change_id}/approve", response_model=PrivilegedChangeView
)
def approve_privileged_change(
    change_id: UUID,
    payload: PrivilegedChangeConfirmationRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> PrivilegedChangeView:
    _require_backoffice_user(current_user)
    return PrivilegedAccessService().approve(
        session,
        current_user=current_user,
        change_id=change_id,
        payload_sha256=payload.payload_sha256,
        request_id=request.headers.get("X-Request-ID"),
    )


@roles_admin_router.post(
    "/privileged-changes/{change_id}/execute", response_model=PrivilegedChangeView
)
def execute_privileged_change(
    change_id: UUID,
    payload: PrivilegedChangeConfirmationRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> PrivilegedChangeView:
    _require_backoffice_user(current_user)
    try:
        return PrivilegedAccessService().execute(
            session,
            current_user=current_user,
            change_id=change_id,
            payload_sha256=payload.payload_sha256,
            request_id=request.headers.get("X-Request-ID"),
        )
    except UserAdminError as error:
        raise _to_admin_http_exception(error) from error
    except RoleAdminError as error:
        raise _to_role_admin_http_exception(error) from error


@roles_admin_router.get("/{role_id}", response_model=AdminRoleDetailView)
def get_admin_role_detail(
    role_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminRoleDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminRoleService().get_role_detail(
            session, role_id=role_id, current_user=current_user
        )
    except RoleAdminError as error:
        raise _to_role_admin_http_exception(error) from error


@roles_admin_router.post(
    "",
    response_model=AdminRoleDetailView,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_role(
    payload: AdminRoleCreateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminRoleDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminRoleService().create_role(
            session,
            current_user=current_user,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except RoleAdminError as error:
        raise _to_role_admin_http_exception(error) from error


@roles_admin_router.patch("/{role_id}", response_model=AdminRoleDetailView)
def update_admin_role(
    role_id: UUID,
    payload: AdminRoleUpdateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminRoleDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminRoleService().update_role(
            session,
            current_user=current_user,
            role_id=role_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except RoleAdminError as error:
        raise _to_role_admin_http_exception(error) from error


@roles_admin_router.post("/{role_id}/status", response_model=AdminRoleDetailView)
def change_admin_role_status(
    role_id: UUID,
    payload: AdminRoleStatusChangeRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminRoleDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminRoleService().change_status(
            session,
            current_user=current_user,
            role_id=role_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except RoleAdminError as error:
        raise _to_role_admin_http_exception(error) from error


@roles_admin_router.post("/{role_id}/users/{user_id}", response_model=AdminRoleDetailView)
def assign_admin_role_to_user(
    role_id: UUID,
    user_id: UUID,
    payload: AdminRoleUserAssignmentRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminRoleDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminRoleService().assign_role_to_user(
            session,
            current_user=current_user,
            role_id=role_id,
            user_id=user_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except RoleAdminError as error:
        raise _to_role_admin_http_exception(error) from error


@roles_admin_router.post("/{role_id}/users/{user_id}/remove", response_model=AdminRoleDetailView)
def remove_admin_role_from_user(
    role_id: UUID,
    user_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminRoleDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminRoleService().remove_role_from_user(
            session,
            current_user=current_user,
            role_id=role_id,
            user_id=user_id,
            request_id=request.headers.get("X-Request-ID"),
        )
    except RoleAdminError as error:
        raise _to_role_admin_http_exception(error) from error
