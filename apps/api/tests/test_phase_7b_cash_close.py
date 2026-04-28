from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_PRODUCT_BOLILLO_STD_CODE,
    SEED_PRODUCT_CLASS_BOLILLO_CODE,
    SEED_PRODUCT_CLASS_PAN_DULCE_CODE,
    SEED_PRODUCT_COCA_355_CODE,
    SEED_PRODUCT_CONCHA_CHOCO_CODE,
    SEED_PRODUCT_CONCHA_VAN_CODE,
    SEED_PRODUCT_CUERNO_MANTEQUILLA_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.cash.domain.constants import CASH_SESSION_STATUS_CLOSED
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.cash_close.infrastructure.models import (
    BranchCounterSnapshot,
    BranchCounterSnapshotLine,
    CashSessionClose,
)
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.sales.infrastructure.models import SaleLine


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
            "opening_amount": "150.00",
        },
    )
    assert response.status_code == 201


def _get_product_id(code: str) -> str:
    with SessionLocal() as session:
        product = session.execute(select(Product).where(Product.code == code)).scalar_one()
    return str(product.id)


def _get_product_class_id(code: str) -> str:
    with SessionLocal() as session:
        product_class = session.execute(
            select(ProductClass).where(ProductClass.code == code)
        ).scalar_one()
    return str(product_class.id)


def _seed_counter_baseline(lines: list[tuple[str, str]]) -> None:
    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == "MAIN")).scalar_one()
        user = session.execute(select(User).where(User.email == SEED_USER_EMAIL)).scalar_one()
        snapshot = BranchCounterSnapshot(
            branch_id=branch.id,
            source_cash_session_close_id=None,
            snapshot_type="CLOSE_BASELINE",
            captured_by_user_id=user.id,
        )
        session.add(snapshot)
        session.flush()

        for product_code, quantity in lines:
            product = session.execute(
                select(Product).where(Product.code == product_code)
            ).scalar_one()
            product_class = session.execute(
                select(ProductClass).where(ProductClass.id == product.product_class_id)
            ).scalar_one()
            session.add(
                BranchCounterSnapshotLine(
                    snapshot_id=snapshot.id,
                    product_id=product.id,
                    product_code_snapshot=product.code,
                    product_name_snapshot=product.name,
                    product_class_id=product_class.id,
                    product_class_code_snapshot=product_class.code,
                    product_class_name_snapshot=product_class.name,
                    quantity=Decimal(quantity),
                    bucket_code="COUNTER",
                )
            )
        session.commit()


def _confirm_sale(
    client: TestClient,
    *,
    lines: list[dict[str, str]],
    tendered_amount: str,
) -> None:
    response = client.post(
        "/v1/sales/confirm",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "lines": lines,
            "payments": [
                {
                    "payment_method_code": "CASH",
                    "tendered_amount": tendered_amount,
                }
            ],
        },
    )
    assert response.status_code == 201


def test_cash_close_reconciliation_endpoint_and_preview_auto_resolve(client: TestClient) -> None:
    _seed_counter_baseline(
        [
            (SEED_PRODUCT_BOLILLO_STD_CODE, "10.000"),
            (SEED_PRODUCT_COCA_355_CODE, "4.000"),
        ]
    )
    _open_cash_session(client)
    _confirm_sale(
        client,
        lines=[
            {
                "capture_mode": "CLASS_CAPTURE",
                "product_class_id": _get_product_class_id(SEED_PRODUCT_CLASS_BOLILLO_CODE),
                "quantity": "2",
            }
        ],
        tendered_amount="10.00",
    )
    _confirm_sale(
        client,
        lines=[
            {
                "capture_mode": "PRODUCT_DIRECT",
                "product_id": _get_product_id(SEED_PRODUCT_COCA_355_CODE),
                "quantity": "1",
            }
        ],
        tendered_amount="20.00",
    )

    reconciliation = client.get(
        f"/v1/cash-close/reconciliation?workstation_code={SEED_WORKSTATION_CODE}",
        headers=_authorization_header(client),
    )
    assert reconciliation.status_code == 200
    reconciliation_payload = reconciliation.json()
    assert reconciliation_payload["class_reconciliations"] == [
        {
            "product_class_id": _get_product_class_id(SEED_PRODUCT_CLASS_BOLILLO_CODE),
            "product_class_code": "BOLILLO",
            "product_class_name": "Bolillo",
            "pending_quantity": "2.000",
            "auto_attributed_quantity": "0.000",
            "final_attributed_quantity": "0.000",
            "discrepancy_quantity": "2.000",
            "resolution_status": "COUNT_REQUIRED",
            "attribution_lines": [],
            "notes": None,
        }
    ]

    preview = client.post(
        "/v1/cash-close/preview",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "counted_payment_methods": [
                {"payment_method_code": "CASH", "counted_amount": "174.00"},
            ],
            "counted_product_lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "counted_quantity": "8",
                },
                {
                    "product_id": _get_product_id(SEED_PRODUCT_COCA_355_CODE),
                    "counted_quantity": "3",
                },
            ],
        },
    )

    assert preview.status_code == 200
    payload = preview.json()
    assert payload["reconciliation_status"] == "READY"
    assert payload["blockers"] == []
    assert payload["class_reconciliations"][0]["resolution_status"] == "AUTO_RESOLVED"
    assert payload["class_reconciliations"][0]["auto_attributed_quantity"] == "2.000"
    assert payload["discrepancy_resolutions"] == []


