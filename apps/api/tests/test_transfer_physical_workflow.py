from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_inventory_core import _run
from test_transfer_idempotency import _created, _send, _state

from zeromerma_api.bootstrap.seed_local import (
    SEED_DESTINATION_WORKSTATION_CODE,
    SEED_PRODUCT_BOLILLO_STD_CODE,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Workstation
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.identity.infrastructure.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRoleAssignment,
)
from zeromerma_api.modules.inventory.application import lots as inventory_lots
from zeromerma_api.modules.inventory.application.mutations import (
    InventoryBalanceKey,
    create_inventory_lot,
)
from zeromerma_api.modules.inventory.infrastructure.lot_models import (
    InventoryLotBalance,
)
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
)
from zeromerma_api.modules.operations.infrastructure.models import OperationDocument
from zeromerma_api.modules.transfers.infrastructure.models import TransferTransitResolution
from zeromerma_api.testing.authorization import TEST_OWNER_EMAIL
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.sessions import login_headers
from zeromerma_api.testing.transfer_operators import transfer_cashier_email


def _pos(client: TestClient, station: str) -> tuple[dict[str, str], dict[str, Any]]:
    email = transfer_cashier_email(station)
    with SessionLocal() as session:
        user = session.scalars(select(User).where(User.email == email)).one()
        role = session.scalar(select(Role).where(Role.code == "transfer_resolution_acceptance"))
        if role is None:
            role = Role(
                code="transfer_resolution_acceptance",
                name="Transfer physical acceptance",
                surfaces=["POS"],
            )
            session.add(role)
            session.flush()
            session.add_all(
                RolePermission(role_id=role.id, permission_id=permission_id)
                for permission_id in session.scalars(
                    select(Permission.id).where(
                        Permission.code.in_(["transfers.cancel", "waste.manage"])
                    )
                )
            )
        if (
            session.scalar(
                select(UserRoleAssignment.id).where(
                    UserRoleAssignment.user_id == user.id, UserRoleAssignment.role_id == role.id
                )
            )
            is None
        ):
            session.add(UserRoleAssignment(user_id=user.id, role_id=role.id, scope_type="GLOBAL"))
        session.commit()
    headers = login_headers(
        client,
        email=email,
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=station,
    )
    opened = client.post(
        "/v1/cash-sessions/open",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={"workstation_code": station, "opening_amount": "0"},
    )
    assert opened.status_code == 201, opened.text
    return headers, {"workstation_code": station, "cash_session_id": opened.json()["id"]}


def _balance(branch: str, product: str, location: str) -> tuple[Decimal, Decimal | None]:
    with SessionLocal() as session:
        row = session.scalar(
            select(InventoryBalance).where(
                InventoryBalance.branch_id == UUID(branch),
                InventoryBalance.product_id == UUID(product),
                InventoryBalance.location_code == location,
            )
        )
        assert row is not None
        return row.quantity_on_hand, row.inventory_value


