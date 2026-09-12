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
from zeromerma_api.modules.identity.infrastructure.models import User, UserBranchAssignment
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.payments.infrastructure.models import (
    OperationalPayment,
    OperationalPaymentCategory,
)
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
            select(OperationalPaymentCategory).where(OperationalPaymentCategory.code == code)
        ).scalar_one()
    return category.code


def test_payments_bootstrap_list_detail_and_cash_commit_work_end_to_end(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    headers = {
        **_authorization_header(client),
        "X-Request-ID": "payments-cash-commit",
    }

    bootstrap_response = client.get(
        "/v1/payments/bootstrap",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=headers,
    )

    assert bootstrap_response.status_code == 200
    bootstrap_payload = bootstrap_response.json()
    assert bootstrap_payload["payment_registration_allowed"] is True
    assert bootstrap_payload["default_scope"] == "CURRENT_SHIFT"
    assert [entry["code"] for entry in bootstrap_payload["available_scopes"]] == [
        "CURRENT_SHIFT",
        "TODAY",
        "RECENT",
    ]
    assert [entry["code"] for entry in bootstrap_payload["active_payment_methods"]] == [
        "CASH",
        "CARD",
        "MIXED",
    ]
    assert bootstrap_payload["active_payment_methods"][2]["is_enabled"] is False

    create_response = client.post(
        "/v1/payments",
        headers=headers,
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "payee_name": "Proveedor El Trigo",
            "concept": "Compra urgente de harina",
            "category_code": _get_category_code("SUPPLIER"),
            "payment_method_code": "CASH",
            "total_amount": "125.50",
            "notes": "Pago del turno",
        },
    )

    assert create_response.status_code == 201
    detail_payload = create_response.json()
    assert detail_payload["folio"].startswith("PAG-")
    assert detail_payload["payment_method_code"] == "CASH"
    assert Decimal(str(detail_payload["total_amount"])) == Decimal("125.50")
    assert Decimal(str(detail_payload["cash_amount"])) == Decimal("125.50")
    assert detail_payload["affects_cash_drawer"] is True

    list_response = client.get(
        "/v1/payments",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "query": "harina",
            "payment_method": "CASH",
        },
        headers=headers,
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert len(list_payload["payments"]) == 1
    assert list_payload["payments"][0]["id"] == detail_payload["id"]
    assert list_payload["payments"][0]["category_code"] == "SUPPLIER"
    assert list_payload["payments"][0]["branch_code"] == "MAIN"
    assert list_payload["payments"][0]["workstation_code"] == SEED_WORKSTATION_CODE

    reread_response = client.get(
        f"/v1/payments/{detail_payload['id']}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=headers,
    )
    assert reread_response.status_code == 200
    reread_payload = reread_response.json()
    assert reread_payload["id"] == detail_payload["id"]
    assert reread_payload["audit_summary"]["created_by"]["email"] == SEED_USER_EMAIL
    assert reread_payload["audit_summary"]["confirmed_by"]["full_name"] == "Main Branch Cashier"

    with SessionLocal() as session:
        payment_record = session.execute(
            select(OperationalPayment).where(OperationalPayment.id == detail_payload["id"])
        ).scalar_one()
        cash_movement = session.execute(
            select(CashMovement).where(
                CashMovement.movement_type == "OPERATIONAL_PAYMENT",
                CashMovement.sale_id.is_(None),
                CashMovement.amount == Decimal("125.50"),
            )
        ).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.action == "operational_payment.committed",
                AuditLog.resource_id == str(payment_record.id),
            )
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == str(payment_record.id),
                OutboxEvent.event_name == "operational_payment.committed.v1",
            )
        ).scalar_one()

    assert cash_movement.direction == "OUT"
    assert cash_movement.sale_id is None
    assert audit_record.request_id == "payments-cash-commit"
    assert outbox_event.payload["payment_method_code"] == "CASH"


def test_card_payment_does_not_reduce_drawer_cash_but_stays_visible_in_close_summary(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    headers = _authorization_header(client)

    card_response = client.post(
        "/v1/payments",
        headers=headers,
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "payee_name": "Mensajeria Norte",
            "concept": "Pago de logistica",
            "category_code": _get_category_code("LOGISTICS"),
            "payment_method_code": "CARD",
            "total_amount": "90.00",
        },
    )
    assert card_response.status_code == 201
    assert Decimal(str(card_response.json()["cash_amount"])) == Decimal("0.00")

    cash_response = client.post(
        "/v1/payments",
        headers=headers,
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "payee_name": "Gasolinera Centro",
            "concept": "Gas del reparto",
            "category_code": _get_category_code("GAS"),
            "payment_method_code": "CASH",
            "total_amount": "40.00",
        },
    )
    assert cash_response.status_code == 201

    with SessionLocal() as session:
        movement_rows = (
            session.execute(
                select(CashMovement)
                .where(CashMovement.movement_type == "OPERATIONAL_PAYMENT")
                .order_by(CashMovement.occurred_at.asc())
            )
            .scalars()
            .all()
        )

    assert len(movement_rows) == 1
    assert Decimal(str(movement_rows[0].amount)) == Decimal("40.00")

    close_summary_response = client.get(
        "/v1/cash-close/summary",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=headers,
    )
    assert close_summary_response.status_code == 200
    close_summary_payload = close_summary_response.json()
    assert Decimal(str(close_summary_payload["total_cash_out"])) == Decimal("40.00")


