# apps/backend/src/zeromerma_api/core/request_context.py
# PURPOSE:
#   Store per-request context data (request_id, user_id, role_code, branch_id)
#   using contextvars so logs can automatically include them.
#
# WHY contextvars:
#   - Safe for async (FastAPI/Starlette)
#   - Values are isolated per request/task
#   - Works without passing "extra=" everywhere in code

from __future__ import annotations

import contextvars
from dataclasses import dataclass

# Defaults must exist so the log formatter never crashes.
_request_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)
_user_id: contextvars.ContextVar[str] = contextvars.ContextVar("user_id", default="-")
_role_code: contextvars.ContextVar[str] = contextvars.ContextVar(
    "role_code", default="-"
)
_branch_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "branch_id", default="-"
)


@dataclass(frozen=True)
class RequestContextTokens:
    """
    Holds tokens returned by ContextVar.set() so we can reset them later.
    """

    request_id: contextvars.Token[str]
    user_id: contextvars.Token[str]
    role_code: contextvars.Token[str]
    branch_id: contextvars.Token[str]


def set_request_context(
    *,
    request_id: str = "-",
    user_id: str = "-",
    role_code: str = "-",
    branch_id: str = "-",
) -> RequestContextTokens:
    """
    Set per-request context values for the current async task.

    Returns tokens that must be used to reset the context afterwards.
    """
    return RequestContextTokens(
        request_id=_request_id.set(request_id),
        user_id=_user_id.set(user_id),
        role_code=_role_code.set(role_code),
        branch_id=_branch_id.set(branch_id),
    )


def reset_request_context(tokens: RequestContextTokens) -> None:
    """
    Reset per-request context to previous values.
    """
    _request_id.reset(tokens.request_id)
    _user_id.reset(tokens.user_id)
    _role_code.reset(tokens.role_code)
    _branch_id.reset(tokens.branch_id)


def get_request_id() -> str:
    return _request_id.get()


def get_user_id() -> str:
    return _user_id.get()


def get_role_code() -> str:
    return _role_code.get()


def get_branch_id() -> str:
    return _branch_id.get()
