"""Explicit owner provisioning for functional tests on an authorized disposable database."""

from __future__ import annotations

import os

from sqlalchemy.orm import Session

from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.identity.infrastructure.privileged_models import IdentityPrivilegeState
from zeromerma_api.testing.database_safety import (
    assert_authorized_destructive_connection,
    load_destructive_test_database_config,
)

TEST_OWNER_EMAIL = "owner@authorization.example.test"
TEST_OWNER_PASSWORD = "Isolated-owner-password-8041"
TEST_OWNER_HOST = "isolated-test-control-plane"


def provision_test_owner(session: Session) -> User:
    from zeromerma_api.modules.identity.application.privileged_access import PrivilegedAccessService

    config = load_destructive_test_database_config(os.environ)
    assert_authorized_destructive_connection(session.connection(), config)
    state = session.get(IdentityPrivilegeState, 1)
    if state is not None and state.initial_owner_user_id is not None:
        owner = session.get(User, state.initial_owner_user_id)
        if owner is None or owner.email != TEST_OWNER_EMAIL:
            raise RuntimeError("This fixture cannot replace a previously designated owner.")
        return owner
    result = PrivilegedAccessService().bootstrap_owner(
        session,
        email=TEST_OWNER_EMAIL,
        full_name="Isolated Test Owner",
        password=TEST_OWNER_PASSWORD,
        authorized_host=TEST_OWNER_HOST,
    )
    owner = session.get(User, result.user_id)
    if owner is None:
        raise RuntimeError("The owner provisioning service did not create its designated user.")
    return owner


def owner_headers() -> dict[str, str]:
    """Provision an authorized fixture session without exercising the HTTP login route.

    Login and password/rate-limit behavior are covered by dedicated HTTP tests.
    Functional owner tests still use persisted sessions, canonical authorization,
    session lifecycle events and the production cookie/CSRF request boundary.
    """
    load_destructive_test_database_config(os.environ)

    from zeromerma_api.db.session import SessionLocal
    from zeromerma_api.modules.identity.application.security import csrf_for_credential
    from zeromerma_api.modules.identity.application.session_services import (
        COOKIE_NAMES,
        SessionService,
        set_audit_context,
    )
    from zeromerma_api.testing.sessions import surface_origin

    with SessionLocal() as session:
        owner = provision_test_owner(session)
        set_audit_context(session, owner.id, "isolated-owner-session-fixture")
        authentication = SessionService().create_session(session, user=owner, audience="BACKOFFICE")
        headers = {
            "Cookie": f"{COOKIE_NAMES['BACKOFFICE']}={authentication.credential}",
            "X-CSRF-Token": csrf_for_credential(authentication.credential),
            "X-ZeroMerma-Surface": "BACKOFFICE",
            "Origin": surface_origin("BACKOFFICE"),
        }
        session.commit()
        return headers
