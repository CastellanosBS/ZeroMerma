# apps/backend/src/zeromerma_api/core/deps_auth.py
from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.core.auth_context import AuthContext
from zeromerma_api.core.authz import get_role_code
from zeromerma_api.core.security import AuthTokenError, decode_access_token
from zeromerma_api.db.engine import get_session
from zeromerma_api.models.user_account import UserAccount


def get_bearer_token(request: Request) -> str:
    """
    Extract a Bearer token from the Authorization header.

    Expected format:
      Authorization: Bearer <token>
    """
    auth = request.headers.get("Authorization", "")

    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = auth.split(" ", 1)
    if len(parts) != 2:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, token = parts[0].strip(), parts[1].strip()
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token


def _decode_payload_or_401(token: str) -> dict[str, Any]:
    """
    Decode JWT or raise a standardized 401 response.
    """
    try:
        return decode_access_token(token)
    except AuthTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def _parse_user_id_from_payload(payload: dict[str, Any]) -> int:
    """
    Parse the `sub` claim as a numeric user id.
    """
    sub = payload.get("sub")

    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject (sub).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if isinstance(sub, bool):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject (sub).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if isinstance(sub, int):
        return sub

    if isinstance(sub, str):
        try:
            return int(sub)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject (sub).",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token subject (sub).",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _load_user_or_401(db: Session, user_id: int) -> UserAccount:
    """
    Load authenticated user from DB or raise 401.
    """
    user = db.execute(select(UserAccount).where(UserAccount.id == user_id)).scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found for token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_user(
    token: Annotated[str, Depends(get_bearer_token)],
    db: Annotated[Session, Depends(get_session)],
) -> UserAccount:
    """
    Resolve the current authenticated user from a JWT Bearer token.
    """
    payload = _decode_payload_or_401(token)
    user_id = _parse_user_id_from_payload(payload)
    return _load_user_or_401(db, user_id)


def get_current_active_user(
    user: Annotated[UserAccount, Depends(get_current_user)],
) -> UserAccount:
    """
    Enforce that the authenticated user is active.
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )
    return user


def get_current_auth_context(
    token: Annotated[str, Depends(get_bearer_token)],
    db: Annotated[Session, Depends(get_session)],
) -> AuthContext:
    """
    Resolve AuthContext from the Bearer token.

    Preferred path:
      - role_code is embedded in JWT

    Backward-compatible fallback:
      - if role_code claim is missing, resolve it from the DB
    """
    payload = _decode_payload_or_401(token)
    user_id = _parse_user_id_from_payload(payload)
    user = _load_user_or_401(db, user_id)

    role_code_claim = payload.get("role_code")
    if isinstance(role_code_claim, str) and role_code_claim.strip():
        role_code = role_code_claim.strip()
    else:
        role_code = get_role_code(db, role_id=int(user.role_id))

    return AuthContext(user=user, role_code=role_code)


def get_current_active_auth_context(
    ctx: Annotated[AuthContext, Depends(get_current_auth_context)],
) -> AuthContext:
    """
    Enforce that the authenticated user in AuthContext is active.
    """
    if not ctx.user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )
    return ctx
