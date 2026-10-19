"""Ticket choices expose original-sale capacity and never authorize future stock."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from queue import Queue
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_inventory_concurrency import _command
from test_sale_physical_inventory import _sale, _setup

from zeromerma_api.bootstrap.seed_local import SEED_USER_EMAIL
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.inventory.application.class_inventory import (
    attribute_class_inventory,
    lock_class_obligations,
)
from zeromerma_api.modules.inventory.application.mutations import (
    InventoryBalanceKey,
    lock_inventory_balances,
)
from zeromerma_api.modules.inventory.infrastructure.attribution_models import (
    ClassInventoryAttribution,
    ClassInventoryObligation,
)
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
)
from zeromerma_api.modules.sales.infrastructure.models import SaleLine
from zeromerma_api.testing.concurrency import (
    TransactionProbe,
    transaction_probe,
    wait_until_blocked,
)
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.inventory import seed_test_inventory


@pytest.mark.parametrize("lots", [False, True])
def test_ticket_choices_exclude_later_receipts_and_follow_partial_attribution(
    client: TestClient, lots: bool
) -> None:
    headers, context = _setup(client, stock="2", lots=lots, class_sale=True)
    sale_response = _sale(client, headers, context, quantity="3", class_sale=True)
    assert sale_response.status_code == 201, sale_response.text
    sale = sale_response.json()
    sale_id = sale["id"]
    with SessionLocal() as session:
        actor = session.scalar(select(User.id).where(User.email == SEED_USER_EMAIL))
        assert actor
        seed_test_inventory(
            session,
            branch_id=UUID(context["branch_id"]),
            actor_user_id=actor,
            product_quantities={UUID(context["product_id"]): Decimal(100)},
            location_code="COUNTER",
            fixture_reference="receipt-after-class-sale",
        )
    detail_url = f"/v1/tickets/{sale_id}?workstation_code={context['workstation_code']}"
    detail = client.get(detail_url, headers=headers)
    assert detail.status_code == 200, detail.text
    line = detail.json()["lines"][0]
    assert line["capture_mode"] == "CLASS_CAPTURE"
    assert Decimal(line["remaining_attribution_quantity"]) == 3
    options = [o for o in line["attribution_options"] if o["product_id"] == context["product_id"]]
    assert len(options) == 1
    assert Decimal(options[0]["available_quantity"]) == 2
    assert options[0]["lot_tracking_enabled"] is lots
    assert line["physical_attributions"] == []
    request_key = new_idempotency_key()
    payload = {
        "workstation_code": context["workstation_code"],
        "cash_session_id": context["cash_session_id"],
        "lines": [
            {
                "sale_line_id": line["id"],
                "product_id": context["product_id"],
                "quantity": "1.000",
                "lot_id": options[0]["lot_id"],
            }
        ],
    }
    response = client.post(
        f"/v1/sales/{sale_id}/attribute-inventory",
        headers={**headers, "Idempotency-Key": request_key},
        json=payload,
    )
    assert response.status_code == 200, response.text
    replay = client.post(
        f"/v1/sales/{sale_id}/attribute-inventory",
        headers={**headers, "Idempotency-Key": request_key},
        json=payload,
    )
    assert replay.status_code == 200 and replay.json() == response.json()
    after = client.get(detail_url, headers=headers).json()["lines"][0]
    assert Decimal(after["remaining_attribution_quantity"]) == 2
    assert len(after["physical_attributions"]) == 1
    assert after["physical_attributions"][0]["id"] == response.json()["lines"][0]["attribution_id"]
    options_after = [
        o for o in after["attribution_options"] if o["product_id"] == context["product_id"]
    ]
    assert sum((Decimal(o["available_quantity"]) for o in options_after), Decimal(0)) == 1
    over = {**payload, "lines": [{**payload["lines"][0], "quantity": "2.000"}]}
    rejected = client.post(
        f"/v1/sales/{sale_id}/attribute-inventory",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json=over,
    )
    assert rejected.status_code == 409, rejected.text
    with SessionLocal() as session:
        physical = list(
            session.scalars(
                select(InventoryMovement).where(
                    InventoryMovement.movement_type == "SALE_CLASS_ATTRIBUTION"
                )
            )
        )
        assert len(physical) == 1 and physical[0].quantity == 1


def test_two_operators_serialize_one_class_obligation_across_different_product_balances(
    client: TestClient,
) -> None:
    headers, context = _setup(client, stock="10", class_sale=True)
    branch_id, product_id = UUID(context["branch_id"]), UUID(context["product_id"])
    with SessionLocal() as session:
        first_actor = session.scalars(select(User.id).where(User.email == SEED_USER_EMAIL)).one()
        second_actor = session.scalars(select(User.id).where(User.id != first_actor)).first()
        assert second_actor is not None
        alternate = session.scalars(
            select(Product).where(
                Product.product_class_id == UUID(context["product_class_id"]),
                Product.id != product_id,
                Product.is_inventory_tracked.is_(True),
            )
        ).first()
        assert alternate is not None
        alternate_id = alternate.id
        seed_test_inventory(
            session,
            branch_id=branch_id,
            actor_user_id=first_actor,
            product_quantities={alternate_id: Decimal(10)},
            location_code="COUNTER",
            fixture_reference="distinct-product-class-attribution-contention",
        )
    sale_response = _sale(client, headers, context, quantity="3", class_sale=True)
    assert sale_response.status_code == 201, sale_response.text
    sale_id = UUID(sale_response.json()["id"])
    with SessionLocal() as session:
        line_id = session.scalars(select(SaleLine.id).where(SaleLine.sale_id == sale_id)).one()
    keys = [
        InventoryBalanceKey(branch_id, value, "COUNTER") for value in (product_id, alternate_id)
    ]
    probes: Queue[TransactionProbe] = Queue()

    def attribute(current: Session, index: int, actor_id: UUID) -> None:
        balances = lock_inventory_balances(current, [keys[index]])
        if index:
            probes.put(transaction_probe(current))
        obligation = lock_class_obligations(current, [line_id])[line_id]
        product = current.get(Product, keys[index].product_id)
        assert product is not None
        attribute_class_inventory(
            current,
            balances=balances,
            obligation=obligation,
            product=product,
            quantity=Decimal(2),
            actor_id=actor_id,
            source_document_type="SALE_ATTRIBUTION",
            source_document_id=sale_id,
            causal_effect_code="concurrent-attribution",
        )
        current.flush()

    def second() -> None:
        with SessionLocal() as session:
            _command(
                session,
                [keys[1]],
                second_actor,
                lambda current: attribute(current, 1, second_actor),
            )

    with ThreadPoolExecutor(max_workers=1) as pool, SessionLocal() as session:
        pending = []

        def first(current: Session) -> None:
            first_probe = transaction_probe(current)
            attribute(current, 0, first_actor)
            pending.append(pool.submit(second))
            second_probe = probes.get(timeout=5)
            assert second_probe.transaction_id != first_probe.transaction_id
            wait_until_blocked(second_probe.backend_pid, first_probe.backend_pid)

        _command(session, [keys[0]], first_actor, first)
        with pytest.raises(HTTPException) as rejected:
            pending[0].result(timeout=10)
        assert rejected.value.status_code == 409
        assert rejected.value.detail["code"] == "CLASS_ATTRIBUTION_QUANTITY_EXCEEDED"

    with SessionLocal() as session:
        obligation = session.scalars(select(ClassInventoryObligation)).one()
        assert obligation.required_quantity == 3 and obligation.attributed_quantity == 2
        assert obligation.status == "OPEN"
        facts = session.scalars(select(ClassInventoryAttribution)).all()
        assert len(facts) == 1 and facts[0].actor_id == first_actor and facts[0].quantity == 2
        physical = session.scalars(
            select(InventoryMovement).where(
                InventoryMovement.movement_type == "SALE_CLASS_ATTRIBUTION"
            )
        ).all()
        assert len(physical) == 1 and physical[0].quantity == 2
        stock = {
            row.product_id: row.quantity_on_hand
            for row in session.scalars(
                select(InventoryBalance).where(InventoryBalance.location_code == "COUNTER")
            )
        }
        assert stock[product_id] == 8 and stock[alternate_id] == 10


def test_class_attribution_rejects_another_class_without_physical_effects(
    client: TestClient,
) -> None:
    headers, context = _setup(client, class_sale=True)
    sold = _sale(client, headers, context, class_sale=True)
    assert sold.status_code == 201, sold.text
    sale_id = UUID(sold.json()["id"])
    with SessionLocal() as session:
        line_id = session.scalars(select(SaleLine.id).where(SaleLine.sale_id == sale_id)).one()
        wrong_product = session.scalars(
            select(Product.id).where(Product.product_class_id != UUID(context["product_class_id"]))
        ).first()
        assert wrong_product is not None
        before = session.scalar(select(func.count()).select_from(InventoryMovement))
    response = client.post(
        f"/v1/sales/{sale_id}/attribute-inventory",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={
            "workstation_code": context["workstation_code"],
            "cash_session_id": context["cash_session_id"],
            "lines": [
                {
                    "sale_line_id": str(line_id),
                    "product_id": str(wrong_product),
                    "quantity": "1.000",
                }
            ],
        },
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "CONFLICT"
    assert response.json()["details"]["code"] == "CLASS_ATTRIBUTION_PRODUCT_MISMATCH"
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(InventoryMovement)) == before
        assert session.scalar(select(func.count()).select_from(ClassInventoryAttribution)) == 0
        assert session.scalars(select(ClassInventoryObligation.attributed_quantity)).one() == 0