@pytest.mark.parametrize("kind", ["RETURN_TO_ORIGIN", "SEND_TO_WASTE"])
def test_partial_receipt_and_transit_resolution_preserve_cost_and_replay(
    client: TestClient,
    kind: str,
) -> None:
    headers, create, shipment = _created(client)
    product = create["lines"][0]["product_id"]
    with SessionLocal() as session:
        balance = session.scalars(select(InventoryBalance)).one()
        balance.inventory_value = Decimal("100.00000000")
        session.commit()
    assert _send(client, headers, "dispatch", {}, transfer_id=shipment["id"]).status_code == 200
    line = shipment["lines"][0]["shipment_line_id"]
    partial = _send(
        client,
        headers,
        "receive",
        {
            "lines": [
                {
                    "shipment_line_id": line,
                    "received_quantity": "2",
                    "variance_reason": "Partial arrival",
                }
            ]
        },
        transfer_id=shipment["id"],
    )
    assert partial.status_code == 200, partial.text
    with SessionLocal() as session:
        current = session.get(Product, UUID(product))
        assert current is not None
        current.standard_cost = Decimal("99.0000")
        session.commit()
    payload = {
        "kind": kind,
        "destination_location": "BACKROOM",
        "reason": "Physical return confirmed"
        if kind == "RETURN_TO_ORIGIN"
        else "Damaged in transit",
        "lines": [{"shipment_line_id": line, "quantity": "3"}],
    }
    key = new_idempotency_key()
    result = _send(client, headers, "resolve", payload, transfer_id=shipment["id"], key=key)
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "RECEIVED_WITH_VARIANCE"
    assert Decimal(result.json()["lines"][0]["pending_quantity"]) == 0
    assert _balance(create["destination_branch_id"], product, "IN_TRANSIT") == (0, 0)
    assert _balance(create["destination_branch_id"], product, "BACKROOM") == (2, 2)
    if kind == "RETURN_TO_ORIGIN":
        assert _balance(create["origin_branch_id"], product, "BACKROOM") == (98, 98)
    else:
        assert _balance(create["destination_branch_id"], product, "WASTE") == (3, 3)
    before = _state()
    replay = _send(client, headers, "resolve", payload, transfer_id=shipment["id"], key=key)
    assert replay.status_code == 200 and replay.json() == result.json(), replay.text
    code = "resolve_return" if kind == "RETURN_TO_ORIGIN" else "resolve_waste"
    recovered = client.get(
        f"/v1/admin/transfers/commands/{code}/confirmations/{key}",
        headers=headers,
        params={"branch_id": create["origin_branch_id"]},
    )
    assert recovered.status_code == 200 and recovered.json() == result.json(), recovered.text
    assert _state() == before
    detail = client.get(f"/v1/admin/transfers/{shipment['id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert len(detail.json()["resolutions"]) == 1
    assert Decimal(detail.json()["lines"][0]["pending_quantity"]) == 0
    assert len(detail.json()["inventory_impact"]["movements"]) == 6


def test_pos_dispatch_admin_receive_and_pos_physical_return_share_inventory(
    client: TestClient,
) -> None:
    admin, create, _ = _created(client)
    pos, context = _pos(client, SEED_WORKSTATION_CODE)
    dispatched = client.post(
        "/v1/transfers/dispatch/commit",
        headers={**pos, "Idempotency-Key": new_idempotency_key()},
        json={
            **context,
            "destination_branch_id": create["destination_branch_id"],
            "lines": create["lines"],
        },
    )
    assert dispatched.status_code == 201, dispatched.text
    shipment = dispatched.json()
    product = create["lines"][0]["product_id"]
    assert _balance(create["origin_branch_id"], product, "BACKROOM")[0] == 95
    assert _balance(create["destination_branch_id"], product, "IN_TRANSIT")[0] == 5
    received = _send(
        client,
        admin,
        "receive",
        {
            "lines": [
                {
                    "shipment_line_id": shipment["lines"][0]["shipment_line_id"],
                    "received_quantity": "2",
                    "variance_reason": "Rejected remainder returning",
                }
            ]
        },
        transfer_id=shipment["id"],
    )
    assert received.status_code == 200, received.text
    result = client.post(
        f"/v1/transfers/{shipment['id']}/resolve",
        headers={**pos, "Idempotency-Key": new_idempotency_key()},
        json={
            **context,
            "kind": "RETURN_TO_ORIGIN",
            "destination_location": "BACKROOM",
            "reason": "Returned at origin",
            "lines": [
                {"shipment_line_id": shipment["lines"][0]["shipment_line_id"], "quantity": "3"}
            ],
        },
    )
    assert result.status_code == 200, result.text
    assert _balance(create["origin_branch_id"], product, "BACKROOM")[0] == 98
    assert _balance(create["destination_branch_id"], product, "BACKROOM")[0] == 2
    assert _balance(create["destination_branch_id"], product, "IN_TRANSIT")[0] == 0


@pytest.mark.parametrize("waste_quantity", ["5", "2"])
def test_pos_destination_completion_preserves_origin_identity_and_actual_cause(
    client: TestClient, waste_quantity: str
) -> None:
    _, create, _ = _created(client)
    origin_headers, origin_context = _pos(client, SEED_WORKSTATION_CODE)
    dispatch = client.post(
        "/v1/transfers/dispatch/commit",
        headers={**origin_headers, "Idempotency-Key": new_idempotency_key()},
        json={
            **origin_context,
            "destination_branch_id": create["destination_branch_id"],
            "lines": create["lines"],
        },
    )
    assert dispatch.status_code == 201, dispatch.text
    shipment = dispatch.json()
    shipment_id = UUID(shipment["id"])
    line_id = shipment["lines"][0]["shipment_line_id"]
    with SessionLocal() as session:
        source = session.get(OperationDocument, shipment_id)
        assert source is not None
        identity = (source.source_branch_id, source.workstation_id, source.created_by_user_id)
    destination_headers, destination_context = _pos(client, SEED_DESTINATION_WORKSTATION_CODE)
    payload = {
        **destination_context,
        "kind": "SEND_TO_WASTE",
        "reason": "Physically damaged goods at destination",
        "lines": [{"shipment_line_id": line_id, "quantity": waste_quantity}],
    }
    before = _state()
    forbidden = client.post(
        f"/v1/transfers/{shipment_id}/resolve",
        headers={**destination_headers, "Idempotency-Key": new_idempotency_key()},
        json={**payload, "workstation_code": SEED_WORKSTATION_CODE},
    )
    assert forbidden.status_code == 403, forbidden.text
    assert _state() == (before[0], before[1], before[2] + 1, before[3], before[4])
    with SessionLocal() as session:
        denial = session.scalars(
            select(AuditLog).where(AuditLog.action == "authorization.denied")
        ).one()
        assert denial.resource_id == "POST /v1/transfers/{transfer_id}/resolve"
        assert denial.branch_id == UUID(create["destination_branch_id"])
        assert denial.cash_session_id == UUID(destination_context["cash_session_id"])
        assert session.scalar(select(func.count()).select_from(TransferTransitResolution)) == 0
    resolved = client.post(
        f"/v1/transfers/{shipment_id}/resolve",
        headers={**destination_headers, "Idempotency-Key": new_idempotency_key()},
        json=payload,
    )
    assert resolved.status_code == 200, resolved.text
    remaining = Decimal(5) - Decimal(waste_quantity)
    if remaining:
        assert resolved.json()["status"] == "IN_TRANSIT"
        received = client.post(
            f"/v1/transfers/{shipment_id}/receive",
            headers={**destination_headers, "Idempotency-Key": new_idempotency_key()},
            json={
                **destination_context,
                "lines": [
                    {
                        "shipment_line_id": line_id,
                        "expected_quantity": str(remaining),
                        "received_quantity": str(remaining),
                    }
                ],
            },
        )
        assert received.status_code == 200, received.text
        final = received.json()
    else:
        final = resolved.json()
    assert final["status"] == "RECEIVED_WITH_VARIANCE"
    assert Decimal(final["lines"][0]["pending_quantity"]) == 0
    assert Decimal(final["lines"][0]["waste_quantity"]) == Decimal(waste_quantity)
    assert Decimal(final["lines"][0]["received_quantity"]) == remaining
    product = create["lines"][0]["product_id"]
    assert _balance(create["destination_branch_id"], product, "IN_TRANSIT")[0] == 0
    assert _balance(create["destination_branch_id"], product, "WASTE")[0] == Decimal(waste_quantity)
    with SessionLocal() as session:
        source = session.get(OperationDocument, shipment_id)
        assert source is not None
        assert (
            source.source_branch_id,
            source.workstation_id,
            source.created_by_user_id,
        ) == identity
        resolution = session.scalars(select(TransferTransitResolution)).one()
        assert resolution.cash_session_id == UUID(destination_context["cash_session_id"])
        assert resolution.branch_id == UUID(create["destination_branch_id"])
        if remaining:
            receipt = session.scalars(
                select(OperationDocument).where(
                    OperationDocument.reference_document_id == shipment_id,
                    OperationDocument.document_type == "BRANCH_TRANSFER_RECEIPT",
                )
            ).one()
            assert receipt.status == "RECEIVED"
            assert receipt.workstation_id == resolution.workstation_id


def test_pos_full_return_from_another_origin_station_preserves_dispatch_identity(
    client: TestClient,
) -> None:
    _, create, _ = _created(client)
    origin_headers, origin_context = _pos(client, SEED_WORKSTATION_CODE)
    dispatch = client.post(
        "/v1/transfers/dispatch/commit",
        headers={**origin_headers, "Idempotency-Key": new_idempotency_key()},
        json={
            **origin_context,
            "destination_branch_id": create["destination_branch_id"],
            "lines": create["lines"],
        },
    )
    assert dispatch.status_code == 201, dispatch.text
    shipment = dispatch.json()
    shipment_id = UUID(shipment["id"])
    with SessionLocal() as session:
        source = session.get(OperationDocument, shipment_id)
        assert source is not None
        identity = (source.source_branch_id, source.workstation_id, source.created_by_user_id)
        alternate = Workstation(
            code="RETURN-ORIGIN-POS",
            name="Origin return register",
            branch_id=source.source_branch_id,
        )
        session.add(alternate)
        session.commit()
        alternate_id = alternate.id
    headers, context = _pos(client, "RETURN-ORIGIN-POS")
    key = new_idempotency_key()
    returned = client.post(
        f"/v1/transfers/{shipment_id}/resolve",
        headers={**headers, "Idempotency-Key": key},
        json={
            **context,
            "kind": "RETURN_TO_ORIGIN",
            "destination_location": "QUARANTINE",
            "reason": "Actual full return received by another origin register",
            "lines": [
                {"shipment_line_id": shipment["lines"][0]["shipment_line_id"], "quantity": "5"}
            ],
        },
    )
    assert returned.status_code == 200, returned.text
    assert returned.json()["status"] == "CANCELLED"
    assert Decimal(returned.json()["lines"][0]["pending_quantity"]) == 0
    product = create["lines"][0]["product_id"]
    assert _balance(create["destination_branch_id"], product, "IN_TRANSIT")[0] == 0
    assert _balance(create["origin_branch_id"], product, "QUARANTINE")[0] == 5
    with SessionLocal() as session:
        source = session.get(OperationDocument, shipment_id)
        assert source is not None
        assert (
            source.source_branch_id,
            source.workstation_id,
            source.created_by_user_id,
        ) == identity
        resolution = session.scalars(select(TransferTransitResolution)).one()
        assert resolution.workstation_id == alternate_id != identity[1]
        assert resolution.cash_session_id == UUID(context["cash_session_id"])
    before = _state()
    recovered = client.get(
        f"/v1/transfers/commands/resolve_return/confirmations/{key}",
        headers=headers,
        params=context,
    )
    assert recovered.status_code == 200, recovered.text
    assert recovered.json() == returned.json()
    assert _state() == before


def test_cancellation_requires_explicit_return_and_never_consumes_other_shipment_stock(
    client: TestClient,
) -> None:
    headers, create, shipment = _created(client)
    assert _send(client, headers, "dispatch", {}, transfer_id=shipment["id"]).status_code == 200
    before = _state()
    denied = _send(
        client, headers, "cancel", {"reason": "Cancel after dispatch"}, transfer_id=shipment["id"]
    )
    assert denied.status_code == 400 and _state() == before
    line = shipment["lines"][0]["shipment_line_id"]
    excess = _send(
        client,
        headers,
        "resolve",
        {
            "kind": "RETURN_TO_ORIGIN",
            "destination_location": "BACKROOM",
            "reason": "Over claim",
            "lines": [{"shipment_line_id": line, "quantity": "6"}],
        },
        transfer_id=shipment["id"],
    )
    assert excess.status_code == 400 and _state() == before
    returned = _send(
        client,
        headers,
        "resolve",
        {
            "kind": "RETURN_TO_ORIGIN",
            "destination_location": "BACKROOM",
            "reason": "Physical arrival at origin",
            "lines": [{"shipment_line_id": line, "quantity": "5"}],
        },
        transfer_id=shipment["id"],
    )
    assert returned.status_code == 200 and returned.json()["status"] == "CANCELLED", returned.text
    assert (
        _balance(create["origin_branch_id"], create["lines"][0]["product_id"], "BACKROOM")[0] == 100
    )


def test_pos_resolution_requires_actual_physical_branch_and_rolls_back_on_failure(
    client: TestClient,
) -> None:
    headers, _, shipment = _created(client)
    assert _send(client, headers, "dispatch", {}, transfer_id=shipment["id"]).status_code == 200
    pos, context = _pos(client, SEED_DESTINATION_WORKSTATION_CODE)
    before = _state()
    response = client.post(
        f"/v1/transfers/{shipment['id']}/resolve",
        headers={**pos, "Idempotency-Key": new_idempotency_key()},
        json={
            **context,
            "kind": "RETURN_TO_ORIGIN",
            "destination_location": "BACKROOM",
            "reason": "Not actually at origin",
            "lines": [
                {"shipment_line_id": shipment["lines"][0]["shipment_line_id"], "quantity": "5"}
            ],
        },
    )
    assert response.status_code == 400 and _state() == before, response.text
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(TransferTransitResolution)) == 0


