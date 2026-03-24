# apps/backend/src/zeromerma_api/core/auth_context.py
from __future__ import annotations

from dataclasses import dataclass

from zeromerma_api.models.user_account import UserAccount


@dataclass(frozen=True, slots=True)
class AuthContext:
    """
    Resolved authentication context for protected application routes.

    Design goals:
    - Keep routers clean and explicit.
    - Expose the authenticated DB-backed user as the authoritative actor.
    - Expose the resolved role code without forcing every router to query it.
    - Preserve optional token-level branch metadata for diagnostics/future use.

    Important:
    - `user.branch_id` remains the authoritative branch assignment because it is
      loaded from the database at request time.
    - `token_branch_id` is normalized from JWT claims when present, but it does
      NOT override the user row. This prevents stale tokens from becoming the
      source of truth for branch scoping.
    """

    user: UserAccount
    role_code: str
    token_branch_id: int | None = None

    @property
    def user_id(self) -> int:
        """
        Convenience accessor for the authenticated user id.
        """
        return int(self.user.id)

    @property
    def effective_branch_id(self) -> int | None:
        """
        Return the authoritative branch id for the authenticated user.

        This value comes from the current DB user row, not from JWT claims.
        """
        if self.user.branch_id is None:
            return None
        return int(self.user.branch_id)

    @property
    def branch_id(self) -> int | None:
        """
        Alias for the authoritative effective branch id.

        This shorthand is intended for newer code that prefers `ctx.branch_id`
        over `ctx.user.branch_id`.
        """
        return self.effective_branch_id

    @property
    def has_branch_claim(self) -> bool:
        """
        Return True when the JWT included a branch_id claim.
        """
        return self.token_branch_id is not None
