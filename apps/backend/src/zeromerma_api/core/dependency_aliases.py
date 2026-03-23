# apps/backend/src/zeromerma_api/core/dependency_aliases.py
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from zeromerma_api.core.auth_context import AuthContext
from zeromerma_api.core.deps_auth import (
    get_current_active_auth_context,
    get_current_active_user,
)
from zeromerma_api.db.engine import get_session
from zeromerma_api.models.user_account import UserAccount

DbSessionDep = Annotated[Session, Depends(get_session)]
ActiveUserDep = Annotated[UserAccount, Depends(get_current_active_user)]
ActiveAuthContextDep = Annotated[
    AuthContext,
    Depends(get_current_active_auth_context),
]
