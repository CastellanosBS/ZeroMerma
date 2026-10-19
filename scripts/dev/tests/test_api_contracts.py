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


def test_idempotency_foundation_exposes_reusable_backend_contract_without_claiming_adoption() -> (
    None
):
    normalized = normalize_contract_schema(SCHEMA)
    components = normalized["components"]
    key = components["schemas"]["IdempotencyKey"]
    assert key["format"] == "uuid" and key["x-zeromerma-uuid-version"] == 7
    assert key["minLength"] == key["maxLength"] == 36
    assert "7[0-9a-fA-F]{3}" in key["pattern"]
    assert components["parameters"]["IdempotencyKey"] == {
        "name": "Idempotency-Key",
        "in": "header",
        "required": True,
        "description": "Reuse only for the same operation, actor, context and canonical payload.",
        "schema": {"$ref": "#/components/schemas/IdempotencyKey"},
    }
    assert components["schemas"]["IdempotencyStatus"]["enum"] == [
        "PROCESSING",
        "COMPLETED",
        "REJECTED",
        "UNKNOWN",
    ]
    assert normalized["x-zeromerma-idempotency"]["request_id_is_idempotency_key"] is False
    assert normalized["x-zeromerma-idempotency"]["adoption"] == "PER_OPERATION"
    assert normalized["paths"] == SCHEMA["paths"]
    assert "request_id" not in components["schemas"]["IdempotencyRejectionSnapshot"]["properties"]


def test_schema_change_is_detected() -> None:
    changed = copy.deepcopy(SCHEMA)
    changed["components"]["schemas"]["HealthResponse"]["properties"]["status"]["maxLength"] = 1
    assert _openapi_drift(changed)


def test_sale_confirmation_adopts_key_and_exposes_metadata_only_recovery() -> None:
    operation = SCHEMA["paths"]["/v1/sales/confirm"]["post"]
    key = next(item for item in operation["parameters"] if item["name"] == "Idempotency-Key")
    assert key["in"] == "header" and key["required"] is True
    assert "7[0-9a-fA-F]{3}" in key["schema"]["pattern"]
    schemas = SCHEMA["components"]["schemas"]
    assert "cash_session_id" in schemas["ConfirmSaleRequest"]["required"]
    confirmation = schemas["SaleConfirmationView"]
    assert confirmation["additionalProperties"] is False
    assert "operator_email" not in confirmation["properties"]
    assert "operator_full_name" not in confirmation["properties"]
    assert operation["responses"]["201"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/SaleConfirmationView"
    }
    assert operation["responses"]["201"]["headers"]["Idempotency-Replayed"] == {
        "$ref": "#/components/headers/IdempotencyReplayed"
    }
    recovery = SCHEMA["paths"]["/v1/sales/confirmations/{idempotency_key}"]["get"]
    assert "requestBody" not in recovery
    assert {item["name"] for item in recovery["parameters"] if item["required"]} == {
        "idempotency_key",
        "workstation_code",
        "cash_session_id",
    }
    assert recovery["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/SaleConfirmationView"
    }
    assert recovery["responses"]["200"]["headers"]["Idempotency-Replayed"] == {
        "$ref": "#/components/headers/IdempotencyReplayed"
    }


