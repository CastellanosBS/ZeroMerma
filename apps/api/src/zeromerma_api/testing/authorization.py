"""Explicit owner provisioning for functional tests on an authorized disposable database."""

from __future__ import annotations

import os

from sqlalchemy.orm import Session

from zeromerma_api.modules.identity.application.security import TokenService
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
    from zeromerma_api.db.session import SessionLocal

    with SessionLocal() as session:
        owner = provision_test_owner(session)
        token = TokenService().issue_access_token(owner.id)
        session.commit()
    return {"Authorization": f"Bearer {token}"}
