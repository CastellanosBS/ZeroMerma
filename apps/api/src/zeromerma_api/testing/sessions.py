"""Cookie-authenticated HTTP fixtures for isolated application tests."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from http.cookies import SimpleCookie

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.bootstrap.seed_local import SEED_WORKSTATION_CODE
from zeromerma_api.modules.branches.infrastructure.models import Workstation
from zeromerma_api.modules.identity.application.schemas import IdentitySurface
from zeromerma_api.modules.identity.application.security import new_session_secrets, secret_hash
from zeromerma_api.modules.identity.application.session_services import (
    ABSOLUTE_HOURS,
    COOKIE_NAMES,
    IDLE_MINUTES,
)
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.identity.infrastructure.session_models import AuthSession
from zeromerma_api.testing.database_safety import (
    assert_authorized_destructive_connection,
    load_destructive_test_database_config,
)


def surface_origin(audience: IdentitySurface) -> str:
    return "http://localhost:5173" if audience == "POS" else "http://localhost:5174"


def response_session_headers(response: Response, audience: IdentitySurface) -> dict[str, str]:
    """Keep the actual response credential and CSRF pairing without a bearer adapter."""
    assert response.status_code == 200, response.text
    cookie_name = "__Host-zm-pos-session" if audience == "POS" else "__Host-zm-backoffice-session"
    cookies = SimpleCookie()
    for value in response.headers.get_list("set-cookie"):
        cookies.load(value)
    credential = cookies[cookie_name].value
    payload = response.json()
    assert "access_token" not in payload
    assert payload["session"]["audience"] == audience
    return {
        "Cookie": f"{cookie_name}={credential}",
        "X-CSRF-Token": str(payload["csrf_token"]),
        "X-ZeroMerma-Surface": audience,
        "Origin": surface_origin(audience),
    }


def login_headers(
    client: TestClient,
    *,
    email: str,
    password: str,
    audience: IdentitySurface = "POS",
    workstation_code: str = SEED_WORKSTATION_CODE,
) -> dict[str, str]:
    payload = {"email": email, "password": password, "audience": audience}
    if audience == "POS":
        payload["workstation_code"] = workstation_code
    response = client.post(
        "/v1/auth/login",
        json=payload,
        headers={"Origin": surface_origin(audience), "X-ZeroMerma-Surface": audience},
    )
    # Every request in these fixtures chooses its identity explicitly. In particular,
    # an anonymous request must not inherit cookies from a previous helper login.
    client.cookies.clear()
    headers = response_session_headers(response, audience)
    assert response.json()["user"]["email"] == email.strip().lower()
    return headers


def fixture_session_headers(
    session: Session,
    user: User,
    *,
    audience: IdentitySurface = "BACKOFFICE",
    workstation_code: str = SEED_WORKSTATION_CODE,
) -> dict[str, str]:
    """Construct DB session state for authorization tests, including grantless actors.

    This fixture is restricted to the guarded disposable database. It deliberately
    does not authenticate a password: login behavior uses the real HTTP helper above.
    It permits testing the request boundary independently from login eligibility.
    """
    config = load_destructive_test_database_config(os.environ)
    assert_authorized_destructive_connection(session.connection(), config)
    workstation_id = None
    if audience == "POS":
        workstation_id = session.scalars(
            select(Workstation.id).where(Workstation.code == workstation_code)
        ).one()
    credential, csrf = new_session_secrets()
    now = datetime.now(UTC)
    session.add(
        AuthSession(
            credential_hash=secret_hash(credential),
            csrf_hash=secret_hash(csrf),
            user_id=user.id,
            audience=audience,
            status="ACTIVE",
            created_at=now,
            last_activity_at=now,
            idle_expires_at=now + timedelta(minutes=IDLE_MINUTES[audience]),
            absolute_expires_at=now + timedelta(hours=ABSOLUTE_HOURS[audience]),
            workstation_id=workstation_id,
            cash_session_id=None,
        )
    )
    session.flush()
    return {
        "Cookie": f"{COOKIE_NAMES[audience]}={credential}",
        "X-CSRF-Token": csrf,
        "X-ZeroMerma-Surface": audience,
        "Origin": surface_origin(audience),
    }