@pytest.mark.parametrize(
    ("path", "request_schema", "status"),
    [
        ("/v1/orders", "CreateCustomerOrderRequest", "201"),
        ("/v1/orders/{order_id}/mark-ready", "OrderActionRequest", "200"),
        ("/v1/orders/{order_id}/deliver", "DeliverCustomerOrderRequest", "200"),
        ("/v1/orders/{order_id}/cancel", "CancelCustomerOrderRequest", "200"),
        ("/v1/admin/orders/{order_id}/mark-ready", "AdminOrderActionRequest", "200"),
        ("/v1/admin/orders/{order_id}/deliver", "AdminOrderActionRequest", "200"),
        ("/v1/admin/orders/{order_id}/cancel", "AdminOrderActionRequest", "200"),
    ],
)
def test_order_commands_require_one_identity_and_return_safe_receipts(
    path: str, request_schema: str, status: str
) -> None:
    operation = SCHEMA["paths"][path]["post"]
    key = next(item for item in operation["parameters"] if item["name"] == "Idempotency-Key")
    assert key["in"] == "header" and key["required"] is True
    assert "7[0-9a-fA-F]{3}" in key["schema"]["pattern"]
    schemas = SCHEMA["components"]["schemas"]
    request = schemas[request_schema]
    if path.startswith("/v1/orders"):
        assert "cash_session_id" in request["required"]
    else:
        assert request["properties"] == {} and request["additionalProperties"] is False
    receipt = schemas["OrderCommandResultView"]
    assert receipt["additionalProperties"] is False
    assert (
        not {
            "customer_name",
            "customer_phone",
            "notes",
            "cancellation_reason",
            "operator_full_name",
            "operator_email",
            "can_deliver",
            "can_cancel",
        }
        & receipt["properties"].keys()
    )
    assert (
        not {
            "operator_full_name",
            "operator_email",
            "notes",
        }
        & schemas["OrderCommandPaymentView"]["properties"].keys()
    )
    response = operation["responses"][status]
    assert response["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/OrderCommandResultView"
    }
    assert response["headers"]["Idempotency-Replayed"] == {
        "$ref": "#/components/headers/IdempotencyReplayed"
    }


@pytest.mark.parametrize(
    ("path", "context"),
    [
        (
            "/v1/orders/commands/{command_code}/{idempotency_key}",
            {"workstation_code", "cash_session_id"},
        ),
        ("/v1/admin/orders/commands/{command_code}/{idempotency_key}", {"branch_id"}),
    ],
)
def test_order_recovery_requires_metadata_without_economic_payload(
    path: str, context: set[str]
) -> None:
    recovery = SCHEMA["paths"][path]["get"]
    assert "requestBody" not in recovery
    assert {item["name"] for item in recovery["parameters"] if item["required"]} == {
        "command_code",
        "idempotency_key",
        *context,
    }
    assert "order_id" not in {item["name"] for item in recovery["parameters"]}
    response = recovery["responses"]["200"]
    assert response["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/OrderCommandResultView"
    }
    assert response["headers"]["Idempotency-Replayed"] == {
        "$ref": "#/components/headers/IdempotencyReplayed"
    }


def test_return_command_requires_identity_and_keeps_private_data_out_of_receipt() -> None:
    operation = SCHEMA["paths"]["/v1/returns/commit"]["post"]
    key = next(item for item in operation["parameters"] if item["name"] == "Idempotency-Key")
    assert key["in"] == "header" and key["required"] is True
    assert "7[0-9a-fA-F]{3}" in key["schema"]["pattern"]
    schemas = SCHEMA["components"]["schemas"]
    assert "cash_session_id" in schemas["ReturnCommitRequest"]["required"]
    for name in ("ReturnCommitResultView", "ReturnCommitLineResultView"):
        receipt = schemas[name]
        assert receipt["additionalProperties"] is False
        assert (
            not {
                "notes",
                "created_by",
                "operator_email",
                "operator_full_name",
                "reason_code",
                "reason_name",
                "audit_summary",
                "returned_product_name_snapshot",
            }
            & receipt["properties"].keys()
        )
    assert "refund_cash_movement_id" in schemas["ReturnCommitResultView"]["required"]
    response = operation["responses"]["201"]
    assert response["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ReturnCommitResultView"
    }
    assert response["headers"]["Idempotency-Replayed"] == {
        "$ref": "#/components/headers/IdempotencyReplayed"
    }


