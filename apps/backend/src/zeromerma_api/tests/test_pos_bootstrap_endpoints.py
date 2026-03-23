from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.core.security import create_access_token
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.main import create_app
from zeromerma_api.tests.alembic_utils import alembic_upgrade_head


def auth_headers(user_id: int) -> dict[str, str]:
    """
    Build Authorization headers for protected POS bootstrap endpoint.
    """
    token = create_access_token(subject=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def reset_db(s: Session) -> None:
    """
    Hard reset all tables touched by POS bootstrap tests.

    The order matters because of FK dependencies.
    """
    s.execute(
        text(
            """
            TRUNCATE TABLE
                product_price,
                payment,
                sale_item,
                sale,
                inventory_movement,
                inventory_balance,
                cash_session,
                production_run,
                user_account,
                role,
                branch,
                product,
                product_category
            RESTART IDENTITY CASCADE
            """
        )
    )
    s.commit()


def seed_branch_role_user(s: Session) -> dict[str, int]:
    """
    Create one branch, one ADMIN role, and one active admin user.
    """
    branch_id = s.execute(
        text(
            """
            INSERT INTO branch (code, name, is_active, created_at, updated_at)
            VALUES ('MAIN', 'Main Branch', TRUE, now(), now())
            RETURNING id
            """
        )
    ).scalar_one()

    role_id = s.execute(
        text(
            """
            INSERT INTO role (code, name, created_at, updated_at)
            VALUES ('ADMIN', 'Administrator', now(), now())
            RETURNING id
            """
        )
    ).scalar_one()

    user_id = s.execute(
        text(
            """
            INSERT INTO user_account
                (branch_id, role_id, email, full_name, password_hash, is_active, created_at, updated_at)
            VALUES
                (:branch_id, :role_id, 'admin@example.com', 'Admin User', NULL, TRUE, now(), now())
            RETURNING id
            """
        ),
        {
            "branch_id": int(branch_id),
            "role_id": int(role_id),
        },
    ).scalar_one()

    s.commit()

    return {
        "branch_id": int(branch_id),
        "role_id": int(role_id),
        "user_id": int(user_id),
    }


def seed_open_cash_session(
    s: Session,
    *,
    branch_id: int,
    opened_by_id: int,
    opening_amount: Decimal = Decimal("1000.00"),
) -> int:
    """
    Create one OPEN cash session directly for bootstrap tests.
    """
    cash_session_id = s.execute(
        text(
            """
            INSERT INTO cash_session
                (branch_id, opened_by_id, opened_at, opening_amount, status, created_at, updated_at)
            VALUES
                (:branch_id, :opened_by_id, now(), :opening_amount, 'OPEN', now(), now())
            RETURNING id
            """
        ),
        {
            "branch_id": int(branch_id),
            "opened_by_id": int(opened_by_id),
            "opening_amount": opening_amount,
        },
    ).scalar_one()

    s.commit()
    return int(cash_session_id)


def seed_category(
    s: Session,
    *,
    code: str,
    name: str,
    quick_name: str,
    show_in_pos: bool,
    default_pos_order: int,
    is_active: bool = True,
) -> int:
    """
    Insert one category with POS projection fields.
    """
    category_id = s.execute(
        text(
            """
            INSERT INTO product_category
                (code, name, quick_name, show_in_pos, default_pos_order, is_active, created_at, updated_at)
            VALUES
                (:code, :name, :quick_name, :show_in_pos, :default_pos_order, :is_active, now(), now())
            RETURNING id
            """
        ),
        {
            "code": code,
            "name": name,
            "quick_name": quick_name,
            "show_in_pos": bool(show_in_pos),
            "default_pos_order": int(default_pos_order),
            "is_active": bool(is_active),
        },
    ).scalar_one()

    s.commit()
    return int(category_id)


def seed_product(
    s: Session,
    *,
    sku: str,
    name: str,
    quick_name: str,
    category_id: int,
    uom: str = "PCS",
    is_input: bool = False,
    show_in_pos: bool = True,
    is_sellable_in_pos: bool = True,
    default_pos_order: int = 100,
    sale_price: Decimal | None = None,
    standard_cost: Decimal | None = None,
    is_active: bool = True,
) -> int:
    """
    Insert one product with POS projection fields.
    """
    product_id = s.execute(
        text(
            """
            INSERT INTO product
                (
                    sku,
                    name,
                    quick_name,
                    category_id,
                    uom,
                    is_input,
                    show_in_pos,
                    is_sellable_in_pos,
                    default_pos_order,
                    sale_price,
                    standard_cost,
                    is_active,
                    created_at,
                    updated_at
                )
            VALUES
                (
                    :sku,
                    :name,
                    :quick_name,
                    :category_id,
                    :uom,
                    :is_input,
                    :show_in_pos,
                    :is_sellable_in_pos,
                    :default_pos_order,
                    :sale_price,
                    :standard_cost,
                    :is_active,
                    now(),
                    now()
                )
            RETURNING id
            """
        ),
        {
            "sku": sku,
            "name": name,
            "quick_name": quick_name,
            "category_id": int(category_id),
            "uom": uom,
            "is_input": bool(is_input),
            "show_in_pos": bool(show_in_pos),
            "is_sellable_in_pos": bool(is_sellable_in_pos),
            "default_pos_order": int(default_pos_order),
            "sale_price": sale_price,
            "standard_cost": standard_cost,
            "is_active": bool(is_active),
        },
    ).scalar_one()

    s.commit()
    return int(product_id)


def seed_price_override(
    s: Session,
    *,
    branch_id: int,
    product_id: int,
    price: Decimal,
    created_by_id: int,
) -> int:
    """
    Insert a branch-specific price override.
    """
    override_id = s.execute(
        text(
            """
            INSERT INTO product_price
                (branch_id, product_id, price, currency, created_by_id, created_at, updated_at)
            VALUES
                (:branch_id, :product_id, :price, 'MXN', :created_by_id, now(), now())
            RETURNING id
            """
        ),
        {
            "branch_id": int(branch_id),
            "product_id": int(product_id),
            "price": price,
            "created_by_id": int(created_by_id),
        },
    ).scalar_one()

    s.commit()
    return int(override_id)


def _find_category(payload: dict[str, Any], code: str) -> dict[str, Any]:
    """
    Helper to find one category by code in bootstrap payload.
    """
    for category in payload["categories"]:
        if category["code"] == code:
            return category
    raise AssertionError(f"Category {code!r} not found in payload.")


def _find_product(category: dict[str, Any], sku: str) -> dict[str, Any]:
    """
    Helper to find one product by SKU inside one bootstrap category.
    """
    for product in category["products"]:
        if product["sku"] == sku:
            return product
    raise AssertionError(f"Product {sku!r} not found in category {category['code']!r}.")


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS bootstrap tests",
)
def test_pos_bootstrap_returns_visible_catalog_effective_prices_and_open_session():
    """
    End-to-end validation of the POS bootstrap payload.

    Covers:
    - 200 response
    - current OPEN cash session included
    - hidden categories excluded
    - hidden products excluded
    - input/raw-material products excluded
    - branch override price preferred over catalog base price
    - base price used when no override exists
    - categories and products ordered by default_pos_order
    """
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)

        core = seed_branch_role_user(s)
        branch_id = core["branch_id"]
        user_id = core["user_id"]

        cash_session_id = seed_open_cash_session(
            s,
            branch_id=branch_id,
            opened_by_id=user_id,
            opening_amount=Decimal("1000.00"),
        )

        # Visible categories
        # drinks_category_id = seed_category(
        #    s,
        #    code="DRINKS",
        #    name="Drinks",
        #    quick_name="Drinks",
        #    show_in_pos=True,
        #   default_pos_order=10,
        # )
        donuts_category_id = seed_category(
            s,
            code="DONUTS",
            name="Donuts",
            quick_name="Donuts",
            show_in_pos=True,
            default_pos_order=20,
        )

        # Hidden category should not appear
        hidden_category_id = seed_category(
            s,
            code="INGREDIENTS",
            name="Ingredients",
            quick_name="Ingredients",
            show_in_pos=False,
            default_pos_order=900,
        )

        # Visible products in DRINKS (ordered by default_pos_order)
        # americano_id = seed_product(
        #    s,
        #    sku="COFFEE-AM",
        #    name="Coffee Americano",
        #    quick_name="Americano",
        #    category_id=drinks_category_id,
        #    default_pos_order=10,
        #    sale_price=Decimal("35.00"),
        # )
        # latte_id = seed_product(
        #    s,
        #    sku="COFFEE-LAT",
        #    name="Coffee Latte",
        #    quick_name="Latte",
        #    category_id=drinks_category_id,
        #    default_pos_order=20,
        #    sale_price=Decimal("45.00"),
        # )

        # Visible products in DONUTS (ordered by default_pos_order)
        # donut_cho_id = seed_product(
        #    s,
        #    sku="DONUT-CHO",
        #    name="Donut Chocolate",
        #    quick_name="Chocolate",
        #    category_id=donuts_category_id,
        #    default_pos_order=10,
        #    sale_price=Decimal("20.00"),
        # )
        donut_gla_id = seed_product(
            s,
            sku="DONUT-GLA",
            name="Donut Glazed",
            quick_name="Glazed",
            category_id=donuts_category_id,
            default_pos_order=20,
            sale_price=Decimal("18.00"),
        )

        # Hidden product should not appear
        _hidden_product_id = seed_product(
            s,
            sku="DONUT-HID",
            name="Hidden Donut",
            quick_name="Hidden",
            category_id=donuts_category_id,
            show_in_pos=False,
            is_sellable_in_pos=True,
            default_pos_order=30,
            sale_price=Decimal("22.00"),
        )

        # Input/raw material should not appear
        _input_product_id = seed_product(
            s,
            sku="FLOUR",
            name="Wheat Flour",
            quick_name="Flour",
            category_id=hidden_category_id,
            uom="KG",
            is_input=True,
            show_in_pos=False,
            is_sellable_in_pos=False,
            default_pos_order=900,
            sale_price=None,
            standard_cost=Decimal("18.00"),
        )

        # Product inside hidden category should not appear even if visible itself
        _hidden_category_product_id = seed_product(
            s,
            sku="ING-VIS",
            name="Ingredient Visible Name",
            quick_name="IngVis",
            category_id=hidden_category_id,
            is_input=False,
            show_in_pos=True,
            is_sellable_in_pos=True,
            default_pos_order=10,
            sale_price=Decimal("99.00"),
        )

        # Branch override for one product
        seed_price_override(
            s,
            branch_id=branch_id,
            product_id=donut_gla_id,
            price=Decimal("19.50"),
            created_by_id=user_id,
        )

    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    resp = client.get(
        "/pos/bootstrap",
        params={"branch_id": branch_id},
        headers=auth_headers(user_id),
    )
    assert resp.status_code == 200, resp.text

    payload = resp.json()

    # ---------------------------------------------------------------------
    # Branch context
    # ---------------------------------------------------------------------
    assert payload["branch_id"] == branch_id

    # ---------------------------------------------------------------------
    # Current open cash session
    # ---------------------------------------------------------------------
    assert payload["cash_session"] is not None
    assert payload["cash_session"]["id"] == cash_session_id
    assert payload["cash_session"]["status"] == "OPEN"
    assert Decimal(payload["cash_session"]["opening_amount"]) == Decimal("1000.00")
    assert payload["cash_session"]["opened_at"] is not None

    # ---------------------------------------------------------------------
    # Payment methods
    # ---------------------------------------------------------------------
    assert payload["payment_methods"] == [
        {"code": "CASH", "label": "Cash"},
        {"code": "CARD", "label": "Card"},
        {"code": "OTHER", "label": "Other"},
    ]

    # ---------------------------------------------------------------------
    # Capabilities
    # ---------------------------------------------------------------------
    assert payload["capabilities"] == {
        "can_take_orders": False,
        "can_deliver_orders": False,
        "keyboard_first": True,
    }

    # ---------------------------------------------------------------------
    # Category ordering
    # ---------------------------------------------------------------------
    category_codes = [c["code"] for c in payload["categories"]]
    assert category_codes == ["DRINKS", "DONUTS"]

    drinks = _find_category(payload, "DRINKS")
    donuts = _find_category(payload, "DONUTS")

    # Hidden category must not appear
    assert "INGREDIENTS" not in category_codes

    assert drinks["quick_name"] == "Drinks"
    assert drinks["default_pos_order"] == 10

    assert donuts["quick_name"] == "Donuts"
    assert donuts["default_pos_order"] == 20

    # ---------------------------------------------------------------------
    # Product ordering inside categories
    # ---------------------------------------------------------------------
    drink_skus = [p["sku"] for p in drinks["products"]]
    donut_skus = [p["sku"] for p in donuts["products"]]

    assert drink_skus == ["COFFEE-AM", "COFFEE-LAT"]
    assert donut_skus == ["DONUT-CHO", "DONUT-GLA"]

    # Hidden product must not appear
    assert "DONUT-HID" not in donut_skus

    # Input/raw-material product must not appear
    assert "FLOUR" not in drink_skus
    assert "FLOUR" not in donut_skus

    # Product under hidden category must not appear anywhere
    all_bootstrap_skus = {
        p["sku"] for category in payload["categories"] for p in category["products"]
    }
    assert "ING-VIS" not in all_bootstrap_skus

    # ---------------------------------------------------------------------
    # Effective price resolution
    # ---------------------------------------------------------------------
    americano = _find_product(drinks, "COFFEE-AM")
    latte = _find_product(drinks, "COFFEE-LAT")
    donut_cho = _find_product(donuts, "DONUT-CHO")
    donut_gla = _find_product(donuts, "DONUT-GLA")

    # No override -> uses base sale_price
    assert Decimal(americano["effective_price"]) == Decimal("35.00")
    assert Decimal(latte["effective_price"]) == Decimal("45.00")
    assert Decimal(donut_cho["effective_price"]) == Decimal("20.00")

    # Override present -> uses branch override price
    assert Decimal(donut_gla["effective_price"]) == Decimal("19.50")

    # ---------------------------------------------------------------------
    # Product shape sanity
    # ---------------------------------------------------------------------
    assert americano["name"] == "Coffee Americano"
    assert americano["quick_name"] == "Americano"
    assert americano["default_pos_order"] == 10
    assert americano["uom"] == "PCS"

    assert donut_gla["name"] == "Donut Glazed"
    assert donut_gla["quick_name"] == "Glazed"
    assert donut_gla["default_pos_order"] == 20
    assert donut_gla["uom"] == "PCS"
