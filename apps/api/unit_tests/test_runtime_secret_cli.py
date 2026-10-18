from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from zeromerma_api.core import runtime_secret_cli as cli
from zeromerma_api.core.runtime_secrets import read_private_secret, write_private_secret

OLD_URL = "postgresql+psycopg://runtime:private_old_password_qm8Ms77@localhost/isolated_staging"


def test_rotation_preserves_successor_after_uncertain_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    current = tmp_path / "current"
    successor = tmp_path / "successor"
    write_private_secret(current, OLD_URL)
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.commit.side_effect = RuntimeError("private-driver-content")
    monkeypatch.setattr(cli, "connect", lambda *args, **kwargs: connection)
    assert cli.rotate_database_credential(current, successor) == 2
    assert read_private_secret(current) == OLD_URL
    assert read_private_secret(successor) != OLD_URL
    assert "private-driver-content" not in capsys.readouterr().err


def test_rotation_connection_failure_removes_uncommitted_successor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    current = tmp_path / "current"
    successor = tmp_path / "successor"
    write_private_secret(current, OLD_URL)

    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("Connection was not established.")

    monkeypatch.setattr(cli, "connect", fail)
    with pytest.raises(RuntimeError):
        cli.rotate_database_credential(current, successor)
    assert not successor.exists()
    assert read_private_secret(current) == OLD_URL


def test_secret_cli_rejects_secret_values_in_command_arguments(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as rejected:
        cli.main(["store", "--output", "unused", "--value", "forbidden"])
    assert rejected.value.code == 2
    assert "forbidden" not in capsys.readouterr().err
