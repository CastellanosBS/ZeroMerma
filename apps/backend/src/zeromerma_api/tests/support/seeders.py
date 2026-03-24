from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.tests.auth_helpers import build_auth_headers


def seed_role(session: Session, *, code: str, name: str) -> int:
    """
    Insert one role row and return its id.
    """
    role_id = session.execute(
        text(
            """
            INSERT INTO role (code, name, created_at, updated_at)
            VALUES (:code, :name, now(), now())
            RETURNING id
            """
        ),
        {"code": code, "name": name},
    ).scalar_one()
    session.commit()
    return int(role_id)


def seed_branch(session: Session, *, code: str, name: str) -> int:
    """
    Insert one branch row and return its id.
    """
    branch_id = session.execute(
        text(
            """
            INSERT INTO branch (code, name, is_active, created_at, updated_at)
            VALUES (:code, :name, TRUE, now(), now())
            RETURNING id
            """
        ),
        {"code": code, "name": name},
    ).scalar_one()
    session.commit()
    return int(branch_id)


def seed_user(
    session: Session,
    *,
    branch_id: int,
    role_id: int,
    email: str,
    full_name: str,
    is_active: bool = True,
) -> int:
    """
    Insert one user_account row and return its id.
    """
    user_id = session.execute(
        text(
            """
            INSERT INTO user_account
                (
                    branch_id,
                    role_id,
                    email,
                    full_name,
                    password_hash,
                    is_active,
                    created_at,
                    updated_at
                )
            VALUES
                (
                    :branch_id,
                    :role_id,
                    :email,
                    :full_name,
                    NULL,
                    :is_active,
                    now(),
                    now()
                )
            RETURNING id
            """
        ),
        {
            "branch_id": int(branch_id),
            "role_id": int(role_id),
            "email": email,
            "full_name": full_name,
            "is_active": bool(is_active),
        },
    ).scalar_one()
    session.commit()
    return int(user_id)


def seed_category(
    session: Session,
    *,
    code: str,
    name: str,
    quick_name: str | None = None,
    show_in_pos: bool = True,
    default_pos_order: int = 10,
    is_active: bool = True,
) -> int:
    """
    Insert one product_category row and return its id.
    """
    category_id = session.execute(
        text(
            """
            INSERT INTO product_category
                (
                    code,
                    name,
                    quick_name,
                    show_in_pos,
                    default_pos_order,
                    is_active,
                    created_at,
                    updated_at
                )
            VALUES
                (
                    :code,
                    :name,
                    :quick_name,
                    :show_in_pos,
                    :default_pos_order,
                    :is_active,
                    now(),
                    now()
                )
            RETURNING id
            """
        ),
        {
            "code": code,
            "name": name,
            "quick_name": quick_name if quick_name is not None else name,
            "show_in_pos": bool(show_in_pos),
            "default_pos_order": int(default_pos_order),
            "is_active": bool(is_active),
        },
    ).scalar_one()
    session.commit()
    return int(category_id)


def seed_product(
    session: Session,
    *,
    category_id: int,
    sku: str,
    name: str,
    quick_name: str | None = None,
    sale_price: Decimal | None,
    branch_id: int | None = None,
    on_hand: Decimal | None = None,
    is_input: bool = False,
    show_in_pos: bool = True,
    is_sellable_in_pos: bool = True,
    default_pos_order: int = 10,
    uom: str = "PCS",
    is_active: bool = True,
) -> int:
    """
    Insert one product row and optionally seed inventory_balance.

    If both branch_id and on_hand are provided, an inventory_balance row is
    also created for that branch/product pair.
    """
    product_id = session.execute(
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
            "quick_name": quick_name if quick_name is not None else name,
            "category_id": int(category_id),
            "uom": uom,
            "is_input": bool(is_input),
            "show_in_pos": bool(show_in_pos),
            "is_sellable_in_pos": bool(is_sellable_in_pos),
            "default_pos_order": int(default_pos_order),
            "sale_price": sale_price,
            "is_active": bool(is_active),
        },
    ).scalar_one()

    if branch_id is not None and on_hand is not None:
        session.execute(
            text(
                """
                INSERT INTO inventory_balance
                    (branch_id, product_id, on_hand, reserved, created_at, updated_at)
                VALUES
                    (:branch_id, :product_id, :on_hand, 0.000, now(), now())
                """
            ),
            {
                "branch_id": int(branch_id),
                "product_id": int(product_id),
                "on_hand": on_hand,
            },
        )

    session.commit()
    return int(product_id)


