"""Explicit identities and context for idempotent-command HTTP fixtures."""

from __future__ import annotations

import secrets
import time
from uuid import UUID

from fastapi.testclient import TestClient


def new_idempotency_key() -> str:
    """Create one UUIDv7 for a test intention; retries must keep the returned value."""
    return str(
        UUID(
            int=(time.time_ns() // 1_000_000 << 80)
            | (7 << 76)
            | (secrets.randbits(12) << 64)
            | (2 << 62)
            | secrets.randbits(62)
        )
    )


def current_cash_session_id(
    client: TestClient, *, headers: dict[str, str], workstation_code: str
) -> str:
    """Read the authenticated fixture's existing open session without creating one."""
    response = client.get(
        "/v1/cash-sessions/current",
        headers=headers,
        params={"workstation_code": workstation_code},
    )
    assert response.status_code == 200, response.json()
    payload = response.json()
    assert payload is not None, "The command fixture must explicitly open a cash session first."
    return str(UUID(payload["id"]))
