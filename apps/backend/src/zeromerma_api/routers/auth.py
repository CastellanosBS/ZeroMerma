# apps/backend/src/zeromerma_api/routers/auth.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.core.security import create_access_token, verify_password
from zeromerma_api.core.settings import get_settings
from zeromerma_api.db.engine import get_session
from zeromerma_api.models.role import Role
from zeromerma_api.models.user_account import UserAccount
from zeromerma_api.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate a user and return an access token",
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_session),
) -> TokenResponse:
    """
    Authenticate a user by email and password.

    Flow:
    1) Look up the user by email.
    2) Ensure the account exists and is active.
    3) Ensure the account has a stored password hash.
    4) Verify the provided password.
    5) Resolve role_code once (DB) and embed it in the JWT.
    6) Issue a signed JWT access token.

    Security behavior:
    - We intentionally return a generic 401 for invalid credentials.
    - We do not reveal whether the email or the password was wrong.
    """

    settings = get_settings()

    user = db.execute(
        select(UserAccount).where(UserAccount.email == payload.email)
    ).scalar_one_or_none()

    unauthorized_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None:
        raise unauthorized_exc

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User account has no password configured.",
        )

    if not verify_password(payload.password, user.password_hash):
        raise unauthorized_exc

    # Resolve role_code ONCE at login-time (so we avoid per-request role lookups).
    role = db.execute(select(Role).where(Role.id == user.role_id)).scalar_one_or_none()
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role is invalid or missing.",
        )

    token = create_access_token(
        subject=str(user.id),
        extra_claims={
            # Convenience claims for downstream layers
            "email": user.email,
            "role_id": int(user.role_id),
            "role_code": str(role.code),  # <-- NEW: role-coded JWT
            "branch_id": int(user.branch_id),
        },
    )

    expires_in_seconds = int(settings.auth_access_token_expires_minutes) * 60

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in_seconds,
    )
