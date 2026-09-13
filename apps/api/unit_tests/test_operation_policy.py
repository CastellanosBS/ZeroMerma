from __future__ import annotations

import pytest
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.routing import APIRoute

from zeromerma_api.db.access_scope import (
    DIRECT_SCOPE_COLUMNS,
    IDENTITY_METADATA_TABLES,
    PARENT_SCOPE_COLUMNS,
    SHARED_TABLES,
)
from zeromerma_api.db.base import Base
from zeromerma_api.modules.identity.application.permissions import PERMISSION_CODES
from zeromerma_api.presentation.access_policy import (
    ENDPOINT_POLICIES,
    enforce_operation_policy,
    get_endpoint_policy,
    install_access_policies,
)
from zeromerma_api.presentation.api import api_router


def test_every_route_and_persisted_family_has_an_explicit_policy() -> None:
    app = FastAPI()
    app.include_router(api_router)
    seen = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods:
            key = method, route.path
            seen.add(key)
            policy = get_endpoint_policy(*key)
            assert set(policy.capabilities).issubset(PERMISSION_CODES)
            if not policy.exception_reason:
                assert policy.capabilities
                assert any(
                    dependency.call is enforce_operation_policy
                    for dependency in route.dependant.dependencies
                )
    assert seen == set(ENDPOINT_POLICIES)
    classified = (
        set(DIRECT_SCOPE_COLUMNS)
        | set(PARENT_SCOPE_COLUMNS)
        | SHARED_TABLES
        | IDENTITY_METADATA_TABLES
        | {"outbox_events"}
    )
    assert set(Base.metadata.tables) == classified


def test_undeclared_endpoint_fails_closed_and_receives_a_guard() -> None:
    with pytest.raises(HTTPException) as denied:
        get_endpoint_policy("POST", "/v1/admin/undeclared-action")
    assert denied.value.status_code == 403
    router = APIRouter()

    @router.post("/v1/admin/undeclared-action")
    def endpoint() -> dict[str, bool]:
        return {"unexpected": True}

    install_access_policies(router)
    app = FastAPI()
    app.include_router(router)
    route = next(route for route in app.routes if isinstance(route, APIRoute))
    assert any(
        dependency.call is enforce_operation_policy for dependency in route.dependant.dependencies
    )


def test_sensitive_operation_splits_are_explicit() -> None:
    expected = {
        ("GET", "/v1/admin/audit/export"): ("audit.export",),
        ("POST", "/v1/admin/products/{product_id}/availability"): ("catalog.availability.manage",),
        ("POST", "/v1/tickets/{ticket_id}/reprint"): ("sales_tickets.reprint",),
        ("POST", "/v1/transfers/{transfer_id}/receive"): ("transfers.execute",),
        ("POST", "/v1/orders/{order_id}/cancel"): ("orders.cancel",),
    }
    for key, capabilities in expected.items():
        assert get_endpoint_policy(*key).capabilities == capabilities
    policies = [
        policy
        for (method, path), policy in ENDPOINT_POLICIES.items()
        if "apply-standard-cost" in path
    ]
    assert len(policies) == 1
    assert policies[0].global_only
    assert policies[0].capabilities == ("recipes.manage", "pricing.manage")
