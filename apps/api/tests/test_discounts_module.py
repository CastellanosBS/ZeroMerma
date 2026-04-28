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
from zeromerma_api.modules.identity.infrastructure.models import User, UserBranchAssignment
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.sales.infrastructure.models import CashMovement


def _login(client: TestClient) -> str:
    response = client.post(
        "/v1/auth/login",
        json={"email": SEED_USER_EMAIL, "password": SEED_USER_PASSWORD},
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


def _authorization_header(client: TestClient) -> dict[str, str]:
    return {"Authorization": f"Bearer {_login(client)}"}


def _open_cash_session(client: TestClient) -> None:
    response = client.post(
        "/v1/cash-sessions/open",
        headers=_authorization_header(client),
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
        "X-Request-ID": "discounts-cash-commit",
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

    create_response = client.post(
        "/v1/discounts",
        headers=headers,
        json={
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
    assert detail_payload["affects_cash_drawer"] is True

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
    assert reread_payload["audit_summary"]["created_by"]["email"] == SEED_USER_EMAIL
    assert reread_payload["audit_summary"]["confirmed_by"]["full_name"] == "Main Branch Cashier"

    with SessionLocal() as session:
        discount_record = session.execute(
            select(OperationalDiscount).where(OperationalDiscount.id == detail_payload["id"])
        ).scalar_one()
        cash_movement = session.execute(
            select(CashMovement).where(
                CashMovement.movement_type == "OPERATIONAL_DISCOUNT",
                CashMovement.sale_id.is_(None),
                CashMovement.amount == Decimal("125.50"),
            )
        ).scalar_one()
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

    assert cash_movement.direction == "IN"
    assert cash_movement.sale_id is None
    assert audit_record.request_id == "discounts-cash-commit"
    assert outbox_event.payload["payment_method_code"] == "CASH"


def test_card_discount_does_not_change_drawer_cash_but_cash_discount_does(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    headers = _authorization_header(client)

    card_response = client.post(
        "/v1/discounts",
        headers=headers,
        json={
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

    cash_response = client.post(
        "/v1/discounts",
        headers=headers,
        json={
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
        movement_rows = session.execute(
            select(CashMovement)
            .where(CashMovement.movement_type == "OPERATIONAL_DISCOUNT")
            .order_by(CashMovement.occurred_at.asc())
        ).scalars().all()

    assert len(movement_rows) == 1
    assert Decimal(str(movement_rows[0].amount)) == Decimal("40.00")


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
        no_session_response.json()["detail"]
        == "Necesitas una caja abierta en esta estacion para registrar descuentos."
    )

    _open_cash_session(client)
    unsupported_method_response = client.post(
        "/v1/discounts",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "subject_name": "Registro mixto",
            "concept": "Prueba de metodo no disponible",
            "payment_method_code": "MIXED",
            "total_amount": "10.00",
        },
    )
    assert unsupported_method_response.status_code == 400
    assert "efectivo o tarjeta" in unsupported_method_response.json()["detail"]

    high_value_response = client.post(
        "/v1/discounts",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "subject_name": "Empleado Rosa",
            "concept": "Descuento extraordinario",
            "category_code": _get_category_code("OTHER"),
            "payment_method_code": "CARD",
            "total_amount": "250.00",
        },
    )
    assert high_value_response.status_code == 400
    assert "alto valor" in high_value_response.json()["detail"]


def test_discounts_list_supports_scope_and_operator_filters_and_high_value_alerts(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    headers = {
        **_authorization_header(client),
        "X-Request-ID": "discounts-high-value",
    }

    create_response = client.post(
        "/v1/discounts",
        headers=headers,
        json={
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

    high_value_response = client.post(
        "/v1/discounts",
        headers=headers,
        json={
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

    assert audit_record.metadata["high_value"] is True
    assert audit_record.metadata["high_value_acknowledged"] is True
    assert alert_audit_record.metadata["notification_target"] == "backoffice"
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
