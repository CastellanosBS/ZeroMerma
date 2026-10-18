from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HELPER = ROOT / "scripts/powershell/ZeroMerma.ValidationArtifacts.ps1"


def _publish(source: Path, destination: Path, wrapper: Path) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("pwsh")
    assert executable is not None, "Artifact validation requires PowerShell 7"
    wrapper.write_text(
        "param([string]$SourceDirectory,[string]$DestinationDirectory)\n"
        "$ErrorActionPreference='Stop'\n"
        ". '" + str(HELPER).replace("'", "''") + "'\n"
        "Protect-ZeroMermaValidationArtifacts -SourceDirectory $SourceDirectory "
        "-DestinationDirectory $DestinationDirectory\n",
        encoding="utf-8",
    )
    return subprocess.run(
        [
            executable,
            "-NoProfile",
            "-File",
            str(wrapper),
            "-SourceDirectory",
            str(source),
            "-DestinationDirectory",
            str(destination),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_actual_pytest_failure_is_preserved_without_credentials_in_published_artifacts(
    tmp_path: Path,
) -> None:
    source = tmp_path / "raw"
    destination = tmp_path / "published"
    source.mkdir()
    credentials = {
        "ARTIFACT_COOKIE": secrets.token_urlsafe(32),
        "ARTIFACT_CSRF": secrets.token_hex(32),
        "ARTIFACT_RESET": secrets.token_urlsafe(32),
        "ARTIFACT_PASSWORD": secrets.token_urlsafe(32),
    }
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    failed_test = tmp_path / "test_controlled_failure.py"
    failed_test.write_text(
        "import os\n"
        "def test_controlled_404():\n"
        "    headers = {'Cookie': '__Host-zm-backoffice-session=' + os.environ['ARTIFACT_COOKIE'], "
        "'X-CSRF-Token': os.environ['ARTIFACT_CSRF']}\n"
        "    body = {'csrf_token': os.environ['ARTIFACT_CSRF'], "
        "'reset_token': os.environ['ARTIFACT_RESET'], "
        "'password': os.environ['ARTIFACT_PASSWORD']}\n"
        "    print(headers)\n"
        "    print(body)\n"
        "    assert {'status': 404, **headers, **body} == {'status': 200}\n",
        encoding="utf-8",
    )
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str(tmp_path / "pytest.ini"),
            str(failed_test),
            "-q",
            "-o",
            "junit_logging=all",
            "--junitxml=" + str(source / "result.xml"),
        ],
        cwd=tmp_path,
        env={**os.environ, **credentials},
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert process.returncode == 1
    raw = process.stdout + process.stderr
    assert all(value in raw for value in credentials.values())
    (source / "failure.log").write_text(raw, encoding="utf-8")
    (source / "quoted-password.log").write_text(
        "password=" + repr("quoted'\\\" " + credentials["ARTIFACT_PASSWORD"]),
        encoding="utf-8",
    )
    (source / "result.json").write_text(
        json.dumps(
            {
                "passed": False,
                "exit_code": 1,
                "password": credentials["ARTIFACT_PASSWORD"],
                "message": 'X-CSRF-Token: "' + credentials["ARTIFACT_CSRF"] + '"',
                "optional": [None, 0, "unchanged"],
            }
        ),
        encoding="utf-8",
    )
    (source / "tls").mkdir()
    (source / "tls" / "localhost.key.pem").write_text(credentials["ARTIFACT_COOKIE"])
    (source / "trace.zip").write_bytes(credentials["ARTIFACT_COOKIE"].encode())
    console_wrapper = tmp_path / "console.ps1"
    console_wrapper.write_text(
        "param([string]$Python,[string]$TestPath,[string]$Config,[string]$Capture)\n"
        "$ErrorActionPreference='Stop'\n"
        ". '" + str(HELPER).replace("'", "''") + "'\n"
        "$code = Invoke-ZeroMermaProtectedValidationProcess -FilePath $Python "
        "-ArgumentList @('-m','pytest','-c',$Config,$TestPath,'-q') -CaptureDirectory $Capture\n"
        "exit $code\n",
        encoding="utf-8",
    )
    protected_process = subprocess.run(
        [
            shutil.which("pwsh") or "pwsh",
            "-NoProfile",
            "-File",
            str(console_wrapper),
            "-Python",
            sys.executable,
            "-TestPath",
            str(failed_test),
            "-Config",
            str(tmp_path / "pytest.ini"),
            "-Capture",
            str(tmp_path / "private-console"),
        ],
        cwd=tmp_path,
        env={**os.environ, **credentials},
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert protected_process.returncode == 1
    safe_console = protected_process.stdout + protected_process.stderr
    assert "1 failed" in safe_console and "404" in safe_console
    assert all(value not in safe_console for value in credentials.values())
    assert not list((tmp_path / "private-console").rglob("*.capture"))
    before = (source / "result.xml").read_bytes()
    result = _publish(source, destination, tmp_path / "publish.ps1")
    assert result.returncode == 0, result.stderr
    assert (source / "result.xml").read_bytes() == before
    assert not (destination / "tls").exists()
    assert not (destination / "trace.zip").exists()
    for published in destination.rglob("*"):
        if published.is_file():
            content = published.read_text(encoding="utf-8")
            assert all(value not in content for value in credentials.values())
    xml = ET.parse(destination / "result.xml")
    suite = xml.find(".//testsuite")
    assert suite is not None and suite.attrib["failures"] == "1"
    assert xml.find(".//failure") is not None
    assert "404" in (destination / "failure.log").read_text(encoding="utf-8")
    report = json.loads((destination / "result.json").read_text(encoding="utf-8"))
    assert report["passed"] is False and report["exit_code"] == 1
    assert report["optional"] == [None, 0, "unchanged"]


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("partial.xml", "<testsuite><failure>"),
        ("partial.json", '{"passed":false,'),
        ("partial.log", "-----BEGIN " + "PRIVATE KEY-----\nunfinished"),
    ],
    ids=["invalid-xml", "invalid-json", "partial-private-key"],
)
def test_partial_artifacts_cannot_be_published(tmp_path: Path, name: str, content: str) -> None:
    source = tmp_path / "raw"
    source.mkdir()
    (source / name).write_text(content, encoding="utf-8")
    destination = tmp_path / "published"
    result = _publish(source, destination, tmp_path / "publish.ps1")
    assert result.returncode != 0
    assert not (destination / name).exists()


def test_publisher_rejects_overlapping_raw_and_destination_trees(tmp_path: Path) -> None:
    result = _publish(tmp_path, tmp_path / "published", tmp_path / "publish.ps1")
    assert result.returncode != 0
    assert "non-overlapping" in result.stderr
