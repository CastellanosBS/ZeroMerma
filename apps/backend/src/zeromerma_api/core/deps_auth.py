# apps/backend/src/zeromerma_api/core/deps_auth.py
from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.core.auth_context import AuthContext
from zeromerma_api.core.authz import get_role_code
from zeromerma_api.core.security import (
    JWT_CLAIM_BRANCH_ID,
    JWT_CLAIM_ROLE_CODE,
    AuthTokenError,
    decode_access_token,
)
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
    Decode a JWT payload or raise a standardized 401 response.
    """
    try:
        return decode_access_token(token)
    except AuthTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


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
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject (sub).",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token subject (sub).",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _parse_optional_role_code_claim(payload: dict[str, Any]) -> str | None:
    """
    Parse the optional `role_code` claim.

    Behavior:
    - missing claim -> None
    - blank string  -> None
    - non-string    -> 401 because token is malformed
    """
    raw_value = payload.get(JWT_CLAIM_ROLE_CODE)

    if raw_value is None:
        return None

    if not isinstance(raw_value, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token role_code claim.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    normalized = raw_value.strip().upper()
    return normalized or None


def _parse_optional_branch_id_claim(payload: dict[str, Any]) -> int | None:
    """
    Parse the optional `branch_id` claim.

    Behavior:
    - missing claim -> None
    - positive int  -> accepted
    - numeric str   -> accepted
    - anything else -> 401 because token is malformed

    Security model:
    - the claim is normalized and exposed in AuthContext for diagnostics/future
      contract evolution
    - it is NOT the authoritative branch assignment; the DB user row remains
      authoritative
    """
    raw_value = payload.get(JWT_CLAIM_BRANCH_ID)

    if raw_value is None:
        return None

    if isinstance(raw_value, bool):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token branch_id claim.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if isinstance(raw_value, int):
        if raw_value <= 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token branch_id claim.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return raw_value

    if isinstance(raw_value, str):
        try:
            normalized = int(raw_value.strip())
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token branch_id claim.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        if normalized <= 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token branch_id claim.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return normalized

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token branch_id claim.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _load_user_or_401(db: Session, user_id: int) -> UserAccount:
    """
    Load the authenticated user from DB or raise 401.
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
    Resolve an AuthContext from the Bearer token.

    Resolution policy:
    - user identity always comes from `sub` + DB lookup
    - role_code prefers JWT claim when present
    - role_code falls back to DB lookup when missing
    - branch_id claim is normalized when present, but the authoritative branch
      remains `user.branch_id` from the current DB row

    This preserves backward compatibility with legacy subject-only tokens while
    supporting a more expressive and explicit token contract for newer callers.
    """
    payload = _decode_payload_or_401(token)
    user_id = _parse_user_id_from_payload(payload)
    user = _load_user_or_401(db, user_id)

    role_code = _parse_optional_role_code_claim(payload)
    if role_code is None:
        role_code = get_role_code(db, role_id=int(user.role_id))

    token_branch_id = _parse_optional_branch_id_claim(payload)

    return AuthContext(
        user=user,
        role_code=role_code,
        token_branch_id=token_branch_id,
    )


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
