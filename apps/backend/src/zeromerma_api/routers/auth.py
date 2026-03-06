# apps/backend/src/zeromerma_api/routers/auth.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.core.security import create_access_token, verify_password
from zeromerma_api.core.settings import get_settings
from zeromerma_api.db.engine import get_session
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
    5) Issue a signed JWT access token.

    Security behavior:
    - We intentionally return a generic 401 for invalid credentials.
    - We do not reveal whether the email or the password was wrong.
    """

    settings = get_settings()

    # Look up the account by its unique email.
    user = db.execute(
        select(UserAccount).where(UserAccount.email == payload.email)
    ).scalar_one_or_none()

    # Generic auth failure to avoid leaking which part was invalid.
    unauthorized_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # If no account exists, fail generically.
    if user is None:
        raise unauthorized_exc

    # Do not allow login for inactive users.
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    # If the account exists but has no password hash, login cannot work yet.
    # This is common during bootstrap before all seeded users are updated.
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User account has no password configured.",
        )

    # Verify the provided plain password against the stored hash.
    if not verify_password(payload.password, user.password_hash):
        raise unauthorized_exc

    # Build a token with the user id as the canonical subject.
    # We also include a few practical claims that are useful to downstream code.
    token = create_access_token(
        subject=str(user.id),
        extra_claims={
            "email": user.email,
            "role_id": user.role_id,
            "branch_id": user.branch_id,
        },
    )

    # Convert configured token lifetime to seconds for client convenience.
    expires_in_seconds = int(settings.auth_access_token_expires_minutes) * 60

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in_seconds,
    )
