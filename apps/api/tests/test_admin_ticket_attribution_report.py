"""Administrative pending-attribution reporting follows canonical physical progress."""

from decimal import Decimal
from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from inventory_fixtures import stock_for_codes
from sqlalchemy import select
from test_sale_physical_inventory import _sale, _setup

from zeromerma_api.bootstrap.seed_local import SEED_PRODUCT_COCA_355_CODE
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.sales.infrastructure.models import SaleLine
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.idempotency import new_idempotency_key


@pytest.mark.parametrize("lots", [False, True])
def test_admin_pending_report_tracks_partial_and_completed_class_attribution(
    client: TestClient, lots: bool
) -> None:
    headers, context = _setup(client, stock="5", lots=lots, class_sale=True)
    sale_response = _sale(client, headers, context, quantity="3", class_sale=True)
    assert sale_response.status_code == 201, sale_response.text
    sale_id = sale_response.json()["id"]
    stock_for_codes(
        workstation_code=context["workstation_code"],
        quantities={SEED_PRODUCT_COCA_355_CODE: Decimal(1)},
        location="COUNTER",
        reference="admin-attribution-direct-control",
    )
    with SessionLocal() as session:
        direct_product_id = session.scalars(
            select(Product.id).where(Product.code == SEED_PRODUCT_COCA_355_CODE)
        ).one()
    direct = _sale(client, headers, {**context, "product_id": str(direct_product_id)}, quantity="1")
    assert direct.status_code == 201, direct.text
    ticket = client.get(
        f"/v1/tickets/{sale_id}",
        headers=headers,
        params={"workstation_code": context["workstation_code"]},
    )
    assert ticket.status_code == 200, ticket.text
    original = ticket.json()["lines"][0]
    selected = next(
        option
        for option in original["attribution_options"]
        if option["product_id"] == context["product_id"]
    )
    admin = owner_headers()
    list_url = "/v1/admin/sales/tickets"
    params = {"pending_physical_only": "true", "branch_id": context["branch_id"]}
    detail_url = f"{list_url}/{sale_id}"

    def report() -> tuple[dict, dict]:
        # Read-only reporting must not calculate available inventory or allocation choices.
        with patch(
            "zeromerma_api.modules.inventory.application.attribution_queries.read_product_availability",
            side_effect=AssertionError("The administrative report must only read progress."),
        ):
            listing = client.get(list_url, headers=admin, params=params)
            detail = client.get(detail_url, headers=admin)
        assert listing.status_code == 200, listing.text
        assert detail.status_code == 200, detail.text
        return listing.json(), detail.json()["lines"][0]

    listing, line = report()
    assert listing["total"] == 1 and listing["metrics"]["ticket_count"] == 1
    assert listing["items"][0]["id"] == sale_id
    assert listing["items"][0]["pending_attribution_line_count"] == 1
    assert Decimal(line["attributed_quantity"]) == 0
    assert Decimal(line["remaining_attribution_quantity"]) == 3
    assert line["physical_attributions"] == []
    assert line["physical_attribution_status"] == "PENDING_RECONCILIATION"

    attribution_ids = []
    for quantity, remaining in [("1", 2), ("2", 0)]:
        attributed = client.post(
            f"/v1/sales/{sale_id}/attribute-inventory",
            headers={**headers, "Idempotency-Key": new_idempotency_key()},
            json={
                "workstation_code": context["workstation_code"],
                "cash_session_id": context["cash_session_id"],
                "lines": [
                    {
                        "sale_line_id": original["id"],
                        "product_id": context["product_id"],
                        "lot_id": selected["lot_id"],
                        "quantity": quantity,
                    }
                ],
            },
        )
        assert attributed.status_code == 200, attributed.text
        attribution_ids.append(attributed.json()["lines"][0]["attribution_id"])
        listing, line = report()
        assert Decimal(line["attributed_quantity"]) == 3 - remaining
        assert Decimal(line["remaining_attribution_quantity"]) == remaining
        assert listing["total"] == (1 if remaining else 0)
        assert [item["id"] for item in line["physical_attributions"]] == attribution_ids
        assert (
            sum((Decimal(item["quantity"]) for item in line["physical_attributions"]), Decimal(0))
            == 3 - remaining
        )
        assert all(
            item["product_id"] == context["product_id"] for item in line["physical_attributions"]
        )
        assert all(
            item["product_code"]
            and item["product_name"]
            and item["inventory_movement_id"]
            and item["occurred_at"]
            for item in line["physical_attributions"]
        )
        assert line["physical_attribution_status"] == (
            "PENDING_RECONCILIATION" if remaining else "RECONCILED"
        )

    all_tickets = client.get(list_url, headers=admin).json()
    assert all(item["pending_attribution_line_count"] == 0 for item in all_tickets["items"])
    direct_detail = client.get(f"{list_url}/{direct.json()['id']}", headers=admin)
    assert direct_detail.status_code == 200, direct_detail.text
    direct_line = direct_detail.json()["lines"][0]
    assert direct_line["physical_attribution_status"] == "DIRECT_ASSIGNED"
    assert direct_line["attributed_quantity"] is None
    assert direct_line["remaining_attribution_quantity"] is None
    assert direct_line["physical_attributions"] == []
    with SessionLocal() as session:
        stored = session.get(SaleLine, UUID(original["id"]))
        assert stored is not None and stored.quantity == 3
