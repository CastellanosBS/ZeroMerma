from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.cash.domain.constants import CASH_SESSION_STATUS_CLOSED
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.discounts.infrastructure.models import (
    OperationalDiscount,
    OperationalDiscountCategory,
)
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.modules.identity.infrastructure.models import User, UserBranchAssignment
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.sales.infrastructure.models import CashMovement
from zeromerma_api.testing.idempotency import current_cash_session_id, new_idempotency_key
from zeromerma_api.testing.sessions import login_headers


def _login(client: TestClient) -> dict[str, str]:
    return login_headers(client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD, audience="POS")


def _authorization_header(client: TestClient) -> dict[str, str]:
    return _login(client)


def _open_cash_session(client: TestClient) -> None:
    response = client.post(
        "/v1/cash-sessions/open",
        headers={**_authorization_header(client), "Idempotency-Key": new_idempotency_key()},
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "opening_amount": "300.00",
        },
    )
    assert response.status_code == 201


def _get_category_code(code: str) -> str:
    with SessionLocal() as session:
        category = session.execute(
            select(OperationalDiscountCategory).where(OperationalDiscountCategory.code == code)
        ).scalar_one()
    return category.code


def test_discounts_bootstrap_list_detail_and_cash_commit_work_end_to_end(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    headers = {
        **_authorization_header(client),
        "X-Request-ID": "8ff80c16-e473-5f5d-bd95-2437501d5660",
    }

    bootstrap_response = client.get(
        "/v1/discounts/bootstrap",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=headers,
    )

    assert bootstrap_response.status_code == 200
    bootstrap_payload = bootstrap_response.json()
    assert bootstrap_payload["discount_registration_allowed"] is True
    assert bootstrap_payload["default_scope"] == "CURRENT_SHIFT"
    assert [entry["code"] for entry in bootstrap_payload["available_scopes"]] == [
        "CURRENT_SHIFT",
        "TODAY",
        "RECENT",
    ]
    assert bootstrap_payload["discount_controls"]["high_value_amount_threshold"] == "200"
    assert bootstrap_payload["discount_controls"]["high_value_requires_acknowledgement"] is True
    assert [entry["code"] for entry in bootstrap_payload["active_discount_methods"]] == [
        "CASH",
        "CARD",
        "MIXED",
    ]
    assert bootstrap_payload["active_discount_methods"][2]["is_enabled"] is False

    cash_command_headers = {**headers, "Idempotency-Key": new_idempotency_key()}
    cash_command_cash_session_id = current_cash_session_id(
        client, headers=cash_command_headers, workstation_code=SEED_WORKSTATION_CODE
    )

    create_response = client.post(
        "/v1/discounts",
        headers=cash_command_headers,
        json={
            "cash_session_id": cash_command_cash_session_id,
            "workstation_code": SEED_WORKSTATION_CODE,
            "subject_name": "Empleado Juan",
            "concept": "Prestamo interno abril",
            "category_code": _get_category_code("EMPLOYEE_LOAN"),
            "payment_method_code": "CASH",
            "total_amount": "125.50",
            "notes": "Descuento del turno",
        },
    )

    assert create_response.status_code == 201
    detail_payload = create_response.json()
    assert detail_payload["folio"].startswith("DES-")
    assert detail_payload["payment_method_code"] == "CASH"
    assert Decimal(str(detail_payload["total_amount"])) == Decimal("125.50")
    assert Decimal(str(detail_payload["cash_amount"])) == Decimal("125.50")

    list_response = client.get(
        "/v1/discounts",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "query": "prestamo",
            "payment_method": "CASH",
        },
        headers=headers,
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert len(list_payload["discounts"]) == 1
    assert list_payload["discounts"][0]["id"] == detail_payload["id"]
    assert list_payload["discounts"][0]["category_code"] == "EMPLOYEE_LOAN"
    assert list_payload["discounts"][0]["branch_code"] == "MAIN"
    assert list_payload["discounts"][0]["workstation_code"] == SEED_WORKSTATION_CODE

    reread_response = client.get(
        f"/v1/discounts/{detail_payload['id']}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=headers,
    )
    assert reread_response.status_code == 200
    reread_payload = reread_response.json()
    assert reread_payload["id"] == detail_payload["id"]
    assert reread_payload["affects_cash_drawer"] is True
    assert reread_payload["audit_summary"]["created_by"]["email"] == SEED_USER_EMAIL
    assert reread_payload["audit_summary"]["confirmed_by"]["full_name"] == "Main Branch Cashier"

    with SessionLocal() as session:
        discount_record = session.execute(
            select(OperationalDiscount).where(OperationalDiscount.id == detail_payload["id"])
        ).scalar_one()
        assert (
            session.scalar(
                select(CashMovement).where(
                    CashMovement.movement_type == "OPERATIONAL_DISCOUNT",
                )
            )
            is None
        )
        operation = session.scalars(
            select(FinancialOperation).where(FinancialOperation.source_id == discount_record.id)
        ).one()
        entry = session.scalars(
            select(FinancialEntry).where(FinancialEntry.financial_operation_id == operation.id)
        ).one()
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.action == "operational_discount.committed",
                AuditLog.resource_id == str(discount_record.id),
            )
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == str(discount_record.id),
                OutboxEvent.event_name == "operational_discount.committed.v1",
            )
        ).scalar_one()

    assert detail_payload["cash_movement_id"] is None
    assert operation.kind == "OPERATIONAL_CHARGE"
    assert operation.source_type == operation.subject_type == "OPERATIONAL_DISCOUNT"
    assert operation.subject_id == discount_record.id
    assert operation.amount_due == entry.amount == Decimal("125.50")
    assert entry.direction == "IN" and entry.payment_method_code == "CASH"
    assert entry.state == "CONFIRMED" and entry.execution_mode == "LOCAL"
    assert operation.branch_id == entry.branch_id == discount_record.branch_id
    assert operation.workstation_id == entry.workstation_id == discount_record.workstation_id
    assert (
        operation.cash_session_id == entry.cash_session_id == discount_record.active_cash_session_id
    )
    assert operation.actor_id == entry.actor_id == discount_record.created_by_user_id
    assert audit_record.request_id == "8ff80c16-e473-5f5d-bd95-2437501d5660"
    assert outbox_event.payload["payment_method_code"] == "CASH"
    for trace in (audit_record.metadata_, outbox_event.payload, outbox_event.headers):
        assert trace["financial_operation_id"] == str(operation.id)
        assert trace["financial_entry_ids"] == [str(entry.id)]
    assert operation.operation_id == entry.operation_id == audit_record.operation_id
    assert operation.operation_id == outbox_event.operation_id


