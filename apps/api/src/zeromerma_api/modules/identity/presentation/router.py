from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.db.transactions import rollback_on_error
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
)
from zeromerma_api.modules.identity.application.services import user_can_access_surface
from zeromerma_api.modules.identity.application.session_schemas import (
    AuthSessionsResponse,
    AuthSessionView,
    LoginResponse,
    PasswordChangeRequest,
    PasswordResetCredentialView,
    PasswordResetIssueRequest,
    PasswordResetRequest,
    ReauthenticationRequest,
)
from zeromerma_api.modules.identity.application.session_services import (
    COOKIE_NAMES,
    SessionAuthentication,
    SessionService,
    auth_error,
)
from zeromerma_api.modules.identity.domain.constants import IDENTITY_SURFACE_BACKOFFICE
from zeromerma_api.modules.identity.domain.exceptions import (
    RoleAdminError,
    RoleConflictError,
    RoleNotFoundError,
    RoleValidationError,
    UserAdminError,
    UserConflictError,
    UserNotFoundError,
    UserValidationError,
)
from zeromerma_api.modules.identity.presentation.dependencies import (
    get_current_authentication,
    get_current_user,
    request_audience,
    validate_origin,
)

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
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
) -> LoginResponse:
    if request_audience(request) != payload.audience or request.headers.get("Authorization"):
        raise auth_error(401, "AUTHENTICATION_REQUIRED", "The application audience is invalid.")
    validate_origin(request, payload.audience)
    authentication = SessionService().login(
        session, payload, ip=_client_ip(request), request_id=request.headers.get("X-Request-ID")
    )
    _set_session_cookie(response, authentication)
    return authentication.response()