def test_payments_require_open_session_and_reject_unsupported_methods(
    client: TestClient,
) -> None:
    no_session_response = client.get(
        "/v1/payments",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_authorization_header(client),
    )
    assert no_session_response.status_code == 409
    assert (
        no_session_response.json()["message"]
        == "Necesitas una caja abierta en esta estacion para registrar pagos."
    )

    _open_cash_session(client)
    unsupported_method_response = client.post(
        "/v1/payments",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "payee_name": "Pago mixto",
            "concept": "Prueba de metodo no disponible",
            "payment_method_code": "MIXED",
            "total_amount": "10.00",
        },
    )
    assert unsupported_method_response.status_code == 400
    assert "efectivo o tarjeta" in unsupported_method_response.json()["message"]


def test_payments_list_supports_scope_and_operator_filters(client: TestClient) -> None:
    _open_cash_session(client)
    headers = _authorization_header(client)

    create_response = client.post(
        "/v1/payments",
        headers=headers,
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "payee_name": "Proveedor turno actual",
            "concept": "REF-TURNO",
            "category_code": _get_category_code("SUPPLIER"),
            "payment_method_code": "CASH",
            "total_amount": "80.00",
        },
    )
    assert create_response.status_code == 201

    bootstrap_response = client.get(
        "/v1/payments/bootstrap",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=headers,
    )
    assert bootstrap_response.status_code == 200
    current_user_id = str(bootstrap_response.json()["user"]["id"])

    with SessionLocal() as session:
        current_payment = session.execute(
            select(OperationalPayment).where(OperationalPayment.id == create_response.json()["id"])
        ).scalar_one()

        second_user = User(
            id=uuid.uuid4(),
            email="payments-operator@zeromerma.local",
            full_name="Second Payments Operator",
            password_hash="seed-password-hash",
            is_active=True,
        )
        session.add(second_user)
        session.flush()
        session.add(
            UserBranchAssignment(
                user_id=second_user.id,
                branch_id=current_payment.branch_id,
                is_active=True,
            )
        )
        historical_cash_session = CashSession(
            branch_id=current_payment.branch_id,
            workstation_id=current_payment.workstation_id,
            user_id=second_user.id,
            status=CASH_SESSION_STATUS_CLOSED,
            opening_amount=Decimal("150.00"),
            opened_at=datetime.now(tz=UTC) - timedelta(days=2, hours=2),
            closed_at=datetime.now(tz=UTC) - timedelta(days=2),
        )
        session.add(historical_cash_session)
        session.flush()
        session.add(
            OperationalPayment(
                branch_id=current_payment.branch_id,
                workstation_id=current_payment.workstation_id,
                created_by_user_id=second_user.id,
                active_cash_session_id=historical_cash_session.id,
                payee_name="Servicio historico",
                concept="REF-HISTORICO",
                category_code=_get_category_code("SERVICES"),
                notes="Pago de consulta historica",
                payment_method_code="CARD",
                currency_code="MXN",
                total_amount=Decimal("90.00"),
                cash_amount=Decimal("0.00"),
                non_cash_amount=Decimal("90.00"),
                status="COMMITTED",
                created_at_utc=datetime.now(tz=UTC) - timedelta(days=2),
                committed_at_utc=datetime.now(tz=UTC) - timedelta(days=2),
            )
        )
        session.commit()

    current_shift_response = client.get(
        "/v1/payments",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "scope": "CURRENT_SHIFT",
        },
        headers=headers,
    )
    assert current_shift_response.status_code == 200
    current_shift_payload = current_shift_response.json()
    assert current_shift_payload["scope"] == "CURRENT_SHIFT"
    assert len(current_shift_payload["payments"]) == 1
    assert current_shift_payload["payments"][0]["concept"] == "REF-TURNO"

    recent_response = client.get(
        "/v1/payments",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "scope": "RECENT",
        },
        headers=headers,
    )
    assert recent_response.status_code == 200
    recent_payload = recent_response.json()
    assert len(recent_payload["payments"]) == 2
    assert {entry["label"] for entry in recent_payload["available_users"]} == {
        "Main Branch Cashier",
        "Second Payments Operator",
    }

    operator_filter_response = client.get(
        "/v1/payments",
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
    assert len(operator_filter_payload["payments"]) == 1
    assert operator_filter_payload["payments"][0]["payee_name"] == "Servicio historico"

    today_response = client.get(
        "/v1/payments",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "scope": "TODAY",
            "created_by_user_id": current_user_id,
        },
        headers=headers,
    )
    assert today_response.status_code == 200
    today_payload = today_response.json()
    assert len(today_payload["payments"]) == 1
    assert today_payload["payments"][0]["folio"].startswith("PAG-")