def test_card_discount_does_not_change_drawer_cash_but_cash_discount_does(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    headers = _authorization_header(client)

    cash_command_headers = {**headers, "Idempotency-Key": new_idempotency_key()}
    cash_command_cash_session_id = current_cash_session_id(
        client, headers=cash_command_headers, workstation_code=SEED_WORKSTATION_CODE
    )

    card_response = client.post(
        "/v1/discounts",
        headers=cash_command_headers,
        json={
            "cash_session_id": cash_command_cash_session_id,
            "workstation_code": SEED_WORKSTATION_CODE,
            "subject_name": "Empleado Ana",
            "concept": "Seguro quincenal",
            "category_code": _get_category_code("EMPLOYEE_INSURANCE"),
            "payment_method_code": "CARD",
            "total_amount": "90.00",
        },
    )
    assert card_response.status_code == 201
    assert Decimal(str(card_response.json()["cash_amount"])) == Decimal("0.00")

    cash_command_headers = {**headers, "Idempotency-Key": new_idempotency_key()}
    cash_command_cash_session_id = current_cash_session_id(
        client, headers=cash_command_headers, workstation_code=SEED_WORKSTATION_CODE
    )

    cash_response = client.post(
        "/v1/discounts",
        headers=cash_command_headers,
        json={
            "cash_session_id": cash_command_cash_session_id,
            "workstation_code": SEED_WORKSTATION_CODE,
            "subject_name": "Empleado Luis",
            "concept": "Cargo interno",
            "category_code": _get_category_code("INTERNAL_CHARGE"),
            "payment_method_code": "CASH",
            "total_amount": "40.00",
        },
    )
    assert cash_response.status_code == 201

    with SessionLocal() as session:
        assert (
            session.scalar(
                select(CashMovement).where(CashMovement.movement_type == "OPERATIONAL_DISCOUNT")
            )
            is None
        )
        entries = (
            session.execute(
                select(FinancialEntry)
                .join(
                    FinancialOperation,
                    FinancialOperation.id == FinancialEntry.financial_operation_id,
                )
                .where(FinancialOperation.kind == "OPERATIONAL_CHARGE")
            )
            .scalars()
            .all()
        )

    assert len(entries) == 2
    by_method = {entry.payment_method_code: entry for entry in entries}
    assert set(by_method) == {"CASH", "CARD"}
    assert by_method["CASH"].amount == Decimal("40.00")
    assert by_method["CASH"].execution_mode == "LOCAL"
    assert by_method["CARD"].amount == Decimal("90.00")
    assert by_method["CARD"].execution_mode == "ACCOUNTING_ONLY"
    assert by_method["CARD"].resolution_kind == "EXTERNAL_RECORDING"
    assert by_method["CARD"].resolution_reference == uuid.UUID(card_response.json()["id"])
    for entry in entries:
        assert entry.state == "CONFIRMED" and entry.direction == "IN"
        assert str(entry.cash_session_id) == cash_command_cash_session_id


def test_discounts_require_open_session_and_reject_unsupported_methods_and_missing_high_value_ack(
    client: TestClient,
) -> None:
    no_session_response = client.get(
        "/v1/discounts",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_authorization_header(client),
    )
    assert no_session_response.status_code == 409
    assert (
        no_session_response.json()["message"]
        == "Necesitas una caja abierta en esta estacion para registrar descuentos."
    )

    _open_cash_session(client)
    cash_command_headers = {
        **_authorization_header(client),
        "Idempotency-Key": new_idempotency_key(),
    }
    cash_command_cash_session_id = current_cash_session_id(
        client, headers=cash_command_headers, workstation_code=SEED_WORKSTATION_CODE
    )

    unsupported_method_response = client.post(
        "/v1/discounts",
        headers=cash_command_headers,
        json={
            "cash_session_id": cash_command_cash_session_id,
            "workstation_code": SEED_WORKSTATION_CODE,
            "subject_name": "Registro mixto",
            "concept": "Prueba de metodo no disponible",
            "payment_method_code": "MIXED",
            "total_amount": "10.00",
        },
    )
    assert unsupported_method_response.status_code == 400
    assert "efectivo o tarjeta" in unsupported_method_response.json()["message"]

    cash_command_headers = {
        **_authorization_header(client),
        "Idempotency-Key": new_idempotency_key(),
    }
    cash_command_cash_session_id = current_cash_session_id(
        client, headers=cash_command_headers, workstation_code=SEED_WORKSTATION_CODE
    )

    high_value_response = client.post(
        "/v1/discounts",
        headers=cash_command_headers,
        json={
            "cash_session_id": cash_command_cash_session_id,
            "workstation_code": SEED_WORKSTATION_CODE,
            "subject_name": "Empleado Rosa",
            "concept": "Descuento extraordinario",
            "category_code": _get_category_code("OTHER"),
            "payment_method_code": "CARD",
            "total_amount": "250.00",
        },
    )
    assert high_value_response.status_code == 400
    assert "alto valor" in high_value_response.json()["message"]


def test_discounts_list_supports_scope_and_operator_filters_and_high_value_alerts(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    headers = {
        **_authorization_header(client),
        "X-Request-ID": "343f3f88-2ffa-5e93-9ea5-e0d1242e0a8f",
    }

    cash_command_headers = {**headers, "Idempotency-Key": new_idempotency_key()}
    cash_command_cash_session_id = current_cash_session_id(
        client, headers=cash_command_headers, workstation_code=SEED_WORKSTATION_CODE
    )

    create_response = client.post(
        "/v1/discounts",
        headers=cash_command_headers,
        json={
            "cash_session_id": cash_command_cash_session_id,
            "workstation_code": SEED_WORKSTATION_CODE,
            "subject_name": "Empleado turno actual",
            "concept": "DES-TURNO",
            "category_code": _get_category_code("EMPLOYEE_LOAN"),
            "payment_method_code": "CASH",
            "total_amount": "80.00",
        },
    )
    assert create_response.status_code == 201

    with SessionLocal() as session:
        current_discount = session.execute(
            select(OperationalDiscount).where(
                OperationalDiscount.id == create_response.json()["id"]
            )
        ).scalar_one()

        second_user = User(
            id=uuid.uuid4(),
            email="discounts-operator@zeromerma.local",
            full_name="Second Discounts Operator",
            password_hash="seed-password-hash",
            is_active=True,
        )
        session.add(second_user)
        session.flush()
        session.add(
            UserBranchAssignment(
                user_id=second_user.id,
                branch_id=current_discount.branch_id,
                is_active=True,
            )
        )
        historical_cash_session = CashSession(
            branch_id=current_discount.branch_id,
            workstation_id=current_discount.workstation_id,
            user_id=second_user.id,
            status=CASH_SESSION_STATUS_CLOSED,
            opening_amount=Decimal("150.00"),
            opened_at=datetime.now(tz=UTC) - timedelta(days=2, hours=2),
            closed_at=datetime.now(tz=UTC) - timedelta(days=2),
        )
        session.add(historical_cash_session)
        session.flush()
        historical_discount = OperationalDiscount(
            branch_id=current_discount.branch_id,
            workstation_id=current_discount.workstation_id,
            created_by_user_id=second_user.id,
            active_cash_session_id=historical_cash_session.id,
            subject_name="Empleado historico",
            concept="DES-HISTORICO",
            category_code=_get_category_code("OTHER"),
            notes="Descuento de consulta historica",
            payment_method_code="CARD",
            currency_code="MXN",
            total_amount=Decimal("90.00"),
            cash_amount=Decimal("0.00"),
            non_cash_amount=Decimal("90.00"),
            status="COMMITTED",
            created_at_utc=datetime.now(tz=UTC) - timedelta(days=2),
            committed_at_utc=datetime.now(tz=UTC) - timedelta(days=2),
        )
        session.add(historical_discount)
        session.commit()

    bootstrap_response = client.get(
        "/v1/discounts/bootstrap",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=headers,
    )
    assert bootstrap_response.status_code == 200
    current_user_id = str(bootstrap_response.json()["user"]["id"])

    current_shift_response = client.get(
        "/v1/discounts",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "scope": "CURRENT_SHIFT",
        },
        headers=headers,
    )
    assert current_shift_response.status_code == 200
    current_shift_payload = current_shift_response.json()
    assert current_shift_payload["scope"] == "CURRENT_SHIFT"
    assert len(current_shift_payload["discounts"]) == 1
    assert current_shift_payload["discounts"][0]["concept"] == "DES-TURNO"

    recent_response = client.get(
        "/v1/discounts",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "scope": "RECENT",
        },
        headers=headers,
    )
    assert recent_response.status_code == 200
    recent_payload = recent_response.json()
    assert len(recent_payload["discounts"]) == 2
    assert {entry["label"] for entry in recent_payload["available_users"]} == {
        "Main Branch Cashier",
        "Second Discounts Operator",
    }

    operator_filter_response = client.get(
        "/v1/discounts",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "scope": "RECENT",
            "created_by_user_id": str(second_user.id),
            "query": "historico",
        },
        headers=headers,
    )
    assert operator_filter_response.status_code == 200
    operator_filter_payload = operator_filter_response.json()
    assert operator_filter_payload["created_by_user_id"] == str(second_user.id)
    assert len(operator_filter_payload["discounts"]) == 1
    assert operator_filter_payload["discounts"][0]["subject_name"] == "Empleado historico"

    today_response = client.get(
        "/v1/discounts",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "scope": "TODAY",
            "created_by_user_id": current_user_id,
        },
        headers=headers,
    )
    assert today_response.status_code == 200
    today_payload = today_response.json()
    assert len(today_payload["discounts"]) == 1

    cash_command_headers = {**headers, "Idempotency-Key": new_idempotency_key()}
    cash_command_cash_session_id = current_cash_session_id(
        client, headers=cash_command_headers, workstation_code=SEED_WORKSTATION_CODE
    )

    high_value_response = client.post(
        "/v1/discounts",
        headers=cash_command_headers,
        json={
            "cash_session_id": cash_command_cash_session_id,
            "workstation_code": SEED_WORKSTATION_CODE,
            "subject_name": "Empleado alto valor",
            "concept": "Descuento especial",
            "category_code": _get_category_code("OTHER"),
            "payment_method_code": "CARD",
            "total_amount": "250.00",
            "high_value_acknowledged": True,
        },
    )
    assert high_value_response.status_code == 201

    with SessionLocal() as session:
        discount_record = session.execute(
            select(OperationalDiscount).where(
                OperationalDiscount.id == high_value_response.json()["id"]
            )
        ).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.action == "operational_discount.committed",
                AuditLog.resource_id == str(discount_record.id),
            )
        ).scalar_one()
        alert_audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.action == "operational_discount.high_value_alert_requested",
                AuditLog.resource_id == str(discount_record.id),
            )
        ).scalar_one()
        alert_event = session.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == str(discount_record.id),
                OutboxEvent.event_name == "operational_discount.high_value_alert.v1",
            )
        ).scalar_one()

    assert audit_record.metadata_["high_value"] is True
    assert audit_record.metadata_["high_value_acknowledged"] is True
    assert alert_audit_record.metadata_["notification_target"] == "backoffice"
    assert alert_event.payload["notification_target"] == "backoffice"

    detail_response = client.get(
        f"/v1/discounts/{high_value_response.json()['id']}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=headers,
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["audit_summary"]["acknowledged_by"]["email"] == SEED_USER_EMAIL
    assert detail_payload["audit_summary"]["backoffice_notification"]["status"] == "PENDING"
