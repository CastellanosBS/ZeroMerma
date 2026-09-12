#!/usr/bin/env python3
"""Validate the canonical ZeroMerma functional operation inventory."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import json
import os
import re
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BASELINE_COMMIT = "35b403c3cd85770b479c581e1e7e7acdd0d20bcf"
MATRIX_PATH = Path("docs/architecture/FUNCTIONAL_OPERATION_MATRIX.json")
PLAN_PATH = Path("docs/PLAN_MAESTRO_FINALIZACION_ZERO_MERMA.md")
DECISIONS_PATH = Path("docs/DECISIONES_ZERO_MERMA.md")
NON_FUNCTIONAL_VALIDATION_TOOLS = {
    "scripts/dev/api-contracts.py",
    "scripts/dev/run-web-integration.ps1",
    "scripts/dev/seed-web-integration.py",
}

IMPLEMENTATION_STATES = {
    "IMPLEMENTED_VERIFIED",
    "IMPLEMENTED_UNVERIFIED",
    "PARTIAL",
    "PLACEHOLDER",
    "DISCONNECTED",
    "INTERNAL_ONLY",
    "FRAMEWORK_ONLY",
    "DEPRECATED",
}
VERIFICATION_STATES = {
    "TESTED_IN_THIS_TASK",
    "DIRECT_TEST_EXISTS_NOT_RUN",
    "INDIRECT_TEST_ONLY",
    "NO_TEST",
    "NOT_APPLICABLE",
}
AUDIT_OUTBOX_STATES = {"ATOMIC", "PRESENT_NON_ATOMIC", "ABSENT", "NOT_REQUIRED"}
PERSISTENCE_STATES = {"NO_DB", "READ_ONLY", "WRITE", "EXTERNAL_EFFECT", "MIXED"}
CAPABILITY_STATES = {
    "PUBLIC",
    "SYSTEM_INTERNAL",
    "CAPABILITY_ENFORCED",
    "CAPABILITY_MISSING",
    "NOT_APPLICABLE",
}
SCOPE_STATES = {"SCOPE_ENFORCED", "SCOPE_PARTIAL", "SCOPE_MISSING", "NOT_APPLICABLE"}
IDEMPOTENCY_STATES = {
    "DEC07_COMPLIANT",
    "REQUEST_ID_ONLY",
    "UI_DOUBLE_CLICK_ONLY",
    "PARTIAL",
    "ABSENT",
    "NOT_REQUIRED",
}
AUTH_REQUIREMENTS = {"PUBLIC", "AUTHENTICATED", "SYSTEM_INTERNAL"}
CONSUMER_CONTRACT_STATES = {
    "CLIENT_GENERATED_USED",
    "RAW_HTTP_USED",
    "NO_CLIENT_OPERATION",
    "NOT_CONSUMED",
}
CONSUMER_DISPOSITIONS = {
    "LOCAL_UI_PRESENT",
    "API_ONLY_BY_APPROVED_DESIGN",
    "EXTERNAL_OR_SYSTEM_CONSUMER",
    "LOCAL_UI_REQUIRED_NOT_WIRED",
    "FUTURE_CONSUMER_NOT_IMPLEMENTED",
    "NOT_APPLICABLE",
}
FORBIDDEN_SEMANTIC_VALUES = {
    "",
    "NONE",
    "UNKNOWN",
    "TBD",
    "NOT_APPLICABLE",
    "IMPLEMENTED",
}
GAP_TYPES = {
    "AUTH_GAP",
    "CAPABILITY_GAP",
    "SCOPE_GAP",
    "PERSISTENCE_GAP",
    "TRANSACTION_GAP",
    "AUDIT_GAP",
    "OUTBOX_GAP",
    "IDEMPOTENCY_GAP",
    "CLIENT_CONTRACT_GAP",
    "UI_DISCONNECTED",
    "PLACEHOLDER",
    "TEST_GAP",
    "WORKER_GAP",
    "UNKNOWN_BEHAVIOR",
}

API_REQUIRED_FIELDS = {
    "operation_key",
    "surface",
    "method",
    "path",
    "operation_id",
    "include_in_schema",
    "tags",
    "router_file",
    "router_symbol",
    "module_owner",
    "use_case",
    "implementation_state",
    "verification_state",
    "auth_requirement",
    "actual_auth_dependency",
    "actual_surface_guard",
    "required_capability",
    "capability_enforcement_state",
    "required_scope",
    "scope_source",
    "scope_enforcement_state",
    "request_schema",
    "response_schema",
    "error_contract_state",
    "application_service",
    "domain_or_use_case_symbol",
    "transaction_owner",
    "transaction_boundary",
    "persistence",
    "external_side_effect",
    "reads_entities",
    "writes_entities",
    "locks_or_concurrency_control",
    "audit_required",
    "audit_actual",
    "audit_atomicity",
    "outbox_required",
    "outbox_actual",
    "outbox_atomicity",
    "idempotency_required",
    "idempotency_actual",
    "generated_client_operation",
    "consumer_contract_state",
    "consumer_disposition",
    "consumer_reason",
    "pos_consumers",
    "backoffice_consumers",
    "other_consumers",
    "direct_tests",
    "indirect_tests",
    "missing_test_types",
    "approved_target_state",
    "feature_complete_blocker",
    "later_ZM_FIN_tasks",
    "decision_refs",
    "gate_refs",
    "gap_ids",
    "evidence",
}
UI_REQUIRED_FIELDS = {
    "operation_key",
    "surface",
    "route_path",
    "dynamic_parameters",
    "route_registration_file",
    "page_component",
    "module_owner",
    "auth_guard",
    "required_capability",
    "required_scope",
    "route_registered",
    "navigation_visible",
    "feature_action_available",
    "api_wired",
    "backend_enforced",
    "api_operations_consumed",
    "queries",
    "mutations",
    "implementation_state",
    "verification_state",
    "placeholder_evidence",
    "user_actions",
    "direct_tests",
    "indirect_tests",
    "later_ZM_FIN_tasks",
    "decision_refs",
    "gate_refs",
    "feature_complete_blocker",
    "evidence",
}
EXECUTABLE_REQUIRED_FIELDS = {
    "operation_key",
    "trigger",
    "symbol",
    "source_event_or_schedule",
    "reads",
    "writes",
    "external_effect",
    "idempotency",
    "claim_or_lease",
    "retry",
    "completion_state",
    "audit",
    "outbox",
    "direct_tests",
    "indirect_tests",
    "implementation_state",
    "verification_state",
    "later_ZM_FIN_tasks",
    "decision_refs",
    "gate_refs",
    "feature_complete_blocker",
    "evidence",
}


@dataclass(frozen=True)
class Inventory:
    api: dict[str, dict[str, Any]]
    pos: dict[str, dict[str, Any]]
    backoffice: dict[str, dict[str, Any]]
    worker: dict[str, dict[str, Any]]
    internal: dict[str, dict[str, Any]]


def find_repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() and (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError("Could not locate the ZeroMerma repository root.")


def _relative_source(root: Path, source: str | None) -> str:
    if not source:
        return "NONE"
    try:
        return Path(source).resolve().relative_to(root).as_posix()
    except ValueError:
        return Path(source).as_posix()


def _walk_dependencies(dependant: Any) -> Iterable[Any]:
    for dependency in dependant.dependencies:
        yield dependency
        yield from _walk_dependencies(dependency)


def extract_api_operations(root: Path) -> dict[str, dict[str, Any]]:
    api_src = root / "apps/api/src"
    sys.path.insert(0, str(api_src)) if str(api_src) not in sys.path else None
    os.environ.setdefault(
        "ZEROMERMA_API_DATABASE_URL",
        "postgresql+psycopg://zm_matrix_inventory:disabled@127.0.0.1:1/zeromerma_matrix_inventory",
    )
    module = importlib.import_module("zeromerma_api.main")
    from fastapi.routing import APIRoute

    operations: dict[str, dict[str, Any]] = {}
    for route in module.app.routes:
        if not isinstance(route, APIRoute):
            continue
        dependency_symbols = []
        for dependency in _walk_dependencies(route.dependant):
            call = dependency.call
            call_name = getattr(call, "__qualname__", call.__class__.__qualname__)
            dependency_symbols.append(
                f"{getattr(call, '__module__', call.__class__.__module__)}:{call_name}"
            )
        for method in sorted((route.methods or set()) - {"HEAD", "OPTIONS"}):
            key = f"API:{method}:{route.path}"
            operations[key] = {
                "operation_key": key,
                "method": method,
                "path": route.path,
                "operation_id": route.operation_id or route.unique_id,
                "include_in_schema": route.include_in_schema,
                "tags": route.tags or ["NONE"],
                "router_file": _relative_source(root, route.endpoint.__code__.co_filename),
                "router_symbol": route.endpoint.__qualname__,
                "dependency_symbols": sorted(set(dependency_symbols)) or ["NONE"],
            }
    return operations


def _extract_create_route_blocks(text: str) -> list[tuple[str, str, str]]:
    pattern = re.compile(
        r"const\s+(?P<symbol>\w+)\s*=\s*createRoute\(\{(?P<body>.*?)\}\);",
        re.DOTALL,
    )
    rows: list[tuple[str, str, str]] = []
    for match in pattern.finditer(text):
        body = match.group("body")
        path_match = re.search(r'\bpath:\s*"([^"]+)"', body)
        component_match = re.search(r"\bcomponent:\s*([^,\n]+)", body)
        if path_match:
            rows.append(
                (
                    match.group("symbol"),
                    path_match.group(1),
                    component_match.group(1).strip() if component_match else "INLINE_OR_DYNAMIC",
                )
            )
    return rows


def extract_pos_routes(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "apps/pos-web/src/router.tsx"
    routes: dict[str, dict[str, Any]] = {}
    route_blocks = _extract_create_route_blocks(path.read_text(encoding="utf-8"))
    for symbol, route_path, component in route_blocks:
        key = f"UI:POS:{route_path}"
        routes[key] = {
            "operation_key": key,
            "route_path": route_path,
            "route_symbol": symbol,
            "page_component": component,
            "route_registration_file": "apps/pos-web/src/router.tsx",
        }
    return routes


def extract_backoffice_routes(root: Path) -> dict[str, dict[str, Any]]:
    router_path = root / "apps/backoffice-web/src/router.tsx"
    module_path = root / "apps/backoffice-web/src/features/admin/adminModules.ts"
    router_text = router_path.read_text(encoding="utf-8")
    module_text = module_path.read_text(encoding="utf-8")
    routes: dict[str, dict[str, Any]] = {}

    for symbol, route_path, component in _extract_create_route_blocks(router_text):
        if symbol in {
            "indexRoute",
            "healthRoute",
            "loginRoute",
            "adminRoute",
            "adminIndexRoute",
            "legacyRolesRoute",
            "legacyRegistersRoute",
            "legacySalesTicketsRoute",
            "legacyPurchasesRoute",
        }:
            parent_admin = symbol.startswith("admin") or symbol.startswith("legacy")
            combined = route_path
            if parent_admin and route_path not in {"/admin"}:
                combined = "/admin/" if route_path == "/" else f"/admin/{route_path}"
            key = f"UI:BACKOFFICE:{combined}"
            routes[key] = {
                "operation_key": key,
                "route_path": combined,
                "route_symbol": symbol,
                "page_component": component,
                "route_registration_file": "apps/backoffice-web/src/router.tsx",
            }

    for slug in re.findall(r'^\s*routeSlug:\s*"([^"]+)"', module_text, re.MULTILINE):
        route_path = f"/admin/{slug}"
        key = f"UI:BACKOFFICE:{route_path}"
        routes[key] = {
            "operation_key": key,
            "route_path": route_path,
            "route_symbol": "adminModuleRoutes",
            "page_component": "MODULE_DISPATCH",
            "route_registration_file": "apps/backoffice-web/src/router.tsx",
        }
    return routes


def extract_worker_operations(root: Path) -> dict[str, dict[str, Any]]:
    candidates = {
        root / "apps/worker/src/zeromerma_worker/main.py": {"main", "run_worker"},
        root / "apps/worker/src/zeromerma_worker/outbox/poller.py": {"OutboxPoller.poll_once"},
    }
    operations: dict[str, dict[str, Any]] = {}
    for path, accepted in candidates.items():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        module_name = ".".join(path.relative_to(root / "apps/worker/src").with_suffix("").parts)
        discovered: set[str] = set()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_"):
                    continue
                discovered.add(node.name)
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    if isinstance(
                        child, (ast.FunctionDef, ast.AsyncFunctionDef)
                    ) and not child.name.startswith("_"):
                        discovered.add(f"{node.name}.{child.name}")
        for symbol in sorted(discovered & accepted):
            key = f"WORKER:{module_name}:{symbol}"
            operations[key] = {
                "operation_key": key,
                "symbol": symbol,
                "source_file": path.relative_to(root).as_posix(),
            }
    return operations


def extract_internal_operations(root: Path) -> dict[str, dict[str, Any]]:
    operations: dict[str, dict[str, Any]] = {}
    api_src = root / "apps/api/src"
    sys.path.insert(0, str(api_src)) if str(api_src) not in sys.path else None
    os.environ.setdefault(
        "ZEROMERMA_API_DATABASE_URL",
        "postgresql+psycopg://zm_matrix_inventory:disabled@127.0.0.1:1/zeromerma_matrix_inventory",
    )
    app_module = importlib.import_module("zeromerma_api.main")
    from fastapi.routing import APIRoute

    for route in app_module.app.routes:
        if isinstance(route, APIRoute):
            continue
        path = getattr(route, "path", None)
        name = getattr(route, "name", None)
        if not path or not name:
            continue
        key = f"INTERNAL:fastapi:{name}"
        operations[key] = {
            "operation_key": key,
            "symbol": name,
            "source_file": "apps/api/src/zeromerma_api/main.py",
        }

    scripts_root = root / "scripts"
    for path in sorted(scripts_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".py", ".ps1"}:
            continue
        relative = path.relative_to(root).as_posix()
        if "/tests/" in f"/{relative}" or path.name.startswith("test_"):
            continue
        if relative.startswith("scripts/powershell/"):
            continue
        if relative in NON_FUNCTIONAL_VALIDATION_TOOLS:
            continue
        module = path.relative_to(root).with_suffix("").as_posix().replace("/", ".")
        key = f"INTERNAL:{module}:command"
        operations[key] = {
            "operation_key": key,
            "symbol": "command",
            "source_file": relative,
        }
    return operations


def discover_inventory(root: Path) -> Inventory:
    return Inventory(
        api=extract_api_operations(root),
        pos=extract_pos_routes(root),
        backoffice=extract_backoffice_routes(root),
        worker=extract_worker_operations(root),
        internal=extract_internal_operations(root),
    )


def _is_blank(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _validate_rows(
    rows: list[dict[str, Any]],
    required: set[str],
    section: str,
    errors: list[str],
) -> None:
    for index, row in enumerate(rows):
        missing = sorted(required - row.keys())
        if missing:
            errors.append(f"{section}[{index}] missing fields: {', '.join(missing)}")
        for field in required & row.keys():
            if _is_blank(row[field]):
                errors.append(f"{section}[{index}].{field} is blank")
        if row.get("implementation_state") not in IMPLEMENTATION_STATES:
            errors.append(f"{section}[{index}] invalid implementation_state")
        if row.get("verification_state") not in VERIFICATION_STATES:
            errors.append(f"{section}[{index}] invalid verification_state")


def _validate_discovered_section(
    rows: list[dict[str, Any]],
    discovered: dict[str, dict[str, Any]],
    section: str,
    errors: list[str],
) -> None:
    matrix = {
        str(row["operation_key"]): row for row in rows if isinstance(row.get("operation_key"), str)
    }
    matrix_keys = set(matrix)
    discovered_keys = set(discovered)
    for key in sorted(discovered_keys - matrix_keys):
        errors.append(f"{section} registered operation missing from matrix: {key}")
    for key in sorted(matrix_keys - discovered_keys):
        errors.append(f"{section} matrix row has no registered operation: {key}")
    for key in sorted(matrix_keys & discovered_keys):
        actual = discovered[key]
        row = matrix[key]
        for field in (
            "method",
            "path",
            "operation_id",
            "include_in_schema",
            "router_file",
            "router_symbol",
            "route_path",
            "route_registration_file",
            "symbol",
        ):
            if field in actual and row.get(field) != actual[field]:
                errors.append(
                    f"{section} drift for {key}: {field} matrix={row.get(field)!r} "
                    f"actual={actual[field]!r}"
                )


def _task_ids(root: Path) -> set[str]:
    text = (root / PLAN_PATH).read_text(encoding="utf-8")
    return set(re.findall(r"^### (ZM-FIN-\d{3}) —", text, re.MULTILINE))


def _decision_ids(root: Path) -> set[str]:
    text = (root / DECISIONS_PATH).read_text(encoding="utf-8")
    return set(re.findall(r"^## (DEC-\d{2}) —", text, re.MULTILINE))


def _gate_ids(root: Path) -> set[str]:
    return set(
        re.findall(
            r"\b(G\d) —",
            (root / PLAN_PATH).read_text(encoding="utf-8"),
        )
    )


def _validate_reference(
    reference: str,
    root: Path,
    operation_key: str,
    errors: list[str],
    reference_kind: str = "evidence",
) -> None:
    raw_path, separator, symbol = reference.partition("#")
    if not raw_path or Path(raw_path).is_absolute() or ".." in Path(raw_path).parts:
        errors.append(f"invalid {reference_kind} path for {operation_key}: {reference}")
        return
    if any(character in raw_path for character in "*?[]"):
        errors.append(f"glob is not allowed in {reference_kind} for {operation_key}: {reference}")
        return
    path = (root / raw_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        errors.append(f"invalid {reference_kind} path for {operation_key}: {reference}")
        return
    if not path.is_file():
        errors.append(f"missing {reference_kind} file for {operation_key}: {raw_path}")
        return
    if separator and not symbol:
        errors.append(f"missing {reference_kind} symbol for {operation_key}: {reference}")
        return
    if separator and symbol not in path.read_text(encoding="utf-8", errors="ignore"):
        errors.append(f"missing {reference_kind} symbol for {operation_key}: {reference}")


def _meaningful_text(value: Any) -> bool:
    return isinstance(value, str) and value.strip().upper() not in FORBIDDEN_SEMANTIC_VALUES


def _references(row: dict[str, Any], field: str) -> list[str]:
    value = row.get(field, [])
    if not isinstance(value, list):
        return []
    return [
        reference
        for reference in value
        if isinstance(reference, str) and reference not in {"NONE", "NOT_APPLICABLE"}
    ]


def _reference_is_valid(reference: str, root: Path) -> bool:
    errors: list[str] = []
    _validate_reference(reference, root, "reference-probe", errors, "test reference")
    return not errors


def _semantic_counts(data: dict[str, Any], root: Path) -> dict[str, int]:
    all_rows = (
        data.get("api_operations", [])
        + data.get("pos_routes", [])
        + data.get("backoffice_routes", [])
        + data.get("worker_operations", [])
        + data.get("internal_operations", [])
    )
    partial_without_target = sum(
        row.get("implementation_state") == "PARTIAL"
        and not _meaningful_text(row.get("approved_target_state"))
        for row in all_rows
    )
    unjustified_not_consumed = sum(
        row.get("consumer_contract_state") == "NOT_CONSUMED"
        and (
            row.get("consumer_disposition") not in CONSUMER_DISPOSITIONS
            or row.get("consumer_disposition") in {"LOCAL_UI_PRESENT", "NOT_APPLICABLE"}
            or not _meaningful_text(row.get("consumer_reason"))
        )
        for row in data.get("api_operations", [])
    )
    invalid_direct = sum(
        not _reference_is_valid(reference, root)
        for row in all_rows
        for reference in _references(row, "direct_tests")
    )
    invalid_indirect = sum(
        not _reference_is_valid(reference, root)
        for row in all_rows
        for reference in _references(row, "indirect_tests")
    )
    return {
        "partial_without_approved_target_count": partial_without_target,
        "unjustified_not_consumed_api_count": unjustified_not_consumed,
        "invalid_direct_test_reference_count": invalid_direct,
        "invalid_indirect_test_reference_count": invalid_indirect,
    }


def expected_module_summary(data: dict[str, Any]) -> dict[str, Any]:
    api_rows = data.get("api_operations", [])
    pos_rows = data.get("pos_routes", [])
    backoffice_rows = data.get("backoffice_routes", [])
    worker_rows = data.get("worker_operations", [])
    internal_rows = data.get("internal_operations", [])
    all_rows = api_rows + pos_rows + backoffice_rows + worker_rows + internal_rows
    return {
        "surface_counts": {
            "api": len(api_rows),
            "pos": len(pos_rows),
            "backoffice": len(backoffice_rows),
            "worker": len(worker_rows),
            "internal": len(internal_rows),
        },
        "implementation_state_counts": dict(
            sorted(Counter(row["implementation_state"] for row in all_rows).items())
        ),
        "verification_state_counts": dict(
            sorted(Counter(row["verification_state"] for row in all_rows).items())
        ),
        "consumer_contract_state_counts": dict(
            sorted(Counter(str(row.get("consumer_contract_state")) for row in api_rows).items())
        ),
        "consumer_disposition_counts": dict(
            sorted(Counter(str(row.get("consumer_disposition")) for row in api_rows).items())
        ),
        "gap_type_counts": dict(
            sorted(Counter(gap["gap_type"] for gap in data.get("known_gaps", [])).items())
        ),
        "feature_complete_blocker_count": sum(
            row.get("feature_complete_blocker") is True for row in all_rows
        ),
        "test_gap_count": sum(
            gap.get("gap_type") == "TEST_GAP" for gap in data.get("known_gaps", [])
        ),
        "operation_count": len(all_rows),
    }


def _openapi_fingerprint(root: Path) -> dict[str, Any]:
    api_src = root / "apps/api/src"
    sys.path.insert(0, str(api_src)) if str(api_src) not in sys.path else None
    module = importlib.import_module("zeromerma_api.main")
    runtime = module.app.openapi()
    tracked = json.loads((root / "packages/api-client/openapi.json").read_text(encoding="utf-8"))
    methods = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}

    def operations(document: dict[str, Any]) -> dict[str, str]:
        return {
            f"{method.upper()} {path}": operation.get("operationId", "NONE")
            for path, path_item in document.get("paths", {}).items()
            for method, operation in path_item.items()
            if method in methods
        }

    runtime_operations = operations(runtime)
    tracked_operations = operations(tracked)
    runtime_json = json.dumps(
        runtime, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    tracked_json = json.dumps(
        tracked, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return {
        "runtime_operation_count": len(runtime_operations),
        "tracked_operation_count": len(tracked_operations),
        "runtime_only": sorted(set(runtime_operations) - set(tracked_operations)),
        "tracked_only": sorted(set(tracked_operations) - set(runtime_operations)),
        "operation_id_drift": sorted(
            key
            for key in set(runtime_operations) & set(tracked_operations)
            if runtime_operations[key] != tracked_operations[key]
        ),
        "runtime_sha256_canonical_json": hashlib.sha256(runtime_json).hexdigest(),
        "tracked_sha256_canonical_json": hashlib.sha256(tracked_json).hexdigest(),
        "schema_drift_suspected": runtime_json != tracked_json,
        "classification": (
            "NO_DRIFT_OBSERVED" if runtime_json == tracked_json else "SCHEMA_DRIFT_SUSPECTED"
        ),
    }


def validate_matrix(data: dict[str, Any], inventory: Inventory, root: Path) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != "1.0.0":
        errors.append("schema_version must be 1.0.0")
    if data.get("baseline_commit") != BASELINE_COMMIT:
        errors.append(f"baseline_commit must be {BASELINE_COMMIT}")

    api_rows = data.get("api_operations", [])
    pos_rows = data.get("pos_routes", [])
    backoffice_rows = data.get("backoffice_routes", [])
    worker_rows = data.get("worker_operations", [])
    internal_rows = data.get("internal_operations", [])
    _validate_rows(api_rows, API_REQUIRED_FIELDS, "api_operations", errors)
    _validate_rows(pos_rows, UI_REQUIRED_FIELDS, "pos_routes", errors)
    _validate_rows(backoffice_rows, UI_REQUIRED_FIELDS, "backoffice_routes", errors)
    _validate_rows(worker_rows, EXECUTABLE_REQUIRED_FIELDS, "worker_operations", errors)
    _validate_rows(internal_rows, EXECUTABLE_REQUIRED_FIELDS, "internal_operations", errors)

    _validate_discovered_section(api_rows, inventory.api, "api_operations", errors)
    _validate_discovered_section(pos_rows, inventory.pos, "pos_routes", errors)
    _validate_discovered_section(backoffice_rows, inventory.backoffice, "backoffice_routes", errors)
    _validate_discovered_section(worker_rows, inventory.worker, "worker_operations", errors)
    _validate_discovered_section(internal_rows, inventory.internal, "internal_operations", errors)

    all_rows = api_rows + pos_rows + backoffice_rows + worker_rows + internal_rows
    row_sections = {
        id(row): section
        for section, rows in (
            ("API", api_rows),
            ("POS", pos_rows),
            ("BACKOFFICE", backoffice_rows),
            ("WORKER", worker_rows),
            ("INTERNAL", internal_rows),
        )
        for row in rows
    }
    keys = [row.get("operation_key") for row in all_rows]
    duplicates = sorted(key for key, count in Counter(keys).items() if count > 1)
    if duplicates:
        errors.append(f"duplicate operation keys: {', '.join(str(key) for key in duplicates)}")

    tasks = _task_ids(root)
    decisions = _decision_ids(root)
    gates = _gate_ids(root)
    gap_by_id = {
        str(gap.get("gap_id")): gap
        for gap in data.get("known_gaps", [])
        if isinstance(gap, dict) and isinstance(gap.get("gap_id"), str)
    }
    for row in all_rows:
        key = str(row.get("operation_key", "MISSING_KEY"))
        for task in row.get("later_ZM_FIN_tasks", []):
            if task != "NOT_APPLICABLE" and task not in tasks:
                errors.append(f"invalid ZM-FIN reference for {key}: {task}")
        for decision in row.get("decision_refs", []):
            if decision != "NOT_APPLICABLE" and decision not in decisions:
                errors.append(f"invalid DEC reference for {key}: {decision}")
        for gate in row.get("gate_refs", []):
            if gate != "NOT_APPLICABLE" and gate not in gates:
                errors.append(f"invalid gate reference for {key}: {gate}")
        for reference in row.get("evidence", []):
            _validate_reference(reference, root, key, errors)

        if row.get("implementation_state") == "PARTIAL" and not _meaningful_text(
            row.get("approved_target_state")
        ):
            errors.append(
                "PARTIAL approved target invalid: "
                f"operation_key={key} surface={row_sections[id(row)]} "
                "reason=missing, blank, sentinel, or prohibited generic value"
            )

        direct_references = _references(row, "direct_tests")
        indirect_references = _references(row, "indirect_tests")
        valid_direct_references = 0
        for reference in direct_references:
            reference_errors: list[str] = []
            _validate_reference(reference, root, key, reference_errors, "direct test reference")
            if reference_errors:
                errors.extend(reference_errors)
            else:
                valid_direct_references += 1
        for reference in indirect_references:
            _validate_reference(reference, root, key, errors, "indirect test reference")

        verification_state = row.get("verification_state")
        if verification_state == "DIRECT_TEST_EXISTS_NOT_RUN" and valid_direct_references == 0:
            errors.append(f"DIRECT_TEST_EXISTS_NOT_RUN has no valid direct test reference: {key}")
        if verification_state == "NO_TEST":
            if direct_references:
                errors.append(f"NO_TEST declares a direct test reference: {key}")
            row_gap_types = {
                str(gap_by_id[gap_id].get("gap_type"))
                for gap_id in row.get("gap_ids", [])
                if gap_id in gap_by_id
            }
            if "TEST_GAP" not in row_gap_types:
                errors.append(f"NO_TEST is missing a TEST_GAP: {key}")

    for row in api_rows:
        if row.get("persistence") not in PERSISTENCE_STATES:
            errors.append(f"invalid persistence for {row.get('operation_key')}")
        if row.get("capability_enforcement_state") not in CAPABILITY_STATES:
            errors.append(f"invalid capability state for {row.get('operation_key')}")
        if row.get("scope_enforcement_state") not in SCOPE_STATES:
            errors.append(f"invalid scope state for {row.get('operation_key')}")
        if row.get("audit_actual") not in AUDIT_OUTBOX_STATES:
            errors.append(f"invalid audit state for {row.get('operation_key')}")
        if row.get("outbox_actual") not in AUDIT_OUTBOX_STATES:
            errors.append(f"invalid outbox state for {row.get('operation_key')}")
        if row.get("idempotency_actual") not in IDEMPOTENCY_STATES:
            errors.append(f"invalid idempotency state for {row.get('operation_key')}")
        if row.get("auth_requirement") not in AUTH_REQUIREMENTS:
            errors.append(f"invalid auth requirement for {row.get('operation_key')}")
        if row.get("consumer_contract_state") not in CONSUMER_CONTRACT_STATES:
            errors.append(f"invalid consumer contract state for {row.get('operation_key')}")
        if row.get("consumer_disposition") not in CONSUMER_DISPOSITIONS:
            errors.append(f"invalid consumer disposition for {row.get('operation_key')}")
        if not _meaningful_text(row.get("consumer_reason")):
            errors.append(f"invalid consumer reason for {row.get('operation_key')}")

        key = str(row.get("operation_key"))
        contract_state = row.get("consumer_contract_state")
        disposition = row.get("consumer_disposition")
        local_consumers = _references(row, "pos_consumers") + _references(
            row, "backoffice_consumers"
        )
        row_gap_types = {
            str(gap_by_id[gap_id].get("gap_type"))
            for gap_id in row.get("gap_ids", [])
            if gap_id in gap_by_id
        }
        later_tasks = [
            task for task in row.get("later_ZM_FIN_tasks", []) if task != "NOT_APPLICABLE"
        ]
        gate_references = [gate for gate in row.get("gate_refs", []) if gate != "NOT_APPLICABLE"]

        if contract_state in {"RAW_HTTP_USED", "CLIENT_GENERATED_USED"}:
            if disposition != "LOCAL_UI_PRESENT":
                errors.append(f"located local UI consumer has incompatible disposition: {key}")
            if not local_consumers:
                errors.append(f"located local UI consumer has no consumer reference: {key}")
        elif contract_state == "NO_CLIENT_OPERATION":
            if disposition != "NOT_APPLICABLE":
                errors.append(f"NO_CLIENT_OPERATION must be NOT_APPLICABLE: {key}")
        elif contract_state == "NOT_CONSUMED":
            if disposition in {"LOCAL_UI_PRESENT", "NOT_APPLICABLE"}:
                errors.append(f"NOT_CONSUMED has unjustified disposition: {key}")
            if disposition == "LOCAL_UI_REQUIRED_NOT_WIRED":
                if not row_gap_types & {"UI_DISCONNECTED", "CLIENT_CONTRACT_GAP"}:
                    errors.append(f"missing local UI consumer requires UI/client gap: {key}")
                if not later_tasks:
                    errors.append(f"missing local UI consumer requires a later task: {key}")
                if not gate_references:
                    errors.append(f"missing local UI consumer requires a gate: {key}")
                if row.get("feature_complete_blocker") is not True:
                    errors.append(f"missing local UI consumer must block Feature Complete: {key}")
            elif disposition == "FUTURE_CONSUMER_NOT_IMPLEMENTED":
                if not row_gap_types or not later_tasks or not gate_references:
                    errors.append(f"future consumer requires gap, task, and gate: {key}")
                if row.get("feature_complete_blocker") is not True:
                    errors.append(f"future in-scope consumer must block Feature Complete: {key}")
            elif disposition == "API_ONLY_BY_APPROVED_DESIGN":
                if not row.get("evidence") or row.get("evidence") == ["NONE"]:
                    errors.append(f"API-only disposition requires evidence: {key}")
            elif disposition == "EXTERNAL_OR_SYSTEM_CONSUMER":
                other_consumers = _references(row, "other_consumers")
                if not other_consumers:
                    errors.append(
                        f"external/system disposition requires an identified consumer: {key}"
                    )
                for reference in other_consumers:
                    _validate_reference(reference, root, key, errors, "external/system consumer")

    not_consumed_reasons = [
        str(row.get("consumer_reason", "")).strip()
        for row in api_rows
        if row.get("consumer_contract_state") == "NOT_CONSUMED"
        and _meaningful_text(row.get("consumer_reason"))
    ]
    duplicate_not_consumed_reasons = sorted(
        reason for reason, count in Counter(not_consumed_reasons).items() if count > 1
    )
    if duplicate_not_consumed_reasons:
        errors.append("NOT_CONSUMED consumer reasons must be operation-specific")

    expected_openapi = _openapi_fingerprint(root)
    declared_openapi = data.get("openapi_comparison", {})
    for field, expected in expected_openapi.items():
        if declared_openapi.get(field) != expected:
            errors.append(
                f"OpenAPI comparison drift: {field} matrix={declared_openapi.get(field)!r} "
                f"actual={expected!r}"
            )

    unknown_paths: list[str] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                visit(child_value, f"{path}.{child_key}")
        elif isinstance(value, list):
            for index, child_value in enumerate(value):
                visit(child_value, f"{path}[{index}]")
        elif isinstance(value, str) and value in {
            "UNKNOWN",
            "UNKNOWN_CONSUMER",
            "UNKNOWN_BEHAVIOR",
        }:
            unknown_paths.append(path)

    for section_name in (
        "api_operations",
        "pos_routes",
        "backoffice_routes",
        "worker_operations",
        "internal_operations",
        "known_gaps",
    ):
        visit(data.get(section_name, []), f"matrix.{section_name}")
    if unknown_paths:
        errors.append(f"UNKNOWN values remain: {', '.join(unknown_paths[:20])}")

    gap_ids: list[str] = []
    operation_keys = set(keys)
    for gap in data.get("known_gaps", []):
        required = {
            "gap_id",
            "operation_key",
            "gap_type",
            "current_state",
            "approved_target",
            "risk",
            "later_task",
            "gate",
            "evidence",
        }
        if required - gap.keys():
            errors.append(f"known gap missing fields: {gap.get('gap_id', 'MISSING')}")
        if gap.get("gap_type") not in GAP_TYPES:
            errors.append(f"known gap has invalid type: {gap.get('gap_id', 'MISSING')}")
        gap_ids.append(gap.get("gap_id"))
        if gap.get("operation_key") not in operation_keys:
            errors.append(f"known gap references missing operation: {gap.get('operation_key')}")
        if gap.get("later_task") not in tasks and gap.get("later_task") != "PLAN_GAP":
            errors.append(f"known gap references invalid task: {gap.get('later_task')}")
        if gap.get("gate") not in gates:
            errors.append(f"known gap references invalid gate: {gap.get('gate')}")
        for reference in gap.get("evidence", []):
            _validate_reference(reference, root, str(gap.get("operation_key")), errors)
    if len(gap_ids) != len(set(gap_ids)):
        errors.append("duplicate gap ids")
    declared_gap_ids = {
        gap_id for row in all_rows for gap_id in row.get("gap_ids", []) if gap_id != "NONE"
    }
    if declared_gap_ids != set(gap_ids):
        errors.append("operation gap_ids and known_gaps catalog do not match")

    if data.get("module_summary") != expected_module_summary(data):
        errors.append("module_summary does not match operation rows and known gaps")

    return errors


def _summary(data: dict[str, Any], inventory: Inventory) -> dict[str, Any]:
    rows = (
        data["api_operations"]
        + data["pos_routes"]
        + data["backoffice_routes"]
        + data["worker_operations"]
        + data["internal_operations"]
    )
    state_counts = Counter(row["implementation_state"] for row in rows)
    gap_counts = Counter(gap["gap_type"] for gap in data.get("known_gaps", []))
    summary = {
        "api_registered_route_count": len(inventory.api),
        "api_operation_count": len(inventory.api),
        "api_openapi_operation_count": sum(
            bool(row["include_in_schema"]) for row in data["api_operations"]
        ),
        "api_hidden_operation_count": sum(
            not bool(row["include_in_schema"]) for row in data["api_operations"]
        ),
        "pos_route_count": len(inventory.pos),
        "backoffice_route_count": len(inventory.backoffice),
        "worker_operation_count": len(inventory.worker),
        "internal_operation_count": len(inventory.internal),
        "operation_count": len(rows),
        "state_counts": dict(sorted(state_counts.items())),
        "gap_counts": dict(sorted(gap_counts.items())),
        "feature_complete_blocker_count": sum(
            bool(row["feature_complete_blocker"]) for row in rows
        ),
        "plan_gap_count": sum(
            gap.get("later_task") == "PLAN_GAP" for gap in data.get("known_gaps", [])
        ),
        "unknown_operation_count": 0,
        "verification_state_counts": dict(
            sorted(Counter(row["verification_state"] for row in rows).items())
        ),
        "consumer_disposition_counts": dict(
            sorted(Counter(row["consumer_disposition"] for row in data["api_operations"]).items())
        ),
    }
    summary.update(_semantic_counts(data, find_repo_root()))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=MATRIX_PATH)
    parser.add_argument("--json", action="store_true", help="Emit the summary as JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = find_repo_root()
    matrix_path = args.matrix if args.matrix.is_absolute() else root / args.matrix
    data = json.loads(matrix_path.read_text(encoding="utf-8"))
    inventory = discover_inventory(root)
    errors = validate_matrix(data, inventory, root)
    summary = _summary(data, inventory)
    if errors:
        print("Functional operation matrix validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print("Functional operation matrix validation passed.")
        for key, value in summary.items():
            print(f"{key}={json.dumps(value, sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
