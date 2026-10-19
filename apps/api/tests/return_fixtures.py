"""Explicit physical stock for return tests, admitted through the guarded inventory helper."""

from decimal import Decimal

from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_PRODUCT_COCA_355_CODE,
    SEED_PRODUCT_CONCHA_VAN_CODE,
    SEED_USER_EMAIL,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.branches.infrastructure.models import Workstation
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.testing.inventory import seed_test_inventory


def seed_return_stock(
    *,
    workstation_code: str = SEED_WORKSTATION_CODE,
    location_code: str = "COUNTER",
    product_codes: tuple[str, ...] = (SEED_PRODUCT_COCA_355_CODE, SEED_PRODUCT_CONCHA_VAN_CODE),
    quantity: Decimal = Decimal(20),
) -> None:
    with SessionLocal() as session:
        station = session.scalar(select(Workstation).where(Workstation.code == workstation_code))
        actor = session.scalar(select(User).where(User.email == SEED_USER_EMAIL))
        assert station is not None and actor is not None
        products = session.scalars(select(Product).where(Product.code.in_(product_codes))).all()
        assert len(products) == len(product_codes)
        seed_test_inventory(
            session,
            branch_id=station.branch_id,
            actor_user_id=actor.id,
            product_quantities={product.id: quantity for product in products},
            location_code=location_code,
            fixture_reference="Return acceptance physical stock",
        )
