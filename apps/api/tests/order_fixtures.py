"""Opt-in physical stock for order reservation and delivery acceptance."""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID

from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_PRODUCT_BOLILLO_STD_CODE,
    SEED_PRODUCT_CAFE_AMERICANO_CODE,
    SEED_USER_EMAIL,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.branches.infrastructure.models import Workstation
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.orders.infrastructure.models import CustomerOrder, OrderCommitmentPolicy
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.inventory import seed_test_inventory


def seed_order_stock(*, workstation_code: str = SEED_WORKSTATION_CODE) -> None:
    with SessionLocal() as session:
        station = session.scalar(select(Workstation).where(Workstation.code == workstation_code))
        actor = session.scalar(select(User).where(User.email == SEED_USER_EMAIL))
        assert station is not None and actor is not None
        products = session.scalars(
            select(Product).where(
                Product.code.in_((SEED_PRODUCT_BOLILLO_STD_CODE, SEED_PRODUCT_CAFE_AMERICANO_CODE))
            )
        ).all()
        assert len(products) == 2
        seed_test_inventory(
            session,
            branch_id=station.branch_id,
            actor_user_id=actor.id,
            product_quantities={product.id: Decimal(100) for product in products},
            location_code="COUNTER",
            fixture_reference="Order acceptance physical stock",
        )


def quote_order_payload(client, headers, payload, *, lead_time_minutes=1440):
    """Explicit test-only policy and real backend quotation; never adjust money silently."""
    station_code = payload["workstation_code"]
    with SessionLocal() as session:
        station = session.scalar(select(Workstation).where(Workstation.code == station_code))
        branch_id = station.branch_id
        configured = session.scalar(
            select(OrderCommitmentPolicy).where(OrderCommitmentPolicy.branch_id == branch_id)
        )
    if configured is None:
        response = client.post(
            f"/v1/admin/orders/commitment-policies/{branch_id}",
            headers={**owner_headers(), "Idempotency-Key": new_idempotency_key()},
            json={
                "lead_time_minutes": lead_time_minutes,
                "reason": "Explicit synthetic order acceptance policy",
            },
        )
        assert response.status_code == 201, response.text
    body = dict(payload)
    if body.get("requested_for_at") is None:
        body["requested_for_at"] = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    response = client.post(
        "/v1/orders/quote",
        headers=headers,
        json={
            "workstation_code": station_code,
            "requested_for_at": body["requested_for_at"],
            "items": body["items"],
        },
    )
    assert response.status_code == 200, response.text
    body["quote_fingerprint"] = response.json()["quote_fingerprint"]
    return body


@contextmanager
def order_clock(instant):
    """Advance only the order domain clock; authentication and DB ownership remain real."""

    class FixedOrderDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz) if tz is not None else instant.replace(tzinfo=None)

    with (
        patch(
            "zeromerma_api.modules.orders.application.commitment.current_order_time",
            return_value=instant,
        ),
        patch(
            "zeromerma_api.modules.orders.application.services.current_order_time",
            return_value=instant,
        ),
        patch(
            "zeromerma_api.modules.orders.application.admin_services.current_order_time",
            return_value=instant,
        ),
        patch("zeromerma_api.modules.orders.application.commitment.datetime", FixedOrderDateTime),
        patch("zeromerma_api.modules.orders.application.services.datetime", FixedOrderDateTime),
        patch(
            "zeromerma_api.modules.orders.application.admin_services.datetime", FixedOrderDateTime
        ),
    ):
        yield


@contextmanager
def committed_order_clock(order_id):
    with SessionLocal() as session:
        order = session.get(CustomerOrder, UUID(str(order_id)))
        assert order is not None and order.production_commit_at is not None
        instant = order.production_commit_at + timedelta(seconds=1)
    with order_clock(instant):
        yield
