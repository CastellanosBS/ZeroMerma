# apps/backend/src/zeromerma_api/core/deps_auth.py
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.core.security import AuthTokenError, decode_access_token
from zeromerma_api.db.engine import get_session
from zeromerma_api.models.user_account import UserAccount


def get_bearer_token(request: Request) -> str:
    """
    Extract a Bearer token from the Authorization header.

    Expected header format:
      Authorization: Bearer <token>

    Returns:
      The raw JWT token string.

    Raises:
      HTTPException(401) if missing or malformed.
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


def get_current_user(
    token: Annotated[str, Depends(get_bearer_token)],
    db: Annotated[Session, Depends(get_session)],
) -> UserAccount:
    """
    Resolve the current authenticated user from a JWT Bearer token.

    Steps:
      1) Decode/validate the JWT signature and claims.
      2) Read the 'sub' claim as the user id.
      3) Fetch the user from the database.

    Returns:
      UserAccount ORM instance.

    Raises:
      HTTPException(401) if token is invalid/expired or user does not exist.
    """
    try:
        payload = decode_access_token(token)
    except AuthTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    sub = payload.get("sub")

    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject (sub).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(sub)
    except (TypeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject (sub).",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    user = db.execute(
        select(UserAccount).where(UserAccount.id == user_id)
    ).scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found for token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_active_user(
    user: Annotated[UserAccount, Depends(get_current_user)],
) -> UserAccount:
    """
    Enforce that the authenticated user is active.

    Returns:
      The same user if active.

    Raises:
      HTTPException(403) if inactive.
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    return user