def test_return_recovery_uses_only_identity_and_historical_cash_context() -> None:
    recovery = SCHEMA["paths"]["/v1/returns/confirmations/{idempotency_key}"]["get"]
    assert "requestBody" not in recovery
    assert {item["name"] for item in recovery["parameters"] if item["required"]} == {
        "idempotency_key",
        "workstation_code",
        "cash_session_id",
    }
    response = recovery["responses"]["200"]
    assert response["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ReturnCommitResultView"
    }
    assert response["headers"]["Idempotency-Replayed"] == {
        "$ref": "#/components/headers/IdempotencyReplayed"
    }
    schemas = SCHEMA["components"]["schemas"]
    assert {"already_refunded_amount", "remaining_refundable_amount"} <= set(
        schemas["ReturnableSaleLineView"]["required"]
    )


@pytest.mark.parametrize(
    ("prefix", "suffix", "request_name", "result_name", "status"),
    [
        ("cash-sessions", "/open", "OpenCashSessionRequest", "CashSessionOpenResultView", "201"),
        (
            "payments",
            "",
            "CreateOperationalPaymentRequest",
            "OperationalPaymentCommitResultView",
            "201",
        ),
        (
            "discounts",
            "",
            "CreateOperationalDiscountRequest",
            "OperationalDiscountCommitResultView",
            "201",
        ),
        ("cash-close", "/commit", "CashCloseCommitRequest", "CashCloseCommitResultView", "200"),
    ],
)
def test_cash_commands_publish_identity_context_and_minimal_recoverable_results(
    prefix: str,
    suffix: str,
    request_name: str,
    result_name: str,
    status: str,
) -> None:
    schemas = SCHEMA["components"]["schemas"]
    operation = SCHEMA["paths"][f"/v1/{prefix}{suffix}"]["post"]
    key = next(item for item in operation["parameters"] if item["name"] == "Idempotency-Key")
    assert key["in"] == "header" and key["required"] is True
    assert "7[0-9a-fA-F]{3}" in key["schema"]["pattern"]
    request = schemas[request_name]
    assert "workstation_code" in request["required"]
    if prefix != "cash-sessions":
        assert "cash_session_id" in request["required"]
    receipt = schemas[result_name]
    assert receipt["additionalProperties"] is False
    assert (
        not {
            "notes",
            "payee_name",
            "subject_name",
            "concept",
            "user_email",
            "user_full_name",
            "created_by",
            "audit_summary",
            "can_commit",
        }
        & receipt["properties"].keys()
    )
    response = operation["responses"][status]
    assert response["content"]["application/json"]["schema"] == {
        "$ref": f"#/components/schemas/{result_name}"
    }
    assert response["headers"]["Idempotency-Replayed"] == {
        "$ref": "#/components/headers/IdempotencyReplayed"
    }
    recovery = SCHEMA["paths"][f"/v1/{prefix}/confirmations/{{idempotency_key}}"]["get"]
    assert "requestBody" not in recovery
    parameters = {item["name"] for item in recovery["parameters"] if item["required"]}
    assert parameters == (
        {"idempotency_key", "workstation_code"}
        | ({"cash_session_id"} if prefix != "cash-sessions" else set())
    )
    assert recovery["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": f"#/components/schemas/{result_name}"
    }


def test_cash_preview_remains_read_only_and_separate_from_commit_contract() -> None:
    operation = SCHEMA["paths"]["/v1/cash-close/preview"]["post"]
    assert not any(item["name"] == "Idempotency-Key" for item in operation.get("parameters", []))
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/CashClosePreviewRequest"
    }