def test_cash_close_commit_blocks_unresolved_class_capture_mismatch(
    client: TestClient,
) -> None:
    _seed_counter_baseline([(SEED_PRODUCT_BOLILLO_STD_CODE, "10.000")])
    _open_cash_session(client)
    _confirm_sale(
        client,
        lines=[
            {
                "capture_mode": "CLASS_CAPTURE",
                "product_class_id": _get_product_class_id(SEED_PRODUCT_CLASS_BOLILLO_CODE),
                "quantity": "2",
            }
        ],
        tendered_amount="10.00",
    )

    response = client.post(
        "/v1/cash-close/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "counted_payment_methods": [
                {"payment_method_code": "CASH", "counted_amount": "156.00"},
            ],
            "counted_product_lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "counted_quantity": "9",
                },
            ],
        },
    )

    assert response.status_code == 400
    assert "ventas por clase" in response.json()["detail"]


def test_cash_close_commit_with_manual_override_and_auto_discrepancy_resolution(
    client: TestClient,
) -> None:
    _seed_counter_baseline(
        [
            (SEED_PRODUCT_CONCHA_VAN_CODE, "4.000"),
            (SEED_PRODUCT_CONCHA_CHOCO_CODE, "4.000"),
        ]
    )
    _open_cash_session(client)
    _confirm_sale(
        client,
        lines=[
            {
                "capture_mode": "CLASS_CAPTURE",
                "product_class_id": _get_product_class_id(SEED_PRODUCT_CLASS_PAN_DULCE_CODE),
                "quantity": "2",
            }
        ],
        tendered_amount="50.00",
    )

    response = client.post(
        "/v1/cash-close/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "counted_payment_methods": [
                {"payment_method_code": "CASH", "counted_amount": "174.00"},
            ],
            "counted_product_lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE),
                    "counted_quantity": "3",
                },
                {
                    "product_id": _get_product_id(SEED_PRODUCT_CONCHA_CHOCO_CODE),
                    "counted_quantity": "4",
                },
                {
                    "product_id": _get_product_id(SEED_PRODUCT_CUERNO_MANTEQUILLA_CODE),
                    "counted_quantity": "0",
                },
            ],
            "manual_reconciliation_overrides": [
                {
                    "product_class_id": _get_product_class_id(SEED_PRODUCT_CLASS_PAN_DULCE_CODE),
                    "attribution_lines": [
                        {
                            "product_id": _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE),
                            "attributed_quantity": "2",
                        }
                    ],
                    "notes": "Operator resolved pan dulce attribution.",
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["cash_session"]["status"] == "CLOSED"
    assert payload["class_reconciliations"][0]["resolution_status"] == "MANUAL_RESOLVED"
    assert (
        payload["generated_discrepancy_documents"][0]["document_type"]
        == "CLOSE_COUNTER_ADJUSTMENT"
    )

    detail = client.get(
        f"/v1/cash-close/{payload['id']}",
        headers=_authorization_header(client),
    )
    assert detail.status_code == 200
    assert detail.json()["id"] == payload["id"]

    with SessionLocal() as session:
        cash_session = session.execute(select(CashSession)).scalar_one()
        close_rows = session.execute(select(CashSessionClose)).scalars().all()
        sale_lines = session.execute(select(SaleLine)).scalars().all()
        event_names = session.execute(select(OutboxEvent.event_name)).scalars().all()

    assert cash_session.status == CASH_SESSION_STATUS_CLOSED
    assert cash_session.closed_at is not None
    assert len(close_rows) == 1
    assert all(line.physical_attribution_status == "RECONCILED" for line in sale_lines)
    assert "cash_session.closed.v1" in event_names
    assert "class_capture.reconciled.v1" in event_names
    assert "close_discrepancy.generated.v1" in event_names
