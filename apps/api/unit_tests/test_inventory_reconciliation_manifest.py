from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from zeromerma_api.modules.inventory.domain.exceptions import InventoryValidationError
from zeromerma_api.modules.inventory.domain.reconciliation import InventoryReconciliationManifest
from zeromerma_api.testing.idempotency import new_idempotency_key


def _data() -> dict:
    return {
        "manifest_id": uuid4(),
        "branch_id": uuid4(),
        "source_id": "physical-count-sheet",
        "source_classification": "REAL_OPERATIONAL",
        "source_evidence_sha256": "a" * 64,
        "approval_reference": "synthetic-reference-only",
        "approval_evidence_sha256": "b" * 64,
        "controlled_window_reference": "synthetic-window",
        "cutover_at": datetime.now(UTC),
        "expected_row_count": 1,
        "rows": [
            {
                "row_key": "opening-flour",
                "idempotency_key": new_idempotency_key(),
                "action": "OPENING",
                "product_id": uuid4(),
                "location_code": "BACKROOM",
                "unit_of_measure": "KG",
                "quantity": "10.000",
                "inventory_value": "125.50000000",
                "evidence_reference": "count-sheet-1",
                "evidence_sha256": "c" * 64,
                "reason": "Validated physical count",
            }
        ],
    }


@pytest.mark.parametrize(
    "change", ["duplicate", "count", "float", "precision", "uom", "rebuild", "uuid"]
)
def test_manifest_rejects_ambiguous_or_lossy_evidence(change: str) -> None:
    data = _data()
    if change == "duplicate":
        data["rows"].append(data["rows"][0].copy())
        data["expected_row_count"] = 2
    elif change == "count":
        data["expected_row_count"] = 2
    elif change == "float":
        data["rows"][0]["quantity"] = 0.1
    elif change == "precision":
        data["rows"][0]["quantity"] = "0.0001"
    elif change == "uom":
        data["rows"][0]["location_code"] = "UNKNOWN"
    elif change == "rebuild":
        data["rows"][0]["action"] = "REBUILD"
    else:
        data["rows"][0]["idempotency_key"] = uuid4()
    with pytest.raises((ValidationError, InventoryValidationError)):
        InventoryReconciliationManifest.model_validate(data)


def test_known_demo_volume_cannot_be_reclassified_as_productive_and_hash_covers_evidence() -> None:
    data = _data()
    first = InventoryReconciliationManifest.model_validate(data)
    data["approval_reference"] = "another-declaration"
    second = InventoryReconciliationManifest.model_validate(data)
    assert first.digest() != second.digest()
    data["source_id"] = "PG-ZM-CURRENT"
    demo = InventoryReconciliationManifest.model_validate(data)
    with pytest.raises(InventoryValidationError):
        demo.require_productive_source()
