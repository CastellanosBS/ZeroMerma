from __future__ import annotations

import copy
import importlib.util
import json
import sys
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Annotated, Any, cast

import pytest
from pydantic import Field, TypeAdapter

from zeromerma_api.presentation.contracts import normalize_contract_schema

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/dev/api-contracts.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("api_contracts_validator", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


VALIDATOR = _load()
SCHEMA = json.loads((ROOT / VALIDATOR.OPENAPI_PATH).read_text(encoding="utf-8"))
CLIENT = (ROOT / VALIDATOR.CLIENT_PATH).read_text(encoding="utf-8")
POLICY = json.loads((ROOT / VALIDATOR.POLICY_PATH).read_text(encoding="utf-8"))


def _validation_errors(schema: dict[str, Any], client: str = CLIENT) -> list[str]:
    errors, _ = VALIDATOR.validate_contract(schema, client, POLICY, ROOT)
    return cast(list[str], errors)


def _openapi_drift(schema: dict[str, Any]) -> list[str]:
    return cast(
        list[str],
        VALIDATOR.artifact_drift(
            {VALIDATOR.OPENAPI_PATH: VALIDATOR.canonical_json_bytes(schema)},
            ROOT,
        ),
    )


def _first_operation(schema: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    for path, path_item in schema["paths"].items():
        for method in VALIDATOR.HTTP_METHODS:
            if method in path_item:
                return path, method, path_item[method]
    raise AssertionError("expected an operation")


def _first_schema_node(predicate: Any) -> dict[str, Any]:
    return next(
        node
        for node in VALIDATOR._all_schema_nodes(SCHEMA["components"]["schemas"])
        if predicate(node)
    )


def test_path_omission_is_detected() -> None:
    changed = copy.deepcopy(SCHEMA)
    changed["paths"].pop(next(iter(changed["paths"])))
    assert _openapi_drift(changed)


def test_schema_change_is_detected() -> None:
    changed = copy.deepcopy(SCHEMA)
    changed["components"]["schemas"]["HealthResponse"]["properties"]["status"]["maxLength"] = 1
    assert _openapi_drift(changed)


def test_error_response_change_is_rejected() -> None:
    changed = copy.deepcopy(SCHEMA)
    _, _, operation = _first_operation(changed)
    operation["responses"].pop("409")
    assert any(
        "canonical 409 error response missing" in error for error in _validation_errors(changed)
    )


def test_uuid_format_removal_is_detected() -> None:
    changed = copy.deepcopy(SCHEMA)
    target = next(
        node
        for node in VALIDATOR._all_schema_nodes(changed["components"]["schemas"])
        if node.get("format") == "uuid"
    )
    target.pop("format")
    assert _openapi_drift(changed)


def test_decimal_representation_change_is_rejected() -> None:
    changed = copy.deepcopy(SCHEMA)
    target = next(
        node
        for node in VALIDATOR._all_schema_nodes(changed["components"]["schemas"])
        if node.get("pattern") == VALIDATOR.DECIMAL_PATTERN
    )
    target["type"] = "number"
    assert any("decimal schema" in error for error in _validation_errors(changed))


@pytest.mark.parametrize("scale", [None, 2, 3, 4])
def test_decimal_annotations_cover_actual_pydantic_constraint_patterns(scale: int | None) -> None:
    adapter = TypeAdapter(
        Annotated[
            Decimal, Field(max_digits=12 if scale is not None else None, decimal_places=scale)
        ]
    )
    source = adapter.json_schema()
    before = copy.deepcopy(source)
    normalized = normalize_contract_schema({"components": {"schemas": {"Amount": source}}})
    amount = normalized["components"]["schemas"]["Amount"]

    assert source == before
    assert amount["x-zeromerma-decimal-input-representation"] == "JSON_NUMBER_OR_STRING"
    string_branch = next(branch for branch in amount["anyOf"] if branch["type"] == "string")
    assert string_branch["x-zeromerma-decimal-representation"] == "JSON_STRING"
    assert string_branch["pattern"] == before["anyOf"][1]["pattern"]
    assert amount["anyOf"][0]["type"] == "number"


def test_constrained_decimal_annotation_drift_is_rejected() -> None:
    changed = normalize_contract_schema(SCHEMA)
    value = changed["components"]["schemas"]["AdminCommercialDiscountCreateRequest"]["properties"][
        "value"
    ]
    string_branch = next(branch for branch in value["anyOf"] if branch["type"] == "string")
    string_branch.pop("x-zeromerma-decimal-representation")

    assert any("decimal schema" in error for error in _validation_errors(changed))


def test_numeric_decimal_input_union_cannot_claim_string_only() -> None:
    changed = normalize_contract_schema(SCHEMA)
    value = changed["components"]["schemas"]["AdminCommercialDiscountCreateRequest"]["properties"][
        "value"
    ]
    value["x-zeromerma-decimal-input-representation"] = "JSON_STRING"

    assert any("decimal input union" in error for error in _validation_errors(changed))


def test_datetime_metadata_cannot_claim_runtime_utc_normalization() -> None:
    changed = normalize_contract_schema(SCHEMA)
    target = next(
        node
        for node in VALIDATOR._all_schema_nodes(changed["components"]["schemas"])
        if node.get("format") == "date-time"
    )
    target["x-zeromerma-instant-format"] = "RFC3339_UTC"

    assert any("date-time schema" in error for error in _validation_errors(changed))


def test_error_contract_rejects_restoring_a_compatibility_alias() -> None:
    changed = normalize_contract_schema(SCHEMA)
    changed["components"]["schemas"]["ApiErrorResponse"]["properties"]["detail"] = {
        "type": "string"
    }

    assert any("canonical fields without aliases" in error for error in _validation_errors(changed))


def test_error_contract_policy_cannot_allow_compatibility_aliases() -> None:
    policy = copy.deepcopy(POLICY)
    policy["error_contract"]["compatibility_aliases_allowed"] = True

    errors, _ = VALIDATOR.validate_contract(normalize_contract_schema(SCHEMA), CLIENT, policy, ROOT)

    assert any("canonical fields without aliases" in error for error in errors)


def test_operation_id_change_is_detected() -> None:
    changed = copy.deepcopy(SCHEMA)
    _, _, operation = _first_operation(changed)
    operation["operationId"] = "unstable_replacement"
    assert _openapi_drift(changed)


@pytest.mark.parametrize("suffix", ["stale generator output", "manual edit"])
def test_generated_client_change_is_detected(suffix: str) -> None:
    changed = (CLIENT + f"\n// {suffix}\n").encode()
    assert VALIDATOR.artifact_drift({VALIDATOR.CLIENT_PATH: changed}, ROOT)


def test_openapi_operation_without_generated_coverage_is_rejected() -> None:
    _, _, operation = _first_operation(SCHEMA)
    operation_id = operation["operationId"]
    changed_client = CLIENT.replace(f'operations["{operation_id}"]', "unknown", 1)
    assert any(
        "OpenAPI operations missing generated coverage" in error
        for error in _validation_errors(SCHEMA, changed_client)
    )


def test_feature_raw_http_and_manual_contract_source_are_rejected(tmp_path: Path) -> None:
    source = tmp_path / "apps/pos-web/src/features/example/api.ts"
    source.parent.mkdir(parents=True)
    source.write_text(
        "interface ManualResponse { id: string }\n"
        "export const load = () => fetch('/v1/example');\n"
        "export const typed = () => requestJson<ManualResponse>({ path: '/v1/example' });\n",
        encoding="utf-8",
    )

    raw_http, manual_types = VALIDATOR._frontend_contract_audit(tmp_path)

    assert raw_http == ["apps/pos-web/src/features/example/api.ts"]
    assert manual_types == ["apps/pos-web/src/features/example/api.ts"]


def test_exact_collection_policy_rejects_unknown_collection() -> None:
    changed = copy.deepcopy(SCHEMA)
    path, _, operation = _first_operation(changed)
    operation["operationId"] = "list_unclassified_contract_rows"
    changed["paths"][path]["get"] = changed["paths"][path].pop("get", operation)
    errors = _validation_errors(changed)
    assert any("unclassified collection operations" in error for error in errors)


def test_collection_policy_covers_pagination_bounds_filters_and_order() -> None:
    entries = POLICY["collections"]["operations"]
    classifications = {entry["classification"] for entry in entries.values()}

    assert len(entries) == 57
    assert classifications == {
        "PAGINATION_REQUIRED",
        "BOUNDED_REFERENCE_LIST",
        "BOUNDED_OPERATIONAL_WINDOW",
        "EXPLICIT_COMPLETE_EXPORT",
    }
    assert all(
        entry["query_parameters"] == sorted(entry["query_parameters"]) for entry in entries.values()
    )
    assert all(
        entry["stable_order"] and entry["bound"] and entry["evidence"] for entry in entries.values()
    )
    assert _validation_errors(SCHEMA) == []


def test_transfer_operational_windows_apply_the_versioned_bound_and_tie_break() -> None:
    source = (
        ROOT / "apps/api/src/zeromerma_api/modules/transfers/application/services.py"
    ).read_text(encoding="utf-8")

    assert source.count(".limit(MAX_TRANSFER_HISTORY_ITEMS)") == 3
    assert "OperationDocument.id.asc()" in source
    assert source.count("OperationDocument.id.desc()") == 2
