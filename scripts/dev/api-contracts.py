#!/usr/bin/env python3
"""Generate and validate the canonical ZeroMerma HTTP contract artifacts."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from zeromerma_api.presentation.contracts import (
    DECIMAL_PATTERN,
    is_decimal_input_union,
    is_decimal_schema,
)

ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = Path("packages/api-client/openapi.json")
CLIENT_PATH = Path("packages/api-client/src/generated/schema.ts")
INVENTORY_PATH = Path("docs/architecture/API_CONTRACT_INVENTORY.json")
POLICY_PATH = Path("docs/architecture/API_CONTRACT_POLICY.json")
MATRIX_PATH = Path("docs/architecture/FUNCTIONAL_OPERATION_MATRIX.json")
ERROR_STATUSES = ("400", "401", "403", "404", "409", "422", "500")
HTTP_METHODS = ("delete", "get", "head", "options", "patch", "post", "put", "trace")
OPERATION_REFERENCE = re.compile(r'operations\["([^"]+)"\]')
FETCH_CALL = re.compile(r"\bfetch\s*\(")
REQUEST_JSON_CALL = re.compile(r"\brequestJson\s*<")


@dataclass(frozen=True)
class Operation:
    method: str
    path: str
    operation_id: str
    definition: dict[str, Any]

    @property
    def key(self) -> str:
        return f"API:{self.method.upper()}:{self.path}"


@dataclass(frozen=True)
class ContractMetrics:
    operation_count: int
    unique_operation_ids: int
    generated_client_coverage: int
    generated_client_orphans: int
    collection_operations: int
    unclassified_collections: int
    unbounded_growing_collections: int
    decimal_schema_nodes: int
    constrained_decimal_schema_nodes: int
    decimal_input_union_schema_nodes: int
    uuid_schema_nodes: int
    datetime_schema_nodes: int
    enum_schema_nodes: int
    nullable_schema_nodes: int
    raw_http_baseline: int
    unjustified_raw_http: int
    unjustified_manual_contract_types: int


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def runtime_openapi() -> dict[str, Any]:
    source_root = ROOT / "apps/api/src"
    source = str(source_root)
    if source not in sys.path:
        sys.path.insert(0, source)
    module = importlib.import_module("zeromerma_api.main")
    app = module.create_app()
    schema = app.openapi()
    if not isinstance(schema, dict):
        raise TypeError("FastAPI returned a non-object OpenAPI document")
    return schema


def operations(schema: Mapping[str, Any]) -> list[Operation]:
    result: list[Operation] = []
    for path in sorted(schema.get("paths", {})):
        path_item = schema["paths"][path]
        for method in HTTP_METHODS:
            definition = path_item.get(method)
            if not isinstance(definition, dict):
                continue
            operation_id = definition.get("operationId")
            result.append(
                Operation(
                    method=method,
                    path=path,
                    operation_id=str(operation_id or ""),
                    definition=definition,
                )
            )
    return result


def _response_schema(operation: Operation, success: bool) -> list[Any]:
    matches: list[Any] = []
    for status, response in sorted(operation.definition.get("responses", {}).items()):
        is_success = str(status).startswith("2")
        if is_success != success or not isinstance(response, dict):
            continue
        content = response.get("content", {}).get("application/json", {})
        matches.append({"status": str(status), "schema": content.get("schema")})
    return matches


def _request_contract(operation: Operation) -> dict[str, Any]:
    parameters = []
    for parameter in operation.definition.get("parameters", []):
        if not isinstance(parameter, dict):
            continue
        parameters.append(
            {
                "in": parameter.get("in"),
                "name": parameter.get("name"),
                "required": bool(parameter.get("required")),
                "schema": parameter.get("schema"),
            }
        )
    request_body = operation.definition.get("requestBody")
    body_schema = None
    if isinstance(request_body, dict):
        body_schema = request_body.get("content", {}).get("application/json", {}).get("schema")
    return {"parameters": parameters, "body_schema": body_schema}


def _schema_signals(value: Any, path: str = "$") -> dict[str, list[str]]:
    result: dict[str, list[str]] = {
        "decimal_fields": [],
        "id_fields": [],
        "datetime_fields": [],
        "enum_fields": [],
        "nullable_fields": [],
    }

    def visit(child: Any, child_path: str) -> None:
        if isinstance(child, dict):
            if is_decimal_schema(child):
                result["decimal_fields"].append(child_path)
            if child.get("format") == "uuid":
                result["id_fields"].append(child_path)
            if child.get("format") in {"date", "date-time", "time"}:
                result["datetime_fields"].append(child_path)
            if isinstance(child.get("enum"), list):
                result["enum_fields"].append(child_path)
            if any(
                isinstance(item, dict) and item.get("type") == "null"
                for item in child.get("anyOf", [])
            ):
                result["nullable_fields"].append(child_path)
            for key, item in child.items():
                visit(item, f"{child_path}.{key}")
        elif isinstance(child, list):
            for index, item in enumerate(child):
                visit(item, f"{child_path}[{index}]")

    visit(value, path)
    return {key: sorted(set(paths)) for key, paths in result.items()}


def _is_collection_operation(operation: Operation) -> bool:
    operation_id = operation.operation_id
    if operation.method != "get":
        return False
    if "detail" in operation_id and operation.path.rstrip("/").endswith("}"):
        return False
    return operation_id.startswith(("list_", "search_", "export_")) or any(
        marker in operation.path
        for marker in ("/catalog", "/history", "/templates", "/pending", "/classes/")
    )


def collection_operation_ids(schema: Mapping[str, Any]) -> set[str]:
    return {
        operation.operation_id
        for operation in operations(schema)
        if _is_collection_operation(operation)
    }


def _query_parameters(operation: Operation) -> list[str]:
    return sorted(
        str(parameter.get("name"))
        for parameter in operation.definition.get("parameters", [])
        if isinstance(parameter, dict) and parameter.get("in") == "query"
    )


def _frontend_contract_audit(root: Path) -> tuple[list[str], list[str]]:
    unjustified_fetch: list[str] = []
    unjustified_manual: list[str] = []
    allowed_fetch = {Path("packages/api-client/src/transport.ts")}
    source_roots = (
        root / "apps/pos-web/src",
        root / "apps/backoffice-web/src",
        root / "packages/api-client/src",
    )
    for source_root in source_roots:
        if not source_root.exists():
            continue
        for path in sorted((*source_root.rglob("*.ts"), *source_root.rglob("*.tsx"))):
            relative = path.relative_to(root)
            text = path.read_text(encoding="utf-8")
            if (
                ".test." not in path.name
                and FETCH_CALL.search(text)
                and relative not in allowed_fetch
            ):
                unjustified_fetch.append(str(relative).replace("\\", "/"))
            if REQUEST_JSON_CALL.search(text) and relative not in allowed_fetch:
                if "@zeromerma/api-client" not in text and "api-contracts" not in text:
                    unjustified_manual.append(str(relative).replace("\\", "/"))
    return unjustified_fetch, unjustified_manual


def _matrix_rows(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    matrix = load_json(root / MATRIX_PATH)
    rows = {str(row["operation_key"]): row for row in matrix.get("api_operations", [])}
    gap_types = {str(gap["gap_id"]): str(gap["gap_type"]) for gap in matrix.get("known_gaps", [])}
    return rows, gap_types


def build_inventory(
    schema: Mapping[str, Any],
    policy: Mapping[str, Any],
    root: Path = ROOT,
) -> dict[str, Any]:
    rows, gap_types = _matrix_rows(root)
    collection_policy = policy["collections"]["operations"]
    records: list[dict[str, Any]] = []
    for operation in operations(schema):
        request = _request_contract(operation)
        success = _response_schema(operation, success=True)
        signals = _schema_signals({"request": request, "success": success})
        row = rows.get(operation.key, {})
        collection = collection_policy.get(operation.operation_id)
        records.append(
            {
                "operation_key": operation.key,
                "method": operation.method.upper(),
                "path": operation.path,
                "operation_id": operation.operation_id,
                "operation_id_source": operation.definition.get("x-zeromerma-operation-id-policy"),
                "request_schema": request,
                "success_response_schema": success,
                "declared_error_responses": sorted(
                    status
                    for status in operation.definition.get("responses", {})
                    if str(status).startswith(("4", "5"))
                ),
                "pagination_class": (
                    collection["classification"] if collection else "NOT_APPLICABLE"
                ),
                "expected_growth": collection["expected_growth"]
                if collection
                else "NOT_APPLICABLE",
                "filter_class": _query_parameters(operation) if collection else [],
                "stable_order": collection["stable_order"] if collection else "NOT_APPLICABLE",
                **signals,
                "generated_client_symbol": operation.operation_id,
                "frontend_consumers": sorted(
                    {
                        reference
                        for field in ("pos_consumers", "backoffice_consumers", "other_consumers")
                        for reference in row.get(field, [])
                        if reference != "NONE"
                    }
                ),
                "consumer_contract_state": row.get("consumer_contract_state", "NOT_CONSUMED"),
                "contract_gap": sorted(
                    {
                        gap_types[gap_id]
                        for gap_id in row.get("gap_ids", [])
                        if gap_id in gap_types and "CONTRACT" in gap_types[gap_id]
                    }
                ),
            }
        )
    return {
        "schema_version": "1.0.0",
        "application_baseline_commit": policy["application_baseline_commit"],
        "source": "FastAPI runtime OpenAPI plus versioned contract policy and ZM-FIN-008 matrix",
        "operation_count": len(records),
        "operations": records,
    }


def _all_schema_nodes(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _all_schema_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_schema_nodes(child)


def generated_client_operation_ids(client: str) -> set[str]:
    return set(OPERATION_REFERENCE.findall(client))


def validate_contract(
    schema: Mapping[str, Any],
    client: str,
    policy: Mapping[str, Any],
    root: Path = ROOT,
) -> tuple[list[str], ContractMetrics]:
    errors: list[str] = []
    api_operations = operations(schema)
    operation_ids = [operation.operation_id for operation in api_operations]
    if any(not operation_id for operation_id in operation_ids):
        errors.append("every OpenAPI operation must declare operationId")
    duplicate_ids = sorted(
        operation_id for operation_id, count in Counter(operation_ids).items() if count > 1
    )
    if duplicate_ids:
        errors.append(f"duplicate operationId values: {', '.join(duplicate_ids)}")
    if "/dev/audit/snapshot" in schema.get("paths", {}):
        errors.append("hidden development audit route is exposed in OpenAPI")
    if schema.get("x-zeromerma-contract-schema-version") != policy.get("schema_version"):
        errors.append("OpenAPI contract schema version does not match policy")
    error_policy = policy.get("error_contract", {})
    error_schema = schema.get("components", {}).get("schemas", {}).get("ApiErrorResponse", {})
    canonical_error_fields = set(error_policy.get("required_fields", []))
    if (
        error_policy.get("compatibility_aliases_allowed") is not False
        or set(error_schema.get("properties", {})) != canonical_error_fields
        or set(error_schema.get("required", [])) != canonical_error_fields
        or error_schema.get("additionalProperties") is not False
    ):
        errors.append("error schema must contain exactly the canonical fields without aliases")

    for operation in api_operations:
        if (
            operation.definition.get("x-zeromerma-operation-id-policy")
            != "FASTAPI_STABLE_GENERATED"
        ):
            errors.append(f"operationId policy missing: {operation.key}")
        responses = operation.definition.get("responses", {})
        for status in ERROR_STATUSES:
            response_schema = (
                responses.get(status, {})
                .get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            if response_schema.get("$ref") != "#/components/schemas/ApiErrorResponse":
                errors.append(f"canonical {status} error response missing: {operation.key}")

    nodes = list(_all_schema_nodes(schema.get("components", {}).get("schemas", {})))
    decimal_nodes = [node for node in nodes if is_decimal_schema(node)]
    decimal_input_unions = [node for node in nodes if is_decimal_input_union(node)]
    uuid_nodes = [node for node in nodes if node.get("format") == "uuid"]
    datetime_nodes = [node for node in nodes if node.get("format") == "date-time"]
    enum_nodes = [node for node in nodes if isinstance(node.get("enum"), list)]
    nullable_nodes = [
        node
        for node in nodes
        if any(
            isinstance(item, dict) and item.get("type") == "null" for item in node.get("anyOf", [])
        )
    ]
    if any(
        node.get("type") != "string"
        or node.get("x-zeromerma-decimal-representation") != "JSON_STRING"
        for node in decimal_nodes
    ):
        errors.append("decimal schema is not lossless JSON string")
    if any(
        node.get("x-zeromerma-decimal-input-representation") != "JSON_NUMBER_OR_STRING"
        for node in decimal_input_unions
    ):
        errors.append("decimal input union lacks the actual JSON number-or-string contract")
    if any(
        node.get("type") != "string" or node.get("x-zeromerma-id-representation") != "JSON_STRING"
        for node in uuid_nodes
    ):
        errors.append("UUID schema is not a formatted JSON string")
    if any(node.get("x-zeromerma-instant-format") != "ISO8601_DATETIME" for node in datetime_nodes):
        errors.append("date-time schema lacks the explicit ISO 8601 representation contract")
    if any(not node["enum"] for node in enum_nodes):
        errors.append("empty enum exposed in OpenAPI")

    actual_collections = collection_operation_ids(schema)
    declared_collections = set(policy.get("collections", {}).get("operations", {}))
    missing_collections = sorted(actual_collections - declared_collections)
    orphan_collections = sorted(declared_collections - actual_collections)
    if missing_collections:
        errors.append(f"unclassified collection operations: {', '.join(missing_collections)}")
    if orphan_collections:
        errors.append(f"orphan collection policies: {', '.join(orphan_collections)}")
    unbounded = 0
    operation_by_id = {operation.operation_id: operation for operation in api_operations}
    for operation_id, entry in policy.get("collections", {}).get("operations", {}).items():
        classification = entry.get("classification")
        if classification not in {
            "PAGINATION_REQUIRED",
            "BOUNDED_REFERENCE_LIST",
            "BOUNDED_OPERATIONAL_WINDOW",
            "EXPLICIT_COMPLETE_EXPORT",
        }:
            errors.append(f"invalid collection classification: {operation_id}")
            continue
        for field in ("expected_growth", "stable_order", "reason", "evidence"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                errors.append(f"collection policy missing {field}: {operation_id}")
        declared_operation = operation_by_id.get(operation_id)
        if declared_operation is None:
            continue
        query = set(_query_parameters(declared_operation))
        declared_query = entry.get("query_parameters")
        if declared_query != sorted(query):
            errors.append(
                f"collection query parameter drift: {operation_id} "
                f"policy={declared_query!r} actual={sorted(query)!r}"
            )
        if classification == "PAGINATION_REQUIRED" and not {"page", "page_size"} <= query:
            errors.append(f"paginated collection lacks page/page_size: {operation_id}")
            unbounded += 1
        if classification == "PAGINATION_REQUIRED":
            page_size = next(
                (
                    parameter
                    for parameter in declared_operation.definition.get("parameters", [])
                    if isinstance(parameter, dict) and parameter.get("name") == "page_size"
                ),
                {},
            )
            page_size_schema = page_size.get("schema", {})
            if page_size_schema.get("default") != 25 or page_size_schema.get("maximum") != 100:
                errors.append(f"unexpected page_size policy: {operation_id}")
        if classification == "BOUNDED_REFERENCE_LIST" and entry.get("bound") in {None, "", "NONE"}:
            errors.append(f"bounded reference collection lacks bound: {operation_id}")
            unbounded += 1
        if classification == "BOUNDED_OPERATIONAL_WINDOW" and entry.get("bound") in {
            None,
            "",
            "NONE",
        }:
            errors.append(f"bounded operational collection lacks bound: {operation_id}")
            unbounded += 1

    generated_ids = generated_client_operation_ids(client)
    api_ids = set(operation_ids)
    missing_generated = sorted(api_ids - generated_ids)
    orphan_generated = sorted(generated_ids - api_ids)
    if missing_generated:
        errors.append(
            f"OpenAPI operations missing generated coverage: {', '.join(missing_generated)}"
        )
    if orphan_generated:
        errors.append(f"orphan generated operations: {', '.join(orphan_generated)}")
    unjustified_fetch, unjustified_manual = _frontend_contract_audit(root)
    if unjustified_fetch:
        errors.append(f"unjustified feature-level raw HTTP: {', '.join(unjustified_fetch)}")
    if unjustified_manual:
        errors.append(f"unjustified manual API contract types: {', '.join(unjustified_manual)}")

    raw_http_baseline = int(policy.get("frontend", {}).get("raw_http_baseline_count", -1))
    metrics = ContractMetrics(
        operation_count=len(api_operations),
        unique_operation_ids=len(set(operation_ids)),
        generated_client_coverage=len(api_ids & generated_ids),
        generated_client_orphans=len(orphan_generated),
        collection_operations=len(actual_collections),
        unclassified_collections=len(missing_collections),
        unbounded_growing_collections=unbounded,
        decimal_schema_nodes=len(decimal_nodes),
        constrained_decimal_schema_nodes=sum(
            node.get("pattern") != DECIMAL_PATTERN for node in decimal_nodes
        ),
        decimal_input_union_schema_nodes=len(decimal_input_unions),
        uuid_schema_nodes=len(uuid_nodes),
        datetime_schema_nodes=len(datetime_nodes),
        enum_schema_nodes=len(enum_nodes),
        nullable_schema_nodes=len(nullable_nodes),
        raw_http_baseline=raw_http_baseline,
        unjustified_raw_http=len(unjustified_fetch),
        unjustified_manual_contract_types=len(unjustified_manual),
    )
    return errors, metrics


def _corepack() -> str:
    executable = shutil.which("corepack") or shutil.which("corepack.cmd")
    if executable is None:
        raise RuntimeError("Corepack is required to generate the TypeScript contract")
    return executable


def generate_client(openapi_path: Path, output_path: Path, root: Path = ROOT) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        _corepack(),
        "pnpm",
        "--filter",
        "@zeromerma/api-client",
        "exec",
        "openapi-typescript",
        str(openapi_path.resolve()),
        "--output",
        str(output_path.resolve()),
    ]
    subprocess.run(command, cwd=root, check=True)


def generator_version(root: Path = ROOT) -> str:
    command = [
        _corepack(),
        "pnpm",
        "--filter",
        "@zeromerma/api-client",
        "exec",
        "openapi-typescript",
        "--version",
    ]
    result = subprocess.run(command, cwd=root, check=True, capture_output=True, text=True)
    return result.stdout.strip().removeprefix("v")


def _generated_artifacts(temp_root: Path) -> tuple[dict[Path, bytes], ContractMetrics]:
    policy = load_json(ROOT / POLICY_PATH)
    expected_generator = str(policy.get("generator", {}).get("lockfile_resolved_version", ""))
    actual_generator = generator_version()
    if actual_generator != expected_generator:
        raise RuntimeError(
            "contract generator version drift: "
            f"expected={expected_generator} actual={actual_generator}"
        )
    schema = runtime_openapi()
    openapi_bytes = canonical_json_bytes(schema)
    temp_openapi = temp_root / "openapi.json"
    temp_client = temp_root / "schema.ts"
    temp_openapi.write_bytes(openapi_bytes)
    generate_client(temp_openapi, temp_client)
    client_bytes = temp_client.read_bytes()
    client = client_bytes.decode("utf-8")
    errors, metrics = validate_contract(schema, client, policy)
    if errors:
        raise RuntimeError("contract validation failed:\n- " + "\n- ".join(errors))
    inventory_bytes = canonical_json_bytes(build_inventory(schema, policy))
    return (
        {
            OPENAPI_PATH: openapi_bytes,
            CLIENT_PATH: client_bytes,
            INVENTORY_PATH: inventory_bytes,
        },
        metrics,
    )


def _print_metrics(metrics: ContractMetrics) -> None:
    for key, value in metrics.__dict__.items():
        print(f"{key.upper()}={value}")


def artifact_drift(generated: Mapping[Path, bytes], root: Path = ROOT) -> list[str]:
    drift: list[str] = []
    for relative, content in generated.items():
        tracked_path = root / relative
        tracked = tracked_path.read_bytes() if tracked_path.exists() else None
        if tracked != content:
            drift.append(
                f"{relative.as_posix()} tracked={sha256(tracked or b'ABSENT')} "
                f"generated={sha256(content)}"
            )
    return drift


def generate() -> int:
    with tempfile.TemporaryDirectory(prefix="zeromerma-contract-generate-") as directory:
        artifacts, metrics = _generated_artifacts(Path(directory))
    for relative, content in artifacts.items():
        destination = ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        print(f"GENERATED={relative.as_posix()} SHA256={sha256(content)}")
    _print_metrics(metrics)
    return 0


def check(compare_root: Path = ROOT) -> int:
    before = {
        relative: (
            (compare_root / relative).read_bytes() if (compare_root / relative).exists() else None
        )
        for relative in (OPENAPI_PATH, CLIENT_PATH, INVENTORY_PATH)
    }
    with tempfile.TemporaryDirectory(prefix="zeromerma-contract-check-") as directory:
        artifacts, metrics = _generated_artifacts(Path(directory))
    drift = artifact_drift(artifacts, compare_root)
    after = {
        relative: (
            (compare_root / relative).read_bytes() if (compare_root / relative).exists() else None
        )
        for relative in before
    }
    if after != before:
        raise RuntimeError("contracts:check modified a tracked contract artifact")
    if drift:
        raise RuntimeError("contract drift detected:\n- " + "\n- ".join(drift))
    _print_metrics(metrics)
    print("CONTRACT_CHECK_WRITES_TRACKED_FILES=false")
    print("CONTRACT_CHECK_PASS=true")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "check"))
    parser.add_argument(
        "--compare-root",
        type=Path,
        help="compare generated artifacts with this root (check-only test probe)",
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            if args.compare_root is not None:
                raise ValueError("--compare-root is available only for contracts:check")
            return generate()
        return check((args.compare_root or ROOT).resolve())
    except (OSError, RuntimeError, subprocess.CalledProcessError, ValueError) as error:
        print(f"CONTRACT_CHECK_PASS=false\n{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
