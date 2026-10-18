"""Scan Git index/worktree and explicit unpacked artifacts without printing secret values."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from zeromerma_api.core.runtime_secrets import read_private_secret

_PRIVATE_KEY = re.compile(rb"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")
_SESSION_COOKIE = re.compile(
    rb"__Host-zm-(?:pos|backoffice)-session=[A-Za-z0-9_-]{43}(?=[;\s\"']|$)"
)
_MAX_FILE_BYTES = 64 * 1024 * 1024


def secret_needles(secret_files: list[Path]) -> list[bytes]:
    needles: set[bytes] = set()
    for path in secret_files:
        value = read_private_secret(path)
        needles.add(value.encode("utf-8"))
        try:
            parsed = make_url(value)
        except ArgumentError:
            continue
        if parsed.password:
            needles.add(parsed.password.encode("utf-8"))
    return sorted(needles)


def scan_content(content: bytes, needles: list[bytes]) -> bool:
    return (
        bool(_PRIVATE_KEY.search(content) or _SESSION_COOKIE.search(content))
        or any(needle in content for needle in needles)
    )


def _git(repository: Path, *arguments: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments], capture_output=True, check=False
    )
    if result.returncode:
        raise ValueError("The requested Git scan could not be completed.")
    return result.stdout


def scan_repository(
    repository: Path, *, secret_files: list[Path], artifacts: list[Path]
) -> dict[str, object]:
    repository = repository.resolve(strict=True)
    needles = secret_needles(secret_files)
    findings: list[str] = []
    inspected = 0

    def check(label: str, content: bytes) -> None:
        nonlocal inspected
        if len(content) > _MAX_FILE_BYTES:
            raise ValueError("Scan inputs must be unpacked files smaller than 64 MiB.")
        inspected += 1
        if scan_content(content, needles):
            findings.append(label)

    for name in _git(repository, "ls-files", "--cached", "-z").split(b"\0"):
        if not name:
            continue
        relative = name.decode("utf-8")
        check("index:" + relative, _git(repository, "show", ":" + relative))
        path = repository / relative
        if path.exists():
            if path.is_symlink() or not path.resolve().is_relative_to(repository):
                raise ValueError("Scan inputs must not escape the repository through symlinks.")
            if path.stat().st_size > _MAX_FILE_BYTES:
                raise ValueError("Scan inputs must be smaller than 64 MiB.")
            check("worktree:" + relative, path.read_bytes())
    for artifact in artifacts:
        if artifact.is_symlink() or not artifact.is_file():
            raise ValueError("Each artifact must be an explicit unpacked regular file.")
        if artifact.stat().st_size > _MAX_FILE_BYTES:
            raise ValueError("Scan inputs must be smaller than 64 MiB.")
        check("artifact:" + str(artifact), artifact.read_bytes())
    return {
        "passed": not findings,
        "inspected_files": inspected,
        "supplied_secret_files": len(secret_files),
        "findings": findings,
        "scope": "Git index/worktree and explicit unpacked files; no history or image layers",
    }
