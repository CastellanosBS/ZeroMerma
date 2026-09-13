from __future__ import annotations

from pathlib import Path

import pytest

from zeromerma_api.modules.identity import cli


def test_recovery_file_is_private_roundtrips_and_never_overwrites(tmp_path: Path) -> None:
    path = tmp_path / "owner-recovery.json"
    material = "private-test-material-" * 4
    cli.write_recovery_file(path, host="test-control-plane", material=material)
    assert cli.read_recovery_file(path) == {
        "authorized_host": "test-control-plane",
        "recovery_material": material,
    }
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        cli.write_recovery_file(path, host="test-control-plane", material="replacement" * 8)
    assert path.read_bytes() == before


def test_failed_permission_hardening_removes_empty_reserved_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "failed-recovery.json"

    def reject_permissions(path: Path, *, protect: bool) -> None:
        assert protect
        assert path.read_bytes() == b""
        raise ValueError("Controlled permission rejection")

    monkeypatch.setattr(cli, "_private_permissions", reject_permissions)
    with pytest.raises(ValueError, match="Controlled permission rejection"):
        cli.write_recovery_file(path, host="test", material="test-material-" * 8)
    assert not path.exists()


def test_invalid_private_recovery_json_is_rejected_without_echoing_contents(tmp_path: Path) -> None:
    path = tmp_path / "invalid-recovery.json"
    cli.write_recovery_file(path, host="test", material="short")
    with pytest.raises(ValueError, match="Recovery file is invalid"):
        cli.read_recovery_file(path)


def test_cli_has_no_secret_argument_or_web_recovery_mode() -> None:
    with pytest.raises(SystemExit):
        cli._parser().parse_args(
            ["recover-second-superadmin", "--recovery-material", "not-accepted"]
        )
    with pytest.raises(SystemExit):
        cli._parser().parse_args(["bootstrap-owner", "--password", "not-accepted"])
