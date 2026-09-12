from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel

from zeromerma_api.modules.discounts.application.schemas import AdminCommercialDiscountCreateRequest


class ContractState(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ContractTypes(BaseModel):
    identifier: UUID
    amount: Decimal
    occurred_at: datetime
    state: ContractState
    optional_note: str | None = None


@pytest.mark.parametrize(
    "value",
    ["0.1", "0.2", "0.3", "33.33", "999999999999.99", "0.125"],
)
def test_decimal_round_trip_is_lossless(value: str) -> None:
    model = ContractTypes(
        identifier=uuid4(),
        amount=Decimal(value),
        occurred_at=datetime(2026, 9, 4, 12, 30, tzinfo=UTC),
        state=ContractState.ACTIVE,
    )

    payload = model.model_dump_json()
    restored = ContractTypes.model_validate_json(payload)

    assert restored.amount == Decimal(value)
    assert f'"amount":"{value}"' in payload


def test_uuid_datetime_enum_and_nullability_wire_contract() -> None:
    identifier = uuid4()
    model = ContractTypes(
        identifier=identifier,
        amount=Decimal("33.33"),
        occurred_at=datetime(2026, 9, 4, 12, 30, tzinfo=UTC),
        state=ContractState.INACTIVE,
    )
    payload = model.model_dump(mode="json")

    assert payload["identifier"] == str(identifier)
    assert payload["occurred_at"] == "2026-09-04T12:30:00Z"
    assert payload["state"] == "INACTIVE"
    assert payload["optional_note"] is None


def test_uuid_rejects_numeric_identifiers() -> None:
    with pytest.raises(ValueError):
        ContractTypes.model_validate(
            {
                "identifier": 42,
                "amount": "0.1",
                "occurred_at": "2026-09-04T12:30:00Z",
                "state": "ACTIVE",
            }
        )


@pytest.mark.parametrize("value", ["33.33", 33.33])
def test_actual_discount_request_accepts_numeric_or_string_decimal_and_serializes_string(
    value: str | float,
) -> None:
    import json

    request = AdminCommercialDiscountCreateRequest.model_validate_json(
        json.dumps(
            {
                "name": "Contract example",
                "discount_type": "PERCENTAGE",
                "target_scope": "GLOBAL",
                "value": value,
            }
        )
    )

    assert request.value == Decimal("33.33")
    assert request.model_dump(mode="json")["value"] == "33.33"


@pytest.mark.parametrize(
    ("timestamp", "is_naive"),
    [
        ("2026-09-12T10:00:00Z", False),
        ("2026-09-12T10:00:00-07:00", False),
        ("2026-09-12T10:00:00", True),
    ],
)
def test_actual_discount_request_preserves_existing_datetime_acceptance(
    timestamp: str, is_naive: bool
) -> None:
    request = AdminCommercialDiscountCreateRequest.model_validate(
        {
            "name": "Contract example",
            "discount_type": "PERCENTAGE",
            "target_scope": "GLOBAL",
            "value": "33.33",
            "valid_from_utc": timestamp,
        }
    )

    assert request.valid_from_utc is not None
    assert (request.valid_from_utc.tzinfo is None) is is_naive
    assert request.model_dump(mode="json")["valid_from_utc"] == timestamp


def test_served_openapi_matches_the_generated_contract() -> None:
    import json
    from pathlib import Path

    from fastapi.testclient import TestClient

    from zeromerma_api.main import create_app

    artifact = Path(__file__).resolve().parents[3] / "packages/api-client/openapi.json"
    response = TestClient(create_app()).get("/openapi.json")
    assert response.status_code == 200
    assert response.json() == json.loads(artifact.read_text(encoding="utf-8"))