def test_documentary_shipment_cannot_consume_another_shipments_transit(client: TestClient) -> None:
    headers, create, shipment = _created(client)
    assert _send(client, headers, "dispatch", {}, transfer_id=shipment["id"]).status_code == 200
    legacy = _send(client, headers, "create", create).json()
    with SessionLocal() as session:
        document = session.get(OperationDocument, UUID(legacy["id"]))
        assert document is not None
        document.status = "IN_TRANSIT"
        session.commit()
    before = _state()
    response = _send(
        client,
        headers,
        "receive",
        {
            "lines": [
                {
                    "shipment_line_id": legacy["lines"][0]["shipment_line_id"],
                    "received_quantity": "5",
                }
            ]
        },
        transfer_id=legacy["id"],
    )
    assert response.status_code == 400 and _state() == before, response.text
    assert (
        _balance(create["destination_branch_id"], create["lines"][0]["product_id"], "IN_TRANSIT")[0]
        == 5
    )


def test_rounding_remainder_is_carried_by_last_partial_receipt(client: TestClient) -> None:
    headers, _, shipment = _created(client)
    with SessionLocal() as session:
        balance = session.scalars(select(InventoryBalance)).one()
        balance.quantity_on_hand = Decimal("5")
        balance.inventory_value = Decimal("1.00000001")
        session.commit()
    assert _send(client, headers, "dispatch", {}, transfer_id=shipment["id"]).status_code == 200
    for amount in ("1", "1", "3"):
        response = _send(
            client,
            headers,
            "receive",
            {
                "lines": [
                    {
                        "shipment_line_id": shipment["lines"][0]["shipment_line_id"],
                        "received_quantity": amount,
                        "variance_reason": "Partial delivery",
                    }
                ]
            },
            transfer_id=shipment["id"],
        )
        assert response.status_code == 200, response.text
    with SessionLocal() as session:
        total = session.scalar(
            select(func.sum(InventoryMovement.total_cost)).where(
                InventoryMovement.movement_type == "TRANSFER_RECEIPT",
                InventoryMovement.direction == "IN",
            )
        )
        assert total == Decimal("1.00000001")


