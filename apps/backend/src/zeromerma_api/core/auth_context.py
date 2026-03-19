# apps/backend/src/zeromerma_api/core/auth_context.py
from __future__ import annotations

from dataclasses import dataclass

from zeromerma_api.models.user_account import UserAccount


@dataclass(frozen=True)
class AuthContext:
    """
    Auth context resolved from a JWT.

    This keeps routers clean:
      - ctx.user: the DB user
      - ctx.role_code: role code claim (ADMIN/CASHIER)
    """

    user: UserAccount
    role_code: str
