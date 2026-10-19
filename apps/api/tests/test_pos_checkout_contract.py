"""Checkout admission protects the price reviewed by the cashier."""

from copy import deepcopy
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from test_sale_idempotency import _counts, _setup, _submit

from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.testing.idempotency import new_idempotency_key


@pytest.mark.parametrize("new_price", ["10.00", "20.00"])
def test_changed_price_requires_review_even_when_cash_covers_it(
    client: TestClient, new_price: str
) -> None:
    headers, body = _setup(client)
    before = _counts()
    with SessionLocal() as session:
        product = session.get(Product, UUID(body["lines"][1]["product_id"]))
        assert product is not None
        product.unit_price = Decimal(new_price)
        session.commit()
    key = new_idempotency_key()
    rejected = _submit(client, headers, body, key)
    assert rejected.status_code == 409
    assert rejected.json()["code"] == "SALE_PRICE_CHANGED"
    assert _counts() == before
    body["lines"][1]["expected_unit_price"] = new_price
    accepted = _submit(client, headers, body, key)
    assert accepted.status_code == 201
    assert Decimal(accepted.json()["total_amount"]) == Decimal(new_price) + 12
    assert _submit(client, headers, body, key).json() == accepted.json()


def test_changed_currency_is_not_silently_accepted(client: TestClient) -> None:
    headers, body = _setup(client)
    body["lines"] = body["lines"][:1]
    with SessionLocal() as session:
        product_class = session.get(ProductClass, UUID(body["lines"][0]["product_class_id"]))
        assert product_class is not None
        product_class.currency_code = "USD"
        session.commit()
    before = _counts()
    rejected = _submit(client, headers, body, new_idempotency_key())
    assert rejected.status_code == 409
    assert rejected.json()["code"] == "SALE_PRICE_CHANGED"
    assert _counts() == before


@pytest.mark.parametrize("invalid", ["missing_price", "duplicate", "zero", "negative", "precision"])
def test_invalid_cart_never_writes_effects(client: TestClient, invalid: str) -> None:
    headers, body = _setup(client)
    if invalid == "missing_price":
        del body["lines"][0]["expected_unit_price"]
    elif invalid == "duplicate":
        body["lines"].append(deepcopy(body["lines"][0]))
    else:
        body["lines"][0]["quantity"] = {"zero": "0", "negative": "-1", "precision": "0.0001"}[
            invalid
        ]
    before = _counts()
    rejected = _submit(client, headers, body, new_idempotency_key())
    assert rejected.status_code == 422
    assert _counts() == before


def test_mixed_payment_change_is_funded_only_by_cash(client: TestClient) -> None:
    headers, body = _setup(client)
    body["payments"] = [
        {"payment_method_code": "CARD", "tendered_amount": "20.00"},
        {"payment_method_code": "CASH", "tendered_amount": "50.00"},
    ]
    response = _submit(client, headers, body, new_idempotency_key())
    assert response.status_code == 201
    assert Decimal(response.json()["change_amount"]) == 40
    card, cash = response.json()["payments"]
    assert Decimal(card["applied_amount"]) == 20
    assert Decimal(card["change_amount"]) == 0
    assert Decimal(cash["applied_amount"]) == 10
    assert Decimal(cash["change_amount"]) == 40
