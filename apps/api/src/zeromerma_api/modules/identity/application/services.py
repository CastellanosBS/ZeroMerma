from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.application.security import PasswordHasher, TokenService
from zeromerma_api.modules.identity.domain.exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
)
from zeromerma_api.modules.identity.infrastructure.models import User


class AuthService:
    def __init__(
        self,
        password_hasher: PasswordHasher | None = None,
        token_service: TokenService | None = None,
    ) -> None:
        self._password_hasher = password_hasher or PasswordHasher()
        self._token_service = token_service or TokenService()

    def login(
        self,
        session: Session,
        *,
        email: str,
        password: str,
    ) -> tuple[str, AuthenticatedUser]:
        normalized_email = email.strip().lower()
        user = session.execute(
            select(User).where(User.email == normalized_email)
        ).scalar_one_or_none()
        if user is None or not user.is_active:
            raise InvalidCredentialsError("Invalid email or password.")

        if not self._password_hasher.verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password.")

        return self._token_service.issue_access_token(
            user.id
        ), AuthenticatedUser.model_validate(user)

    def get_authenticated_user(self, session: Session, token: str) -> AuthenticatedUser:
        user_id = self._token_service.read_user_id(token)
        user = session.get(User, user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Authenticated user is no longer active.")

        return AuthenticatedUser.model_validate(user)
