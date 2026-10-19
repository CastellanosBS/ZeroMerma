"""Explicit physical inputs for business tests; no implicit stock in shared seed data."""

from decimal import Decimal

from sqlalchemy import select

from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.branches.infrastructure.models import Workstation
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.testing.inventory import seed_test_inventory
from zeromerma_api.testing.transfer_operators import transfer_cashier_email


def stock_for_codes(
    *, workstation_code: str, quantities: dict[str, Decimal], location: str, reference: str
) -> None:
    with SessionLocal() as session:
        station = session.scalars(
            select(Workstation).where(Workstation.code == workstation_code)
        ).one()
        actor = session.scalars(
            select(User.id).where(User.email == transfer_cashier_email(workstation_code))
        ).one()
        products = session.scalars(select(Product).where(Product.code.in_(quantities))).all()
        assert len(products) == len(quantities), (
            "Every synthetic input must identify a real product."
        )
        seed_test_inventory(
            session,
            branch_id=station.branch_id,
            actor_user_id=actor,
            product_quantities={product.id: quantities[product.code] for product in products},
            location_code=location,
            fixture_reference=reference,
        )