def _tracked_shipment(
    client: TestClient,
) -> tuple[dict[str, str], dict[str, Any], dict[str, Any], list[str]]:
    with SessionLocal() as session:
        product = session.scalar(
            select(Product).where(Product.code == SEED_PRODUCT_BOLILLO_STD_CODE)
        )
        assert product is not None
        product.lot_tracking_enabled = True
        product.expiry_required = True
        session.commit()
    headers, create, shipment = _created(client)
    with SessionLocal() as session:
        owner = session.scalars(select(User).where(User.email == TEST_OWNER_EMAIL)).one()
        actor = owner.id
    product_id = UUID(create["lines"][0]["product_id"])
    key = InventoryBalanceKey(UUID(create["origin_branch_id"]), product_id, "BACKROOM")

    def create_lots(session: Session) -> list[UUID]:
        return [
            create_inventory_lot(
                session,
                product_id=product_id,
                lot_code=f"TRANSFER-LOT-{index}",
                expires_at=datetime.now(UTC) + timedelta(days=index + 2),
                source_document_type="SYNTHETIC_ACCEPTANCE",
                source_document_id=UUID(shipment["id"]),
                source_line_id=None,
                branch_id=key.branch_id,
                operator_user_id=actor,
            ).id
            for index in range(2)
        ]

    identifiers = _run(key, actor, create_lots).payload["ids"]
    with SessionLocal() as session:
        for lot_id, quantity in zip(identifiers, ("2", "98"), strict=True):
            session.add(
                InventoryLotBalance(
                    branch_id=key.branch_id,
                    product_id=product_id,
                    location_code="BACKROOM",
                    lot_id=UUID(lot_id),
                    quantity_on_hand=Decimal(quantity),
                )
            )
        session.commit()
    return headers, create, shipment, identifiers


