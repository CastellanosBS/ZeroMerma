from __future__ import annotations

from typing import Annotated, cast
from urllib.parse import urlsplit

from fastapi import Depends, Request
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session

from zeromerma_api.core.config import get_settings
from zeromerma_api.db.session import get_session
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser, IdentitySurface
from zeromerma_api.modules.identity.application.session_services import (
    COOKIE_NAMES,
    SessionAuthentication,
    SessionService,
    auth_error,
)

pos_cookie_scheme = APIKeyCookie(
    name=COOKIE_NAMES["POS"], scheme_name="PosSessionCookie", auto_error=False
)
backoffice_cookie_scheme = APIKeyCookie(
    name=COOKIE_NAMES["BACKOFFICE"], scheme_name="BackofficeSessionCookie", auto_error=False
)
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_LIMITED_PATHS = frozenset(
    {"/v1/auth/session", "/v1/auth/logout", "/v1/auth/password/change", "/v1/auth/reauthenticate"}
)
_LOCKED_PATHS = frozenset({"/v1/auth/session", "/v1/auth/logout", "/v1/auth/reauthenticate"})


def request_audience(request: Request) -> IdentitySurface:
    value = request.headers.get("X-ZeroMerma-Surface")
    if value not in {"POS", "BACKOFFICE"}:
        raise auth_error(
            401, "AUTHENTICATION_REQUIRED", "An explicit application audience is required."
        )
    return cast(IdentitySurface, value)


def validate_origin(request: Request, audience: IdentitySurface, *, required: bool = True) -> None:
    settings = get_settings()
    allowed = (
        settings.session_pos_origins if audience == "POS" else settings.session_backoffice_origins
    )
    origin = request.headers.get("Origin")
    if origin is None and required and request.method in {"GET", "HEAD"}:
        # Same-origin fetches may omit Origin. A validated Referer or the request's
        # own origin proves the audience; the global CORS union is never authority.
        try:
            referer = urlsplit(request.headers.get("Referer") or str(request.base_url))
        except ValueError as error:
            raise auth_error(403, "CSRF_FAILED", "The request origin is invalid.") from error
        if (
            referer.scheme not in {"http", "https"}
            or referer.username is not None
            or referer.password is not None
        ):
            raise auth_error(403, "CSRF_FAILED", "The request origin is invalid.")
        origin = f"{referer.scheme}://{referer.netloc}"
    if (origin is None and required) or (origin is not None and origin not in allowed):
        raise auth_error(
            403, "CSRF_FAILED", "The request origin is not authorized for this application."
        )


def get_current_authentication(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    pos_credential: Annotated[str | None, Depends(pos_cookie_scheme)],
    backoffice_credential: Annotated[str | None, Depends(backoffice_cookie_scheme)],
) -> SessionAuthentication:
    if request.headers.get("Authorization") or any(
        key in request.query_params for key in ("access_token", "token", "bearer")
    ):
        raise auth_error(401, "AUTHENTICATION_REQUIRED", "Cookie authentication is required.")
    audience = request_audience(request)
    validate_origin(
        request,
        audience,
        required=request.method not in _SAFE_METHODS or request.url.path == "/v1/auth/session",
    )
    credential = pos_credential if audience == "POS" else backoffice_credential
    if credential is None:
        raise auth_error(401, "AUTHENTICATION_REQUIRED", "Authentication is required.")
    exclusive = request.method not in _SAFE_METHODS and (
        request.url.path.startswith(("/v1/admin/users", "/v1/admin/roles"))
        or request.url.path == "/v1/auth/password/change"
    )
    service = SessionService()
    authentication = service.authenticate(
        session,
        credential=credential,
        audience=audience,
        allow_locked=request.url.path in _LOCKED_PATHS,
        allow_reset=request.url.path in _LIMITED_PATHS,
        request_id=request.headers.get("X-Request-ID"),
        exclusive=exclusive,
    )
    if request.method not in _SAFE_METHODS:
        service.validate_csrf(authentication, request.headers.get("X-CSRF-Token"))
        if authentication.record.status == "ACTIVE" and not request.url.path.startswith(
            "/v1/auth/"
        ):
            service.activity(session, authentication)
    return authentication


def get_current_user(
    authentication: Annotated[SessionAuthentication, Depends(get_current_authentication)],
) -> AuthenticatedUser:
    return authentication.user
