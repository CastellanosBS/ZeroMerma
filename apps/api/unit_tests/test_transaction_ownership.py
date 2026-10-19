"""Architecture gate: every database boundary has an explicit, current owner."""

from __future__ import annotations

import ast
import json
from collections import Counter
from functools import cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOTS = ("apps/api/src", "apps/worker/src")
METHODS = {"commit", "rollback", "flush", "begin", "begin_nested"}
RECEIVERS = {"session", "audit_session", "connection", "engine", "self._engine"}


@cache
def _matrix() -> dict[str, Any]:
    return json.loads(
        (ROOT / "docs/architecture/TRANSACTION_BOUNDARY_MATRIX.json").read_text(encoding="utf-8")
    )


@cache
def _functions() -> dict[tuple[str, str], ast.FunctionDef | ast.AsyncFunctionDef]:
    functions: dict[tuple[str, str], ast.FunctionDef | ast.AsyncFunctionDef] = {}

    class Functions(ast.NodeVisitor):
        def __init__(self, path: Path) -> None:
            self.path = path.relative_to(ROOT).as_posix()
            self.stack: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            self.stack.append(node.name)
            functions[self.path, ".".join(self.stack)] = node
            self.generic_visit(node)
            self.stack.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

    for directory in SOURCE_ROOTS:
        for path in sorted((ROOT / directory).rglob("*.py")):
            Functions(path).visit(ast.parse(path.read_text(encoding="utf-8-sig")))
    return functions


def _calls(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()

    class Calls(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            pass

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            pass

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            pass

        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Attribute):
                receiver = ast.unparse(node.func.value)
                if node.func.attr in METHODS and receiver in RECEIVERS:
                    counts[node.func.attr, receiver] += 1
            self.generic_visit(node)

    visitor = Calls()
    for statement in node.body:
        visitor.visit(statement)
    return [
        {"method": method, "receiver": receiver, "count": count}
        for (method, receiver), count in sorted(counts.items())
    ]


def test_transaction_inventory_matches_all_declared_database_call_sites() -> None:
    matrix = _matrix()
    assert matrix["schema_version"] == 1
    assert set(matrix["inventory_scope"]["roots"]) == set(SOURCE_ROOTS)
    assert set(matrix["inventory_scope"]["methods"]) == METHODS
    assert set(matrix["inventory_scope"]["receivers"]) == RECEIVERS
    actual = {key: calls for key, node in _functions().items() if (calls := _calls(node))}
    sites = matrix["transaction_sites"]
    documented = {(site["path"], site["symbol"]): site["calls"] for site in sites}
    assert len(documented) == len(sites), "Transaction sites must not be duplicated"
    assert actual == documented, "Update ownership evidence when a database boundary changes"


def test_transaction_owners_and_groups_reference_existing_symbols() -> None:
    matrix = _matrix()
    groups = {group["id"]: group for group in matrix["ownership_groups"]}
    assert len(groups) == len(matrix["ownership_groups"])

    def reference_exists(reference: str) -> None:
        if reference.startswith("group:"):
            assert reference.removeprefix("group:") in groups
        else:
            path, symbol = reference.split("#", 1)
            assert (path, symbol) in _functions(), reference

    for site in matrix["transaction_sites"]:
        assert site["ownership_group"] in groups
        reference_exists(site["owner"])
        assert site["cleanup"]["kind"]
    for group in groups.values():
        assert group["failure_behavior"] and group["post_commit"]
        for field in ("owners", "participants", "entry_points"):
            for reference in group[field]:
                reference_exists(reference)


def test_standalone_commit_owners_have_failure_cleanup_and_participants_do_not_commit() -> None:
    for site in _matrix()["transaction_sites"]:
        node = _functions()[site["path"], site["symbol"]]
        methods = {call["method"] for call in site["calls"]}
        identity = f"{site['path']}#{site['symbol']}"
        if site["role"] in {"STANDALONE_OWNER", "SECURITY_GATE"}:
            assert "commit" in methods, identity
            assert "rollback_on_failure" in {
                ast.unparse(decorator) for decorator in node.decorator_list
            }, identity
            assert "rollback" not in methods, "The failure guard owns cleanup: " + identity
        elif site["role"] == "PARTICIPANT":
            assert not methods & {"commit", "rollback"}, identity
        elif site["role"] == "ENDPOINT_OWNER":
            assert any(
                isinstance(item, ast.Call)
                and isinstance(item.func, ast.Name)
                and item.func.id == "rollback_on_error"
                for item in ast.walk(node)
            ), identity


def test_request_cleanup_and_security_attempt_helpers_cannot_commit() -> None:
    functions = _functions()
    request = functions["apps/api/src/zeromerma_api/db/session.py", "get_session"]
    assert {call["method"] for call in _calls(request)} == {"rollback"}
    rate_attempt = functions[
        "apps/api/src/zeromerma_api/modules/identity/application/session_services.py",
        "SessionService._rate_attempt",
    ]
    assert not {call["method"] for call in _calls(rate_attempt)} & {"commit", "rollback"}
    for path, symbol in (
        ("apps/api/src/zeromerma_api/modules/audit/application/service.py", "AuditRecorder.record"),
        ("apps/api/src/zeromerma_api/modules/outbox/application/service.py", "OutboxWriter.append"),
    ):
        assert not _calls(functions[path, symbol]), "Trace participants must not own boundaries"