def test_fefo_dispatch_partial_receipt_requires_actual_shipped_lot(client: TestClient) -> None:
    headers, create, shipment, lot_ids = _tracked_shipment(client)
    dispatched = _send(client, headers, "dispatch", {}, transfer_id=shipment["id"])
    assert dispatched.status_code == 200, dispatched.text
    by_lot = {item["lot_id"]: item for item in dispatched.json()["lines"][0]["lots"]}
    assert {key: Decimal(value["sent_quantity"]) for key, value in by_lot.items()} == {
        lot_ids[0]: 2,
        lot_ids[1]: 3,
    }
    body = {
        "lines": [
            {
                "shipment_line_id": shipment["lines"][0]["shipment_line_id"],
                "received_quantity": "1",
                "variance_reason": "Only later lot arrived",
            }
        ]
    }
    before = _state()
    rejected = _send(client, headers, "receive", body, transfer_id=shipment["id"])
    assert rejected.status_code == 400 and _state() == before, rejected.text
    body["lines"][0]["lot_allocations"] = [{"lot_id": lot_ids[1], "quantity": "1"}]
    received = _send(client, headers, "receive", body, transfer_id=shipment["id"])
    assert received.status_code == 200, received.text
    remaining = {
        item["lot_id"]: Decimal(item["pending_quantity"])
        for item in received.json()["lines"][0]["lots"]
    }
    assert remaining == {lot_ids[0]: 2, lot_ids[1]: 2}
    with SessionLocal() as session:
        rows = list(
            session.scalars(
                select(InventoryLotBalance).where(
                    InventoryLotBalance.branch_id == UUID(create["destination_branch_id"]),
                    InventoryLotBalance.location_code == "BACKROOM",
                )
            )
        )
        assert [
            (str(row.lot_id), row.quantity_on_hand) for row in rows if row.quantity_on_hand > 0
        ] == [(lot_ids[1], 1)]


