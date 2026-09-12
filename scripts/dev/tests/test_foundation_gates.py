from __future__ import annotations

import json
import os
import runpy
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[3]
CONTRACT_ARTIFACTS = (
    Path("packages/api-client/openapi.json"),
    Path("packages/api-client/src/generated/schema.ts"),
    Path("docs/architecture/API_CONTRACT_INVENTORY.json"),
)


def _canonical_version_overrides() -> dict[str, str]:
    policy = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    return {
        "PythonVersionOverride": (ROOT / ".python-version").read_text().strip() + ".0",
        "UvVersionOverride": policy["tool"]["uv"]["required-version"].removeprefix("=="),
        "NodeVersionOverride": (ROOT / ".node-version").read_text().strip() + ".0.0",
        "CorepackVersionOverride": "0.34.6",
        "PnpmVersionOverride": package["packageManager"].split("+", 1)[0].split("@", 1)[1],
    }


def _run_toolchain(
    *, overrides: dict[str, str] | None = None, test_mode: bool = True
) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("pwsh")
    assert executable is not None, "Foundation gate tests require PowerShell 7"
    versions = _canonical_version_overrides()
    versions.update(overrides or {})
    arguments = [executable, "-NoProfile", "-File", str(ROOT / "scripts/dev/check-toolchain.ps1")]
    if test_mode:
        arguments.append("-TestMode")
    for name, version in versions.items():
        arguments.extend((f"-{name}", version))
    return subprocess.run(
        arguments, cwd=ROOT, capture_output=True, text=True, timeout=30, check=False
    )


def test_canonical_toolchain_mock_versions_are_accepted() -> None:
    result = _run_toolchain()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Toolchain preflight passed." in result.stdout


@pytest.mark.parametrize(
    ("override", "version", "expected_tool"),
    [("NodeVersionOverride", "24.0.0", "Node.js"), ("UvVersionOverride", "0.0.0", "uv")],
)
def test_incompatible_toolchain_versions_exit_nonzero(
    override: str, version: str, expected_tool: str
) -> None:
    result = _run_toolchain(overrides={override: version})
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert f"tool={expected_tool}" in output
    assert f"observed={version}" in output
    assert "Toolchain preflight passed." not in output


def test_version_override_requires_explicit_test_mode() -> None:
    result = _run_toolchain(test_mode=False)
    assert result.returncode != 0
    assert "Version overrides are allowed only with -TestMode" in result.stderr


def test_corrupt_openapi_copy_fails_actual_contract_gate_without_writing_artifacts(
    tmp_path: Path,
) -> None:
    original = {relative: (ROOT / relative).read_bytes() for relative in CONTRACT_ARTIFACTS}
    for relative, content in original.items():
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    openapi_copy = tmp_path / CONTRACT_ARTIFACTS[0]
    altered = json.loads(openapi_copy.read_text(encoding="utf-8"))
    altered["info"]["version"] = "deliberately-corrupted-foundation-probe"
    openapi_copy.write_text(json.dumps(altered), encoding="utf-8")
    before_probe = {relative: (tmp_path / relative).read_bytes() for relative in CONTRACT_ARTIFACTS}

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/dev/api-contracts.py"),
            "check",
            "--compare-root",
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "contract drift detected" in result.stderr
    assert "packages/api-client/openapi.json" in result.stderr
    assert "CONTRACT_CHECK_PASS=false" in result.stderr
    assert {relative: (ROOT / relative).read_bytes() for relative in CONTRACT_ARTIFACTS} == original
    assert {
        relative: (tmp_path / relative).read_bytes() for relative in CONTRACT_ARTIFACTS
    } == before_probe


@pytest.mark.parametrize(
    ("scenario", "expected_message"),
    [
        ("operational_database", "database name is explicitly prohibited"),
        ("missing_test_url", "application DATABASE_URL fallback is forbidden"),
        ("missing_isolated_flag", "Browser fixtures require the isolated integration harness"),
        ("mismatched_run", "Browser run identity must match the authorized test database"),
        ("short_credential", "Browser credentials must be generated per run"),
    ],
)
def test_browser_seed_refuses_unsafe_context_before_creating_engine(
    monkeypatch: pytest.MonkeyPatch, scenario: str, expected_message: str
) -> None:
    for name in os.environ:
        if name.startswith(("ZEROMERMA_", "ZM_E2E_", "ZM_WEB_")):
            monkeypatch.delenv(name)
    run_id = "foundation_gate_probe"
    database = f"zeromerma_test_{run_id}"
    credential = "unit-only-credential-not-a-real-secret"
    environment = {
        "ZEROMERMA_TEST_ENVIRONMENT": "test",
        "ZEROMERMA_TEST_RUN_ID": run_id,
        "ZEROMERMA_TEST_DESTRUCTIVE_CONFIRMATION": f"ALLOW_ZEROMERMA_DESTRUCTIVE_TESTS:{run_id}",
        "ZEROMERMA_TEST_DATABASE_URL": (
            f"postgresql+psycopg://zeromerma_test_runner:{credential}"
            f"@127.0.0.1:55432/{database}?application_name={database}"
        ),
        "ZEROMERMA_API_DATABASE_URL": "postgresql+psycopg://operational@localhost/zeromerma",
        "ZM_WEB_INTEGRATION_ISOLATED": "1",
        "ZM_E2E_RUN_ID": run_id,
        "ZM_E2E_PASSWORD": credential,
    }
    if scenario == "operational_database":
        environment["ZEROMERMA_TEST_DATABASE_URL"] = environment[
            "ZEROMERMA_TEST_DATABASE_URL"
        ].replace(f"/{database}?", "/zeromerma?")
    elif scenario == "missing_test_url":
        del environment["ZEROMERMA_TEST_DATABASE_URL"]
    elif scenario == "missing_isolated_flag":
        del environment["ZM_WEB_INTEGRATION_ISOLATED"]
    elif scenario == "mismatched_run":
        environment["ZM_E2E_RUN_ID"] = "different_run_identity"
    elif scenario == "short_credential":
        environment["ZM_E2E_PASSWORD"] = "short"
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    create_engine = MagicMock(side_effect=AssertionError("Unsafe seed attempted engine creation"))
    monkeypatch.setattr("sqlalchemy.create_engine", create_engine)

    with pytest.raises(RuntimeError, match=expected_message) as error:
        runpy.run_path(str(ROOT / "scripts/dev/seed-web-integration.py"), run_name="__main__")

    create_engine.assert_not_called()
    assert credential not in str(error.value)