def seed_price_override(
    session: Session,
    *,
    branch_id: int,
    product_id: int,
    price: Decimal,
    created_by_id: int,
) -> int:
    """
    Insert one product_price override and return its id.
    """
    override_id = session.execute(
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
    session.commit()
    return int(override_id)


def open_cash_session(
    client: TestClient,
    *,
    branch_id: int,
    user_id: int,
    role_code: str | None = None,
) -> int:
    """
    Open one POS cash session through the public endpoint and return its id.
    """
    response = client.post(
        "/pos/cash-sessions/open",
        json={"branch_id": branch_id, "opening_amount": "1000.00"},
        headers=build_auth_headers(
            user_id=user_id,
            role_code=role_code,
            branch_id=branch_id,
        ),
    )
    assert response.status_code == 200, response.text
    return int(response.json()["id"])


def create_order(
    client: TestClient,
    *,
    branch_id: int,
    user_id: int,
    role_code: str | None,
    product_id: int,
    qty: str,
    customer_name: str | None = None,
    requested_for_at: str | None = None,
) -> int:
    """
    Create one customer order through the public endpoint and return its id.
    """
    response = client.post(
        "/pos/orders",
        json={
            "branch_id": branch_id,
            "customer_name": customer_name,
            "requested_for_at": requested_for_at,
            "items": [{"product_id": product_id, "qty": qty}],
        },
        headers=build_auth_headers(
            user_id=user_id,
            role_code=role_code,
            branch_id=branch_id,
        ),
    )
    assert response.status_code == 200, response.text
    return int(response.json()["id"])


def send_order_to_bakery(
    client: TestClient,
    *,
    order_id: int,
    branch_id: int,
    user_id: int,
    role_code: str | None,
) -> None:
    """
    Move one order from CREATED to SENT_TO_BAKERY.
    """
    response = client.post(
        f"/pos/orders/{order_id}/send-to-bakery",
        headers=build_auth_headers(
            user_id=user_id,
            role_code=role_code,
            branch_id=branch_id,
        ),
    )
    assert response.status_code == 200, response.text


def mark_order_ready(
    client: TestClient,
    *,
    order_id: int,
    branch_id: int,
    user_id: int,
    role_code: str | None,
) -> None:
    """
    Move one order from SENT_TO_BAKERY to READY.
    """
    response = client.post(
        f"/pos/orders/{order_id}/ready",
        headers=build_auth_headers(
            user_id=user_id,
            role_code=role_code,
            branch_id=branch_id,
        ),
    )
    assert response.status_code == 200, response.text


def create_ready_order(
    client: TestClient,
    *,
    branch_id: int,
    admin_user_id: int,
    cashier_user_id: int,
    product_id: int,
    qty: str = "2.000",
    customer_name: str = "Transfer Customer",
) -> int:
    """
    Create an order and move it to READY using canonical POS endpoints.
    """
    order_id = create_order(
        client,
        branch_id=branch_id,
        user_id=cashier_user_id,
        role_code="CASHIER",
        product_id=product_id,
        qty=qty,
        customer_name=customer_name,
    )
    send_order_to_bakery(
        client,
        order_id=order_id,
        branch_id=branch_id,
        user_id=admin_user_id,
        role_code="ADMIN",
    )
    mark_order_ready(
        client,
        order_id=order_id,
        branch_id=branch_id,
        user_id=admin_user_id,
        role_code="ADMIN",
    )
    return order_id
