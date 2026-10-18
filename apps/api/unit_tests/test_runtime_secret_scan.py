from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from zeromerma_api.core.runtime_secret_cli import main
from zeromerma_api.core.runtime_secret_scan import scan_content
from zeromerma_api.core.runtime_secrets import write_private_secret


def test_secret_scan_checks_index_worktree_and_logs_without_echoing_material(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "--quiet", str(repository)], check=True)
    secret = "test-only-dynamic-material-a7f9013cc21d"
    private_file = tmp_path / "credential"
    write_private_secret(private_file, secret)
    tracked = repository / "configuration.txt"
    tracked.write_text(secret, encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "configuration.txt"], check=True)
    tracked.write_text("clean working copy", encoding="utf-8")
    artifact = tmp_path / "log.txt"
    artifact.write_text("error=" + secret, encoding="utf-8")
    arguments = [
        "scan",
        "--repository",
        str(repository),
        "--secret-file",
        str(private_file),
        "--artifact",
        str(artifact),
    ]
    assert main(arguments) == 1
    output = capsys.readouterr().out
    assert secret not in output
    report = json.loads(output)
    assert report["findings"] == ["index:configuration.txt", "artifact:" + str(artifact)]
    subprocess.run(["git", "-C", str(repository), "add", "configuration.txt"], check=True)
    artifact.write_text("clean log", encoding="utf-8")
    assert main(arguments) == 0


def test_secret_scan_detects_pem_private_keys_without_a_supplied_inventory() -> None:
    assert scan_content(b"-----BEGIN " + b"PRIVATE KEY-----\nprivate-material", [])
    assert scan_content(b"__Host-zm-pos-session=" + b"a" * 43 + b"; Secure", [])
    assert not scan_content(b"public certificate and safe status", [])
