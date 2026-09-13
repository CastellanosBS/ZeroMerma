from __future__ import annotations

import json
import re
from typing import Any
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.db.base import Base
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.application.schemas import IdentitySurface
from zeromerma_api.modules.identity.application.security import TokenService
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.presentation.access_policy import ENDPOINT_POLICIES


def _persisted_state(session: Session) -> dict[str, list[dict[str, Any]]]:
    # Compare complete rows, including updates/deletes and outbox, not only row counts.
    return {
        table.name: [
            dict(row)
            for row in session.execute(
                select(table).order_by(*table.primary_key.columns)
            ).mappings()
        ]
        for table in Base.metadata.sorted_tables
        if table.name != AuditLog.__tablename__
    }


@pytest.mark.parametrize("surface", ["BACKOFFICE", "POS"])
def test_every_mutating_route_denies_without_capabilities_before_body_validation(
    client: TestClient, surface: IdentitySurface
) -> None:
    with SessionLocal() as session:
        user = User(
            email=f"denied-mutations-{uuid4()}@example.test",
            full_name="No-capability operator",
            password_hash="unusable",
            allowed_surfaces=["BACKOFFICE", "POS"],
            default_surface=surface,
        )
        session.add(user)
        session.commit()
        # Missing capabilities are rejected before an operation scope is bound.
        actor = resolve_authorization(session, user)
        assert actor.effective_grants == []
        token = TokenService().issue_access_token(user.id)
        before = _persisted_state(session)
        previous_audit_ids = set(session.scalars(select(AuditLog.id)))

    registered = {
        (method, route.path)
        for route in client.app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    }
    operations = {
        key: policy
        for key, policy in ENDPOINT_POLICIES.items()
        if policy.surface == surface
        and policy.capabilities
        and not policy.exception_reason
        and (policy.mutation or key[0] in {"POST", "PUT", "PATCH", "DELETE"})
    }
    assert operations
    assert set(operations).issubset(registered)
    body_secret = f"rejected-body-{uuid4().hex}"
    request_ids = {}
    for index, (method, template) in enumerate(operations):
        path = re.sub(r"\{[^}]+\}", str(uuid4()), template)
        request_id = f"denied-{surface.lower()}-{index}"
        request_ids[(method, template)] = request_id
        # Deliberately invalid domain data must never be accepted as evidence of denial (422).
        body = {"password": body_secret, "notes": body_secret}
        unauthenticated = client.request(method, path, json=body)
        assert unauthenticated.status_code == 401, (method, template, unauthenticated.text)
        denied = client.request(
            method,
            path,
            headers={"Authorization": f"Bearer {token}", "X-Request-ID": request_id},
            json=body,
        )
        assert denied.status_code == 403, (method, template, denied.text)

    with SessionLocal() as session:
        after = _persisted_state(session)
        for table_name in before:
            assert after[table_name] == before[table_name], table_name
        audits = [
            record
            for record in session.scalars(select(AuditLog))
            if record.id not in previous_audit_ids
        ]
        assert len(audits) == len(operations)
        observed = set()
        for record in audits:
            metadata = record.metadata_
            key = metadata["method"], metadata["path_template"]
            observed.add(key)
            assert key in operations
            assert record.action == "authorization.denied"
            assert record.actor_id == actor.id
            assert record.resource_type == "api_operation"
            assert record.request_id == request_ids[key]
            assert metadata["required_capabilities"] == list(operations[key].capabilities)
            assert metadata["result"] == "denied"
            provenance = metadata["authorization"]
            assert provenance["actor_id"] == str(actor.id)
            assert provenance["authorization_version"] == actor.authorization_version
            assert provenance["surface"] == surface
            assert provenance["decision"] == "DENIED"
            assert provenance["scope_type"] == "UNRESOLVED"
            assert provenance["branch_ids"] == []
            serialized = json.dumps(metadata)
            if any(secret in serialized for secret in (token, body_secret, actor.email)):
                pytest.fail(
                    "Denied-operation audit retained private request material", pytrace=False
                )
        assert observed == set(operations)