REMAINING_IDEMPOTENT_COMMANDS = [
    ("post", "/v1/transfers/dispatch/commit", "TransferCommandResultView"),
    ("post", "/v1/transfers/{transfer_id}/receive", "TransferCommandResultView"),
    ("post", "/v1/admin/transfers", "TransferCommandResultView"),
    ("patch", "/v1/admin/transfers/{transfer_id}", "TransferCommandResultView"),
    *[
        ("post", f"/v1/admin/transfers/{{transfer_id}}/{action}", "TransferCommandResultView")
        for action in ("dispatch", "receive", "cancel")
    ],
    ("post", "/v1/admin/purchases", "PurchaseCommandResultView"),
    ("patch", "/v1/admin/purchases/{purchase_id}", "PurchaseCommandResultView"),
    ("post", "/v1/admin/purchases/direct-entry", "PurchaseCommandResultView"),
    *[
        ("post", f"/v1/admin/purchases/{{purchase_id}}/{action}", "PurchaseCommandResultView")
        for action in ("confirm", "receive", "cancel")
    ],
    ("post", "/v1/operations/counter-transfer/commit", "OperationCommitResultView"),
    ("post", "/v1/operations/waste/commit", "OperationCommitResultView"),
    ("post", "/v1/corrections/commit", "CorrectionCommitResultView"),
    ("post", "/v1/admin/waste", "OperationCommitResultView"),
    ("post", "/v1/admin/inventory/adjustments", "AdminInventoryAdjustmentResultView"),
    ("post", "/v1/admin/production", "ProductionCommandResultView"),
    ("patch", "/v1/admin/production/{production_id}", "ProductionCommandResultView"),
    *[
        ("post", f"/v1/admin/production/{{production_id}}/{action}", "ProductionCommandResultView")
        for action in ("start", "complete", "cancel")
    ],
]


@pytest.mark.parametrize(("method", "path", "result_name"), REMAINING_IDEMPOTENT_COMMANDS)
def test_operational_commands_publish_required_key_and_minimized_acknowledgement(
    method: str,
    path: str,
    result_name: str,
) -> None:
    operation = SCHEMA["paths"][path][method]
    keys = [item for item in operation["parameters"] if item["name"] == "Idempotency-Key"]
    assert len(keys) == 1 and keys[0]["required"] and keys[0]["in"] == "header"
    assert "7[0-9a-fA-F]{3}" in keys[0]["schema"]["pattern"]
    response = next(
        value for code, value in operation["responses"].items() if code in {"200", "201"}
    )
    assert response["content"]["application/json"]["schema"] == {
        "$ref": f"#/components/schemas/{result_name}"
    }
    assert "Idempotency-Replayed" in response["headers"]
    assert operation["responses"]["409"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ApiErrorResponse"
    }
    schema = SCHEMA["components"]["schemas"][result_name]
    assert schema["additionalProperties"] is False
    assert not {
        "notes",
        "reason",
        "operator_name",
        "supplier_name",
        "customer_name",
        "available_actions",
    }.intersection(schema["properties"])
    if not path.startswith("/v1/admin/"):
        request = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].split(
            "/"
        )[-1]
        assert "cash_session_id" in SCHEMA["components"]["schemas"][request]["required"]


@pytest.mark.parametrize(
    "path",
    [
        "/v1/transfers/commands/{command_code}/confirmations/{idempotency_key}",
        "/v1/admin/transfers/commands/{command_code}/confirmations/{idempotency_key}",
        "/v1/admin/purchases/commands/{command_code}/{idempotency_key}",
        "/v1/admin/production/commands/{command_code}/{idempotency_key}",
        "/v1/corrections/confirmations/{idempotency_key}",
        "/v1/operations/counter-transfer/confirmations/{idempotency_key}",
        "/v1/operations/waste/confirmations/{idempotency_key}",
        "/v1/admin/waste/confirmations/{idempotency_key}",
        "/v1/admin/inventory/adjustments/confirmations/{idempotency_key}",
    ],
)
def test_operational_recovery_is_a_contextual_read_without_new_intention(path: str) -> None:
    operation = SCHEMA["paths"][path]["get"]
    assert "requestBody" not in operation
    names = {
        parameter["name"] for parameter in operation["parameters"] if parameter.get("required")
    }
    assert "idempotency_key" in names and "Idempotency-Key" not in names
    assert (
        {"branch_id"} if path.startswith("/v1/admin/") else {"workstation_code", "cash_session_id"}
    ).issubset(names)
    assert "Idempotency-Replayed" in operation["responses"]["200"]["headers"]


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

    assert len(entries) == 59
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
