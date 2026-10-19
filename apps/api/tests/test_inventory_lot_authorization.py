"""Lots inherit the admitted branch command, never unrestricted master authority."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_operation_authorization import _actor, _headers

from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyBoundaryError
from zeromerma_api.modules.inventory.application.mutations import create_inventory_lot
from zeromerma_api.modules.inventory.infrastructure.lot_models import InventoryLot
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
)
from zeromerma_api.testing.idempotency import new_idempotency_key


def test_branch_adjuster_creates_lot_only_with_owner_in_authorized_branch(
    client: TestClient,
) -> None:
    with SessionLocal() as session:
        branches = list(session.scalars(select(Branch.id).order_by(Branch.code)))
        assert len(branches) >= 2
        product = session.scalars(select(Product).where(Product.is_inventory_tracked)).first()
        assert product is not None
        product.lot_tracking_enabled = True
        product.expiry_required = True
        product_id = product.id
        session.commit()
        actor = _actor(session, ("inventory.adjust", "inventory.view"), branches[:1])
    headers = _headers(actor)
    payload = {
        "branch_id": str(branches[0]),
        "product_id": str(product_id),
        "location_code": "BACKROOM",
        "adjustment_type": "INCREASE",
        "quantity": "4.000",
        "reason": "Documented physical lot count",
        "lot_code": "BRANCH-COUNT-001",
        "expires_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
    }
    admitted = client.post(
        "/v1/admin/inventory/adjustments",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json=payload,
    )
    assert admitted.status_code == 201, admitted.text
    denied = client.post(
        "/v1/admin/inventory/adjustments",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={**payload, "branch_id": str(branches[1]), "lot_code": "OUT-OF-SCOPE"},
    )
    assert denied.status_code == 403, denied.text
    with SessionLocal() as session:
        lot = session.scalars(select(InventoryLot)).one()
        movement = session.scalars(select(InventoryMovement)).one()
        assert movement.branch_id == branches[0] and movement.quantity == Decimal(4)
        assert lot.idempotency_record_id == movement.idempotency_record_id
        assert lot.operator_user_id == actor.id
        with pytest.raises(IdempotencyBoundaryError):
            create_inventory_lot(
                session,
                product_id=product_id,
                lot_code="NO-OWNER",
                expires_at=datetime.now(UTC) + timedelta(days=2),
                source_document_type="SYNTHETIC_UNADMITTED_COUNT",
                source_document_id=uuid4(),
                source_line_id=None,
                branch_id=branches[0],
                operator_user_id=actor.id,
            )


@pytest.mark.parametrize("adjustment_type,quantity", [("DECREASE", "1.000"), ("SET_COUNTED", "0")])
def test_expired_lot_physical_count_is_authorized_without_making_it_sellable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, adjustment_type: str, quantity: str
) -> None:
    from zeromerma_api.modules.inventory.application import lots as lot_module

    now = datetime.now(UTC)
    with SessionLocal() as session:
        branch_id = session.scalars(select(Branch.id)).first()
        product = session.scalars(select(Product).where(Product.is_inventory_tracked)).first()
        assert branch_id and product
        product.lot_tracking_enabled = True
        product.expiry_required = True
        product_id = product.id
        session.commit()
        actor = _actor(session, ("inventory.adjust", "inventory.view"), [branch_id])
    headers = _headers(actor)
    payload = {
        "branch_id": str(branch_id),
        "product_id": str(product_id),
        "location_code": "BACKROOM",
        "adjustment_type": "INCREASE",
        "quantity": "2.000",
        "reason": "Physical count evidence",
        "lot_code": "EXPIRING-COUNT",
        "expires_at": (now + timedelta(days=1)).isoformat(),
    }
    opening = client.post(
        "/v1/admin/inventory/adjustments",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json=payload,
    )
    assert opening.status_code == 201, opening.text
    with SessionLocal() as session:
        lot_id = session.scalars(select(InventoryLot.id)).one()

    class FutureDateTime(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:
            return now + timedelta(days=2)

    monkeypatch.setattr(lot_module, "datetime", FutureDateTime)
    count_payload = {
        key: value for key, value in payload.items() if key not in {"lot_code", "expires_at"}
    }
    corrected = client.post(
        "/v1/admin/inventory/adjustments",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={
            **count_payload,
            "lot_id": str(lot_id),
            "adjustment_type": adjustment_type,
            "quantity": quantity,
        },
    )
    assert corrected.status_code == 201, corrected.text
    forbidden_inbound = client.post(
        "/v1/admin/inventory/adjustments",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={**count_payload, "lot_id": str(lot_id), "quantity": "1.000"},
    )
    assert forbidden_inbound.status_code == 400
    with SessionLocal() as session:
        balance = session.scalars(select(InventoryBalance)).one()
        assert balance.quantity_on_hand == (Decimal(1) if adjustment_type == "DECREASE" else 0)
        assert len(list(session.scalars(select(InventoryMovement)))) == 2
