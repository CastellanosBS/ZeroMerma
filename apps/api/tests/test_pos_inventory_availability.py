"""POS reads eligible counter availability without admitting physical effects."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_inventory_core import _run

from zeromerma_api.bootstrap.seed_local import (
    SEED_BRANCH_CODE,
    SEED_DESTINATION_BRANCH_CODE,
    SEED_PRODUCT_CAFE_AMERICANO_CODE,
    SEED_PRODUCT_COCA_355_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.inventory.application.mutations import (
    InventoryBalanceKey,
    create_inventory_lot,
)
from zeromerma_api.modules.inventory.infrastructure.lot_models import InventoryLotBalance
from zeromerma_api.modules.inventory.infrastructure.models import InventoryBalance
from zeromerma_api.testing.sessions import login_headers


def test_catalog_excludes_expired_stock_and_other_locations_and_reports_fefo(
    client: TestClient,
) -> None:
    with SessionLocal() as session:
        product = session.scalars(
            select(Product).where(Product.code == SEED_PRODUCT_COCA_355_CODE)
        ).one()
        product.lot_tracking_enabled = True
        product.expiry_required = True
        product_id, class_id = product.id, product.product_class_id
        branch = session.scalars(select(Branch.id).where(Branch.code == SEED_BRANCH_CODE)).one()
        other = session.scalars(
            select(Branch.id).where(Branch.code == SEED_DESTINATION_BRANCH_CODE)
        ).one()
        actor = session.scalars(select(User.id).where(User.email == SEED_USER_EMAIL)).one()
        session.commit()
    key = InventoryBalanceKey(branch, product_id, "COUNTER")

    def create_lots(session: Session) -> list[UUID]:
        return [
            create_inventory_lot(
                session,
                product_id=product_id,
                lot_code=code,
                expires_at=datetime.now(UTC) + timedelta(days=days),
                source_document_type="SYNTHETIC_ACCEPTANCE",
                source_document_id=uuid4(),
                source_line_id=None,
                branch_id=branch,
                operator_user_id=actor,
            ).id
            for code, days in (("EXPIRED", -1), ("SOON", 1), ("LATER", 2))
        ]

    lot_ids = [UUID(value) for value in _run(key, actor, create_lots).payload["ids"]]
    with SessionLocal() as session:
        for branch_id, location in ((branch, "COUNTER"), (branch, "BACKROOM"), (other, "COUNTER")):
            session.add(
                InventoryBalance(
                    branch_id=branch_id,
                    product_id=product_id,
                    location_code=location,
                    quantity_on_hand=Decimal(
                        10 if location == "COUNTER" and branch_id == branch else 99
                    ),
                    quantity_reserved=Decimal(
                        2 if location == "COUNTER" and branch_id == branch else 0
                    ),
                )
            )
        for lot_id, quantity, reserved in zip(lot_ids, (2, 3, 5), (0, 1, 1), strict=True):
            session.add(
                InventoryLotBalance(
                    branch_id=branch,
                    product_id=product_id,
                    lot_id=lot_id,
                    location_code="COUNTER",
                    quantity_on_hand=Decimal(quantity),
                    quantity_reserved=Decimal(reserved),
                )
            )
        session.commit()
    headers = login_headers(
        client,
        email=SEED_USER_EMAIL,
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=SEED_WORKSTATION_CODE,
    )
    path = f"/v1/pos/classes/{class_id}/products?workstation_code={SEED_WORKSTATION_CODE}"
    response = client.get(path, headers=headers)
    assert response.status_code == 200, response.text
    product_view = next(
        item for item in response.json()["products"] if item["id"] == str(product_id)
    )
    assert Decimal(product_view["available_quantity"]) == 6
    assert Decimal(product_view["reserved_quantity"]) == 2
    assert [item["lot_code"] for item in product_view["available_lots"]] == ["SOON", "LATER"]
    assert [Decimal(item["available_quantity"]) for item in product_view["available_lots"]] == [
        2,
        4,
    ]
    with SessionLocal() as session:
        balance = session.scalars(
            select(InventoryBalance).where(
                InventoryBalance.branch_id == branch,
                InventoryBalance.product_id == product_id,
                InventoryBalance.location_code == "COUNTER",
            )
        ).one()
        balance.quantity_on_hand = Decimal(4)
        session.commit()
    constrained = client.get(path, headers=headers)
    assert constrained.status_code == 200, constrained.text
    current = next(item for item in constrained.json()["products"] if item["id"] == str(product_id))
    assert Decimal(current["available_quantity"]) == 2
    assert [item["lot_code"] for item in current["available_lots"]] == ["SOON"]


def test_catalog_reports_zero_for_missing_stock_and_null_only_for_noninventory(
    client: TestClient,
) -> None:
    with SessionLocal() as session:
        product = session.scalars(
            select(Product).where(Product.code == SEED_PRODUCT_CAFE_AMERICANO_CODE)
        ).one()
        product.is_inventory_tracked = False
        class_id = product.product_class_id
        session.commit()
    headers = login_headers(
        client,
        email=SEED_USER_EMAIL,
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=SEED_WORKSTATION_CODE,
    )
    response = client.get(
        f"/v1/pos/classes/{class_id}/products?workstation_code={SEED_WORKSTATION_CODE}",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    by_code = {item["code"]: item for item in response.json()["products"]}
    assert by_code[SEED_PRODUCT_CAFE_AMERICANO_CODE]["available_quantity"] is None
    assert Decimal(by_code[SEED_PRODUCT_COCA_355_CODE]["available_quantity"]) == 0
