from __future__ import annotations

import copy
import importlib.util
import json
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
VALIDATOR_PATH = REPO_ROOT / "scripts/dev/check-functional-operation-matrix.py"
MATRIX_PATH = REPO_ROOT / "docs/architecture/FUNCTIONAL_OPERATION_MATRIX.json"


def _load_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "functional_operation_matrix_validator", VALIDATOR_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


VALIDATOR = _load_validator()
INVENTORY = VALIDATOR.discover_inventory(REPO_ROOT)
CANONICAL_MATRIX = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def _errors(data: dict[str, Any]) -> list[str]:
    return cast(list[str], VALIDATOR.validate_matrix(data, INVENTORY, REPO_ROOT))


def test_canonical_matrix_passes() -> None:
    assert _errors(CANONICAL_MATRIX) == []


def test_contract_generation_tool_is_not_a_functional_operation() -> None:
    assert "INTERNAL:scripts.dev.api-contracts:command" not in INVENTORY.internal
    assert "INTERNAL:scripts.dev.run-web-integration:command" not in INVENTORY.internal
    assert "INTERNAL:scripts.dev.seed-web-integration:command" not in INVENTORY.internal


@pytest.mark.parametrize(
    ("mutate", "expected_error"),
    [
        (
            lambda data: data["api_operations"].pop(0),
            "api_operations registered operation missing from matrix",
        ),
        (
            lambda data: data["api_operations"].append(
                {
                    **data["api_operations"][0],
                    "operation_key": "API:GET:/v1/not-registered",
                    "path": "/v1/not-registered",
                }
            ),
            "api_operations matrix row has no registered operation",
        ),
        (
            lambda data: data["pos_routes"].pop(0),
            "pos_routes registered operation missing from matrix",
        ),
        (
            lambda data: data["backoffice_routes"].pop(0),
            "backoffice_routes registered operation missing from matrix",
        ),
        (
            lambda data: data["api_operations"].append(copy.deepcopy(data["api_operations"][0])),
            "duplicate operation keys",
        ),
        (
            lambda data: data["api_operations"][0].__setitem__("use_case", ""),
            ".use_case is blank",
        ),
        (
            lambda data: data["api_operations"][0].__setitem__("implementation_state", "UNKNOWN"),
            "UNKNOWN values remain",
        ),
        (
            lambda data: data["api_operations"][0].__setitem__(
                "later_ZM_FIN_tasks", ["ZM-FIN-999"]
            ),
            "invalid ZM-FIN reference",
        ),
        (
            lambda data: data["api_operations"][0].__setitem__(
                "evidence", ["does/not/exist.py#missing_symbol"]
            ),
            "missing evidence file",
        ),
        (
            lambda data: data["api_operations"][0].__setitem__(
                "evidence",
                ["apps/api/src/zeromerma_api/main.py#definitely_missing_symbol"],
            ),
            "missing evidence symbol",
        ),
        (
            lambda data: data["api_operations"][0].__setitem__("method", "TRACE"),
            "api_operations drift",
        ),
    ],
    ids=[
        "registered-api-omitted",
        "orphan-api-row",
        "pos-route-omitted",
        "backoffice-route-omitted",
        "duplicate-key",
        "required-field-blank",
        "unknown-state",
        "invalid-task-reference",
        "missing-evidence",
        "missing-evidence-symbol",
        "route-metadata-drift",
    ],
)
def test_validator_fails_closed(
    mutate: Callable[[dict[str, Any]], Any], expected_error: str
) -> None:
    data = copy.deepcopy(CANONICAL_MATRIX)
    mutate(data)

    errors = _errors(data)

    assert any(expected_error in error for error in errors), errors


def _first_partial(data: dict[str, Any]) -> dict[str, Any]:
    return next(
        row
        for section in (
            "api_operations",
            "pos_routes",
            "backoffice_routes",
            "worker_operations",
        )
        for row in data[section]
        if row["implementation_state"] == "PARTIAL"
    )


def _first_not_consumed(data: dict[str, Any]) -> dict[str, Any]:
    return next(
        row for row in data["api_operations"] if row["consumer_contract_state"] == "NOT_CONSUMED"
    )


def _first_direct_test(data: dict[str, Any]) -> dict[str, Any]:
    return next(
        row
        for section in ("api_operations", "pos_routes", "backoffice_routes")
        for row in data[section]
        if row["verification_state"] == "DIRECT_TEST_EXISTS_NOT_RUN"
    )


def _remove_partial_target(data: dict[str, Any]) -> None:
    _first_partial(data).pop("approved_target_state")


def _blank_partial_target(data: dict[str, Any]) -> None:
    _first_partial(data)["approved_target_state"] = "   "


def _generic_partial_target(data: dict[str, Any]) -> None:
    _first_partial(data)["approved_target_state"] = "IMPLEMENTED"


def _remove_consumer_disposition(data: dict[str, Any]) -> None:
    _first_not_consumed(data).pop("consumer_disposition")


