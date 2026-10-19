"""Pure evidence boundaries for selective financial cutover."""

from datetime import UTC, datetime
from decimal import Decimal, localcontext
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from zeromerma_api.modules.financial_ledger.domain.money import FinancialModelError
from zeromerma_api.modules.financial_ledger.domain.reconciliation import FinancialImportManifest
from zeromerma_api.testing.idempotency import new_idempotency_key


def _manifest() -> dict[str, Any]:
    evidence = str(uuid4())
    now = datetime.now(UTC).isoformat()
    return {
        "manifest_id": str(uuid4()),
        "branch_id": str(uuid4()),
        "source_id": "SYNTHETIC_ACCEPTANCE_ONLY",
        "source_classification": "REAL_OPERATIONAL",
        "source_authority": "closed_and_reconcilable_economic_evidence",
        "source_evidence_sha256": "a" * 64,
        "approval_reference": "synthetic-test-approval",
        "approval_evidence_sha256": "b" * 64,
        "controlled_window_reference": "isolated-test",
        "cutover_at": now,
        "expected_row_count": 1,
        "expected_amount_due": "25.00",
        "rows": [
            {
                "row_key": "receivable-1",
                "idempotency_key": new_idempotency_key(),
                "treatment": "OPENING_ADJUSTMENT",
                "kind": "OPENING_OBLIGATION",
                "source_type": "OPENING_STATE",
                "source_id": evidence,
                "subject_type": "OPENING_BALANCE",
                "subject_id": str(uuid4()),
                "amount_due": "25.00",
                "occurred_at": now,
                "evidence_reference": evidence,
                "evidence_sha256": "c" * 64,
                "reason_code": "APPROVED_RECEIVABLE",
                "opening_obligation_kind": "RECEIVABLE",
            }
        ],
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("expected_row_count", 2),
        ("expected_amount_due", "26.00"),
        ("expected_amount_due", 25.0),
        ("cutover_at", "2026-01-01T00:00:00"),
    ],
)
def test_manifest_rejects_unreconciled_or_inexact_evidence(field: str, value: object) -> None:
    payload = _manifest()
    payload[field] = value
    with pytest.raises(ValidationError):
        FinancialImportManifest.model_validate(payload)


@pytest.mark.parametrize(
    "classification,source",
    [
        ("DEVELOPMENT_DEMO_TEST", "anything"),
        ("UNKNOWN", "anything"),
        ("REAL_OPERATIONAL", "PG-ZM-CURRENT"),
        ("REAL_OPERATIONAL", "pg-zm-legacy"),
        ("REAL_OPERATIONAL", " PG-ZM-CURRENT "),
    ],
)
def test_test_sources_cannot_be_relabelled_as_productive_history(
    classification: str, source: str
) -> None:
    payload = _manifest()
    payload.update(source_classification=classification, source_id=source)
    with pytest.raises(FinancialModelError):
        FinancialImportManifest.model_validate(payload).require_productive_source()


def test_manifest_identity_and_hash_bind_every_row_and_approval() -> None:
    payload = _manifest()
    first = FinancialImportManifest.model_validate(payload)
    assert (
        FinancialImportManifest.model_validate_json(first.model_dump_json()).digest()
        == first.digest()
    )
    payload["approval_reference"] = "different-approval"
    assert FinancialImportManifest.model_validate(payload).digest() != first.digest()
    payload["rows"].append(dict(payload["rows"][0]))
    payload.update(expected_row_count=2, expected_amount_due="50.00")
    with pytest.raises(ValidationError, match="duplicated"):
        FinancialImportManifest.model_validate(payload)


@pytest.mark.parametrize(
    "mutation", ["fake_sale", "fractional_cent", "cash_obligation", "future_source"]
)
def test_opening_state_cannot_fabricate_history_or_cash(mutation: str) -> None:
    payload = _manifest()
    row = payload["rows"][0]
    if mutation == "fake_sale":
        row["kind"] = "SALE_COLLECTION"
    elif mutation == "fractional_cent":
        row["amount_due"] = "25.001"
    elif mutation == "cash_obligation":
        row["cash_session_id"] = str(uuid4())
    else:
        row["occurred_at"] = "2099-01-01T00:00:00+00:00"
    with pytest.raises(ValidationError):
        FinancialImportManifest.model_validate(payload)


def test_manifest_totals_ignore_the_callers_decimal_precision() -> None:
    payload = _manifest()
    payload["rows"][0]["amount_due"] = "25.55"
    second = dict(payload["rows"][0])
    evidence = str(uuid4())
    second.update(
        row_key="receivable-2",
        idempotency_key=new_idempotency_key(),
        source_id=evidence,
        evidence_reference=evidence,
        subject_id=str(uuid4()),
        amount_due="10.15",
    )
    payload.update(
        rows=[payload["rows"][0], second], expected_row_count=2, expected_amount_due="35.70"
    )
    with localcontext() as context:
        context.prec = 2
        manifest = FinancialImportManifest.model_validate(payload)
    assert manifest.expected_amount_due == Decimal("35.70")


def test_diagnostic_totals_ignore_the_callers_decimal_precision() -> None:
    from unittest.mock import MagicMock

    from zeromerma_api.modules.financial_ledger.application.reconciliation import (
        _financial_snapshot,
    )

    session = MagicMock()
    session.execute.side_effect = [
        [],
        [
            (uuid4(), "CONFIRMED", "CASH", "IN", Decimal("25.55")),
            (uuid4(), "CONFIRMED", "CASH", "IN", Decimal("10.15")),
        ],
    ]
    with localcontext() as context:
        context.prec = 2
        snapshot = _financial_snapshot(session, uuid4())
    assert snapshot["confirmed_totals"] == {"CASH_IN": "35.70"}
