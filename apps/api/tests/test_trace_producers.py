"""Existing audit-only operations publish minimal events in their owning transaction."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from zeromerma_api.bootstrap.seed_local import (
    SEED_BRANCH_CODE,
    SEED_PRODUCT_CLASS_BOLILLO_CODE,
    SEED_PRODUCT_COCA_355_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.core.operation_context import OperationContext, SourceApp
from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.db.operation_context import bind_operation_context
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.configuration.infrastructure.models import (
    SystemSetting,
    SystemSettingHistory,
)
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.suppliers.infrastructure.models import (
    Supplier,
    SupplierBranch,
    SupplierContact,
    SupplierProduct,
)
from zeromerma_api.modules.tickets.application.services import TicketsCommandService
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.sessions import login_headers

CASES = (
    "input_create_relation",
    "input_update_relation",
    "supplier_create_contact",
    "supplier_update_contact",
    "supplier_create_product",
    "supplier_update_product",
    "supplier_branch",
    "setting_update",
    "setting_reset",
    "report_export",
    "pos_reprint",
    "admin_reprint",
)
PRIVATE_MARKER = "Contact detail excluded from event payload"


@dataclass(frozen=True)
class _Case:
    method: str
    path: str
    payload: dict[str, Any]
    headers: dict[str, str]
    event_name: str
    branch_id: uuid.UUID | None = None
    source_app: str = "BACKOFFICE"
    workstation_id: uuid.UUID | None = None
    cash_session_id: uuid.UUID | None = None


def _post(
    client: TestClient, path: str, headers: dict[str, str], payload: dict[str, Any]
) -> dict[str, Any]:
    response = client.post(path, headers=headers, json=payload)
    assert response.status_code in {200, 201}
    return dict(response.json())


def _prepare(client: TestClient, kind: str) -> _Case:
    headers = owner_headers()
    with SessionLocal() as session:
        branch_id = session.scalars(select(Branch.id).where(Branch.code == SEED_BRANCH_CODE)).one()
        product_id = session.scalars(
            select(Product.id).where(Product.code == SEED_PRODUCT_COCA_355_CODE)
        ).one()
        class_id = session.scalars(
            select(ProductClass.id).where(ProductClass.code == SEED_PRODUCT_CLASS_BOLILLO_CODE)
        ).one()

    if kind.startswith("setting"):
        key = "general.business_name"
        if kind == "setting_reset":
            response = client.patch(
                f"/v1/admin/settings/{key}", headers=headers, json={"value": PRIVATE_MARKER}
            )
            assert response.status_code == 200
            return _Case(
                "POST", f"/v1/admin/settings/{key}/reset", {}, headers, "admin.setting.reset.v1"
            )
        return _Case(
            "PATCH",
            f"/v1/admin/settings/{key}",
            {"value": PRIVATE_MARKER},
            headers,
            "admin.setting.updated.v1",
        )

    if kind == "report_export":
        return _Case(
            "POST",
            "/v1/admin/reports/user_access_summary/export",
            {"format": "json", "filters": {"branch_id": str(branch_id)}},
            headers,
            "admin.report.exported.v1",
            branch_id=branch_id,
        )

    if kind.endswith("reprint"):
        pos_headers = login_headers(
            client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD, audience="POS"
        )
        opened = _post(
            client,
            "/v1/cash-sessions/open",
            {**pos_headers, "Idempotency-Key": new_idempotency_key()},
            {"workstation_code": SEED_WORKSTATION_CODE, "opening_amount": "20.00"},
        )
        sale = _post(
            client,
            "/v1/sales/confirm",
            {**pos_headers, "Idempotency-Key": new_idempotency_key()},
            {
                "cash_session_id": opened["id"],
                "workstation_code": SEED_WORKSTATION_CODE,
                "lines": [
                    {
                        "capture_mode": "PRODUCT_DIRECT",
                        "product_id": str(product_id),
                        "quantity": "1",
                    }
                ],
                "payments": [{"payment_method_code": "CASH", "tendered_amount": "100"}],
            },
        )
        if kind == "admin_reprint":
            return _Case(
                "POST",
                f"/v1/admin/sales/tickets/{sale['id']}/reprint",
                {},
                headers,
                "ticket.reprinted.v1",
                branch_id=branch_id,
            )
        return _Case(
            "POST",
            f"/v1/tickets/{sale['id']}/reprint",
            {"workstation_code": SEED_WORKSTATION_CODE},
            pos_headers,
            "ticket.reprinted.v1",
            branch_id=branch_id,
            source_app="POS",
            workstation_id=uuid.UUID(opened["workstation_id"]),
            cash_session_id=uuid.UUID(opened["id"]),
        )

    supplier = _post(
        client,
        "/v1/admin/suppliers",
        headers,
        {"code": "TRACE-SUPPLIER", "legal_name": PRIVATE_MARKER},
    )
    supplier_id = supplier["overview"]["id"]
    base = f"/v1/admin/suppliers/{supplier_id}"
    if kind.startswith("input"):
        product = _post(
            client,
            "/v1/admin/inputs-supplies",
            headers,
            {
                "code": "TRACE-INPUT",
                "name": "Trace input",
                "product_kind": "RAW_MATERIAL",
                "product_class_id": str(class_id),
                "unit_of_measure": "KG",
            },
        )
        input_id = product["overview"]["id"]
        path = f"/v1/admin/inputs-supplies/{input_id}/suppliers"
        payload = {"supplier_id": supplier_id, "notes": PRIVATE_MARKER}
        if kind == "input_update_relation":
            _post(client, path, headers, {"supplier_id": supplier_id})
            with SessionLocal() as session:
                relation_id = session.scalars(
                    select(SupplierProduct.id).where(
                        SupplierProduct.product_id == uuid.UUID(input_id)
                    )
                ).one()
            return _Case(
                "PATCH",
                f"{path}/{relation_id}",
                payload,
                headers,
                "admin.input_supply.supplier_relation.updated.v1",
            )
        return _Case(
            "POST", path, payload, headers, "admin.input_supply.supplier_relation.updated.v1"
        )
    if kind.endswith("contact"):
        payload = {
            "name": PRIVATE_MARKER,
            "email": "private-contact@example.test",
            "notes": PRIVATE_MARKER,
        }
        if kind == "supplier_update_contact":
            created = _post(
                client,
                f"{base}/contacts",
                headers,
                {"name": "Initial", "email": "initial@example.test"},
            )
            return _Case(
                "PATCH",
                f"{base}/contacts/{created['contacts'][0]['id']}",
                payload,
                headers,
                "admin.supplier.contact.updated.v1",
            )
        return _Case(
            "POST", f"{base}/contacts", payload, headers, "admin.supplier.contact.created.v1"
        )
    if kind.endswith("product"):
        payload = {"product_id": str(product_id), "notes": PRIVATE_MARKER}
        if kind == "supplier_update_product":
            created = _post(client, f"{base}/products", headers, {"product_id": str(product_id)})
            relation_id = created["product_associations"][0]["id"]
            return _Case(
                "PATCH",
                f"{base}/products/{relation_id}",
                payload,
                headers,
                "admin.supplier.product.updated.v1",
            )
        return _Case(
            "POST", f"{base}/products", payload, headers, "admin.supplier.product.linked.v1"
        )
    return _Case(
        "POST",
        f"{base}/branches",
        {"branch_id": str(branch_id), "delivery_notes": PRIVATE_MARKER},
        headers,
        "admin.supplier.branch.updated.v1",
        branch_id=branch_id,
    )


def _business_snapshot() -> tuple[object, ...]:
    with SessionLocal() as session:
        rows = []
        for model in (
            Supplier,
            SupplierContact,
            SupplierProduct,
            SupplierBranch,
            SystemSetting,
            SystemSettingHistory,
        ):
            values = session.execute(select(model.__table__)).mappings().all()
            rows.append(
                sorted(json.dumps(dict(row), default=str, sort_keys=True) for row in values)
            )
        rows.extend(
            session.scalar(select(func.count()).select_from(model))
            for model in (AuditLog, OutboxEvent)
        )
        return tuple(rows)


@pytest.mark.parametrize("kind", CASES)
def test_existing_trace_gap_writes_one_minimal_correlated_event(
    client: TestClient, kind: str
) -> None:
    case = _prepare(client, kind)
    request_id = str(uuid.uuid4())
    response = client.request(
        case.method,
        case.path,
        headers={**case.headers, "X-Request-ID": request_id},
        json=case.payload,
    )
    assert response.status_code in {200, 201}
    with SessionLocal() as session:
        event_row = session.scalars(
            select(OutboxEvent).where(
                OutboxEvent.request_id == request_id, OutboxEvent.event_name == case.event_name
            )
        ).one()
        audit = session.scalars(select(AuditLog).where(AuditLog.request_id == request_id)).one()
        assert event_row.actor_id == audit.actor_id and audit.actor_id is not None
        assert event_row.branch_id == audit.branch_id == case.branch_id
        assert event_row.source_app == audit.source_app == case.source_app
        assert event_row.context_version == audit.context_version == 1
        assert event_row.operation_id == audit.operation_id
        assert event_row.correlation_id == audit.correlation_id
        assert event_row.operation_id is not None
        assert event_row.causation_id is None
        assert event_row.recorded_at is not None and audit.recorded_at is not None
        assert event_row.schema_version == 1
        assert "None" not in event_row.payload.values()
        if case.source_app == "POS":
            assert event_row.workstation_id == audit.workstation_id == case.workstation_id
            assert event_row.cash_session_id == audit.cash_session_id == case.cash_session_id
        encoded = json.dumps(event_row.payload)
        for forbidden in (
            PRIVATE_MARKER,
            "@example.test",
            "legal_name",
            "tax_id",
            "filters",
            "old_value",
            "new_value",
            "notes",
            "rows",
        ):
            assert forbidden not in encoded


@pytest.mark.parametrize("kind", CASES)
def test_trace_gap_outbox_failure_rolls_back_domain_and_audit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    case = _prepare(client, kind)
    before = _business_snapshot()
    original = OutboxWriter.append

    def fail_after_flush(self: OutboxWriter, *args: Any, **kwargs: Any) -> OutboxEvent:
        record = original(self, *args, **kwargs)
        if record.event_name == case.event_name:
            args[0].flush()
            raise RuntimeError("Injected trace publication failure")
        return record

    with monkeypatch.context() as patch:
        patch.setattr(OutboxWriter, "append", fail_after_flush)
        with pytest.raises(RuntimeError, match="Injected trace publication failure"):
            client.request(
                case.method,
                case.path,
                headers={**case.headers, "X-Request-ID": str(uuid.uuid4())},
                json=case.payload,
            )
    assert _business_snapshot() == before
    # A new request can use the existing service owner after the failed transaction.
    response = client.request(case.method, case.path, headers=case.headers, json=case.payload)
    assert response.status_code in {200, 201}


def test_direct_pos_reprint_resolves_cash_and_workstation_in_both_traces(
    client: TestClient,
) -> None:
    case = _prepare(client, "pos_reprint")
    request_id = str(uuid.uuid4())
    ticket_id = uuid.UUID(case.path.split("/")[-2])
    with SessionLocal() as session:
        actor = session.scalars(select(User).where(User.email == SEED_USER_EMAIL)).one()
        user = resolve_authorization(session, actor, surface="POS")
        bind_authorization_scope(
            session,
            user=user,
            capabilities=("sales_tickets.reprint",),
            mutation=True,
            surface="POS",
        )
        # Direct callers supply an operation; the service resolves station/cash itself.
        bind_operation_context(
            session, OperationContext.start(SourceApp.POS, request_id=request_id)
        )
        TicketsCommandService().reprint_ticket(
            session,
            current_user=user,
            workstation_code=SEED_WORKSTATION_CODE,
            ticket_id=ticket_id,
            request_id=request_id,
        )
    with SessionLocal() as session:
        audit = session.scalars(select(AuditLog).where(AuditLog.request_id == request_id)).one()
        emitted = session.scalars(
            select(OutboxEvent).where(OutboxEvent.request_id == request_id)
        ).one()
        assert audit.workstation_id == emitted.workstation_id == case.workstation_id
        assert audit.cash_session_id == emitted.cash_session_id == case.cash_session_id
        assert audit.branch_id == emitted.branch_id == case.branch_id
        assert audit.actor_id == emitted.actor_id == user.id
        assert audit.source_app == emitted.source_app == "POS"
        assert audit.operation_id == emitted.operation_id