def _remove_consumer_reason(data: dict[str, Any]) -> None:
    _first_not_consumed(data).pop("consumer_reason")


def _sentinel_consumer_reason(data: dict[str, Any]) -> None:
    row = _first_not_consumed(data)
    row["other_consumers"] = ["NONE"]
    row["consumer_reason"] = "NONE"


def _remove_missing_ui_gap(data: dict[str, Any]) -> None:
    row = _first_not_consumed(data)
    gap_catalog = {gap["gap_id"]: gap for gap in data["known_gaps"]}
    row["gap_ids"] = [
        gap_id
        for gap_id in row["gap_ids"]
        if gap_catalog[gap_id]["gap_type"] not in {"UI_DISCONNECTED", "CLIENT_CONTRACT_GAP"}
    ]


def _remove_missing_ui_task(data: dict[str, Any]) -> None:
    _first_not_consumed(data)["later_ZM_FIN_tasks"] = ["NOT_APPLICABLE"]


def _missing_direct_test_path(data: dict[str, Any]) -> None:
    _first_direct_test(data)["direct_tests"] = ["apps/api/tests/does_not_exist.py"]


def _missing_direct_test_symbol(data: dict[str, Any]) -> None:
    _first_direct_test(data)["direct_tests"] = [
        "apps/api/tests/conftest.py#definitely_missing_direct_test"
    ]


def _remove_direct_test_reference(data: dict[str, Any]) -> None:
    _first_direct_test(data)["direct_tests"] = ["NONE"]


def _missing_indirect_test_path(data: dict[str, Any]) -> None:
    data["api_operations"][0]["indirect_tests"] = ["apps/api/tests/does_not_exist_indirect.py"]


@pytest.mark.parametrize(
    ("mutate", "expected_error"),
    [
        (_remove_partial_target, "PARTIAL approved target invalid"),
        (_blank_partial_target, "PARTIAL approved target invalid"),
        (_generic_partial_target, "PARTIAL approved target invalid"),
        (_remove_consumer_disposition, "invalid consumer disposition"),
        (_remove_consumer_reason, "invalid consumer reason"),
        (_sentinel_consumer_reason, "invalid consumer reason"),
        (_remove_missing_ui_gap, "requires UI/client gap"),
        (_remove_missing_ui_task, "requires a later task"),
        (_missing_direct_test_path, "missing direct test reference file"),
        (_missing_direct_test_symbol, "missing direct test reference symbol"),
        (_remove_direct_test_reference, "has no valid direct test reference"),
        (_missing_indirect_test_path, "missing indirect test reference file"),
    ],
    ids=[
        "partial-target-missing",
        "partial-target-blank",
        "partial-target-generic",
        "not-consumed-disposition-missing",
        "not-consumed-reason-missing",
        "none-other-consumer-is-not-justification",
        "missing-local-ui-gap",
        "missing-local-ui-task",
        "direct-test-file-missing",
        "direct-test-symbol-missing",
        "direct-test-state-without-reference",
        "indirect-test-file-missing",
    ],
)
def test_semantic_validator_fails_closed(
    mutate: Callable[[dict[str, Any]], Any], expected_error: str
) -> None:
    data = copy.deepcopy(CANONICAL_MATRIX)
    mutate(data)

    errors = _errors(data)

    assert any(expected_error in error for error in errors), errors


def _api_only_by_design(data: dict[str, Any]) -> None:
    row = next(row for row in data["api_operations"] if not row["include_in_schema"])
    row["consumer_contract_state"] = "NOT_CONSUMED"
    row["consumer_disposition"] = "API_ONLY_BY_APPROVED_DESIGN"
    row["consumer_reason"] = (
        "The hidden development audit snapshot is excluded from the product contract and local UI."
    )
    data["module_summary"] = VALIDATOR.expected_module_summary(data)


def _identified_system_consumer(data: dict[str, Any]) -> None:
    row = next(row for row in data["api_operations"] if not row["include_in_schema"])
    row["consumer_contract_state"] = "NOT_CONSUMED"
    row["consumer_disposition"] = "EXTERNAL_OR_SYSTEM_CONSUMER"
    row["consumer_reason"] = "The registered worker poller is the identified system consumer."
    row["other_consumers"] = ["apps/worker/src/zeromerma_worker/outbox/poller.py#OutboxPoller"]
    data["module_summary"] = VALIDATOR.expected_module_summary(data)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: None,
        _api_only_by_design,
        _identified_system_consumer,
    ],
    ids=[
        "canonical-specific-targets-ui-gaps-and-no-test-state",
        "justified-api-only",
        "identified-system-consumer",
    ],
)
def test_semantic_positive_variants(mutate: Callable[[dict[str, Any]], Any]) -> None:
    data = copy.deepcopy(CANONICAL_MATRIX)
    mutate(data)

    assert _errors(data) == []