def test_expired_transit_returns_to_quarantine_with_original_lot_identity(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, create, shipment, lot_ids = _tracked_shipment(client)
    dispatched = _send(client, headers, "dispatch", {}, transfer_id=shipment["id"])
    assert dispatched.status_code == 200, dispatched.text
    original = {
        item["lot_id"]: item["expires_at"] for item in dispatched.json()["lines"][0]["lots"]
    }

    class FutureClock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            return datetime.now(UTC) + timedelta(days=5)

    monkeypatch.setattr(inventory_lots, "datetime", FutureClock)
    body = {
        "kind": "RETURN_TO_ORIGIN",
        "destination_location": "BACKROOM",
        "reason": "Expired in transit",
        "lines": [{"shipment_line_id": shipment["lines"][0]["shipment_line_id"], "quantity": "5"}],
    }
    before = _state()
    denied = _send(client, headers, "resolve", body, transfer_id=shipment["id"])
    assert denied.status_code == 400 and _state() == before, denied.text
    body["destination_location"] = "QUARANTINE"
    returned = _send(client, headers, "resolve", body, transfer_id=shipment["id"])
    assert returned.status_code == 200, returned.text
    assert {
        item["lot_id"]: item["expires_at"] for item in returned.json()["lines"][0]["lots"]
    } == original
    assert (
        _balance(create["origin_branch_id"], create["lines"][0]["product_id"], "QUARANTINE")[0] == 5
    )
    detail = client.get(f"/v1/admin/transfers/{shipment['id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    resolution = detail.json()["resolutions"][0]
    assert resolution["destination_location"] == "QUARANTINE"
    assert {item["lot_id"] for item in resolution["lines"][0]["lots"]} == set(lot_ids)