@router.get("/me", response_model=AuthenticatedUser)
def me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    surface: IdentitySurface | None = None,
) -> AuthenticatedUser:
    if surface is not None and surface != current_user.authorization_surface:
        raise HTTPException(
            status_code=403, detail="The requested audience does not match this session."
        )
    return current_user


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _set_session_cookie(response: Response, authentication: SessionAuthentication) -> None:
    service = SessionService()
    record = authentication.record
    response.set_cookie(
        COOKIE_NAMES[cast(IdentitySurface, record.audience)],
        authentication.credential,
        max_age=max(0, int((record.absolute_expires_at - datetime.now(UTC)).total_seconds())),
        httponly=True,
        secure=True,
        samesite=service.settings.session_cookie_samesite,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"


def _clear_session_cookie(response: Response, audience: IdentitySurface) -> None:
    response.delete_cookie(
        COOKIE_NAMES[audience],
        path="/",
        secure=True,
        httponly=True,
        samesite=SessionService().settings.session_cookie_samesite,
    )


@router.get("/session", response_model=LoginResponse)
def current_session(
    authentication: Annotated[SessionAuthentication, Depends(get_current_authentication)],
    session: Annotated[Session, Depends(get_session)],
    response: Response,
) -> LoginResponse:
    with rollback_on_error(session):
        response.headers["Cache-Control"] = "no-store"
        result = authentication.response()
        session.commit()
        return result


@router.post("/activity", response_model=AuthSessionView)
def session_activity(
    authentication: Annotated[SessionAuthentication, Depends(get_current_authentication)],
    session: Annotated[Session, Depends(get_session)],
) -> AuthSessionView:
    with rollback_on_error(session):
        result = SessionService().activity(session, authentication)
        session.commit()
        return result


@router.post("/lock", response_model=AuthSessionView)
def lock_session(
    authentication: Annotated[SessionAuthentication, Depends(get_current_authentication)],
    session: Annotated[Session, Depends(get_session)],
) -> AuthSessionView:
    return SessionService().lock(session, authentication)


@router.post("/reauthenticate", response_model=LoginResponse)
def reauthenticate_session(
    payload: ReauthenticationRequest,
    request: Request,
    response: Response,
    authentication: Annotated[SessionAuthentication, Depends(get_current_authentication)],
    session: Annotated[Session, Depends(get_session)],
) -> LoginResponse:
    result = SessionService().reauthenticate(
        session,
        authentication,
        password=payload.password,
        ip=_client_ip(request),
        request_id=request.headers.get("X-Request-ID"),
    )
    _set_session_cookie(response, result)
    return result.response()


@router.post("/logout", status_code=204)
def logout_session(
    request: Request,
    response: Response,
    authentication: Annotated[SessionAuthentication, Depends(get_current_authentication)],
    session: Annotated[Session, Depends(get_session)],
) -> None:
    SessionService().logout(session, authentication, request.headers.get("X-Request-ID"))
    _clear_session_cookie(response, cast(IdentitySurface, authentication.record.audience))


@router.get("/sessions", response_model=AuthSessionsResponse)
def list_own_sessions(
    authentication: Annotated[SessionAuthentication, Depends(get_current_authentication)],
    session: Annotated[Session, Depends(get_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AuthSessionsResponse:
    return SessionService().list_sessions(
        session, authentication.user.id, page=page, page_size=page_size
    )


@router.delete("/sessions/{session_id}", status_code=204)
def revoke_own_session(
    session_id: UUID,
    response: Response,
    authentication: Annotated[SessionAuthentication, Depends(get_current_authentication)],
    session: Annotated[Session, Depends(get_session)],
) -> None:
    with rollback_on_error(session):
        SessionService().revoke_sessions(
            session, user_id=authentication.user.id, target_id=session_id
        )
        session.commit()
    if session_id == authentication.record.id:
        _clear_session_cookie(response, cast(IdentitySurface, authentication.record.audience))


@router.post("/sessions/revoke-others", status_code=204)
def revoke_other_sessions(
    authentication: Annotated[SessionAuthentication, Depends(get_current_authentication)],
    session: Annotated[Session, Depends(get_session)],
) -> None:
    with rollback_on_error(session):
        SessionService().revoke_sessions(
            session, user_id=authentication.user.id, except_id=authentication.record.id
        )
        session.commit()


@router.post("/password/change", status_code=204)
def change_own_password(
    payload: PasswordChangeRequest,
    request: Request,
    response: Response,
    authentication: Annotated[SessionAuthentication, Depends(get_current_authentication)],
    session: Annotated[Session, Depends(get_session)],
) -> None:
    SessionService().change_password(
        session,
        authentication,
        current_password=payload.current_password,
        new_password=payload.new_password,
        request_id=request.headers.get("X-Request-ID"),
        ip=_client_ip(request),
    )
    for audience in COOKIE_NAMES:
        _clear_session_cookie(response, audience)


@router.post("/password/reset", status_code=204)
def complete_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
) -> None:
    validate_origin(request, request_audience(request))
    SessionService().complete_password_reset(
        session,
        credential=payload.reset_token,
        new_password=payload.new_password,
        ip=_client_ip(request),
        request_id=request.headers.get("X-Request-ID"),
    )
    for audience in COOKIE_NAMES:
        _clear_session_cookie(response, audience)


@admin_router.get("/{user_id}/sessions", response_model=AuthSessionsResponse)
def list_user_sessions(
    user_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AuthSessionsResponse:
    from zeromerma_api.modules.identity.application.privileged_access import require_user_scope

    require_user_scope(session, current_user, "users.manage", user_id)
    return SessionService().list_sessions(session, user_id, page=page, page_size=page_size)


@admin_router.delete("/{user_id}/sessions/{session_id}", status_code=204)
def revoke_user_session(
    user_id: UUID,
    session_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> None:
    from zeromerma_api.modules.identity.application.privileged_access import require_user_scope

    with rollback_on_error(session):
        require_user_scope(session, current_user, "users.manage", user_id)
        SessionService().revoke_sessions(
            session, user_id=user_id, target_id=session_id, reason="ADMIN_REVOKED"
        )
        session.commit()


@admin_router.post("/{user_id}/password-reset", response_model=PasswordResetCredentialView)
def issue_user_password_reset(
    user_id: UUID,
    payload: PasswordResetIssueRequest,
    request: Request,
    response: Response,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> PasswordResetCredentialView:
    response.headers["Cache-Control"] = "no-store"
    return SessionService().issue_password_reset(
        session,
        actor=current_user,
        user_id=user_id,
        reason=payload.reason,
        approval_id=payload.approval_id,
        payload_sha256=payload.payload_sha256,
        request_id=request.headers.get("X-Request-ID"),
    )


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
