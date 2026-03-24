from __future__ import annotations

from zeromerma_api.core.security import create_user_access_token


def build_auth_headers(
    *,
    user_id: int,
    role_code: str | None = None,
    branch_id: int | None = None,
) -> dict[str, str]:
    """
    Build Authorization headers for test requests.

    Standard usage:
    - new tests should prefer this helper
    - role_code and branch_id can be embedded to exercise the full token
      contract
    - omitting them still produces a backward-compatible subject-only token
    """
    token = create_user_access_token(
        user_id=user_id,
        role_code=role_code,
        branch_id=branch_id,
    )
    return {"Authorization": f"Bearer {token}"}
