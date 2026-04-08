from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.modules.identity.application.schemas import (
    AuthenticatedUser,
    LoginRequest,
    LoginResponse,
)
from zeromerma_api.modules.identity.application.services import AuthService
from zeromerma_api.modules.identity.domain.exceptions import InvalidCredentialsError
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user

router = APIRouter(prefix="/v1/auth", tags=["auth"])


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
def me(current_user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> AuthenticatedUser:
    return current_user
