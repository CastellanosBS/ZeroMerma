from __future__ import annotations

import logging
import signal
import socket
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import OperationalError

import zeromerma_worker.main as worker_main
from zeromerma_worker.core.config import WorkerSettings
from zeromerma_worker.db.session import create_worker_engine


@pytest.fixture
def runtime(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, MagicMock]:
    engine = MagicMock()
    poller = MagicMock()
    monkeypatch.setattr(worker_main, "configure_logging", lambda level: None)
    monkeypatch.setattr(worker_main, "create_worker_engine", lambda settings: engine)
    monkeypatch.setattr(worker_main, "OutboxPoller", lambda **kwargs: poller)
    return engine, poller


def test_once_polls_exactly_once_and_disposes_engine(
    runtime: tuple[MagicMock, MagicMock], caplog: pytest.LogCaptureFixture
) -> None:
    engine, poller = runtime
    caplog.set_level(logging.INFO)
    assert worker_main.run_worker(WorkerSettings(), once=True, skip_db_check=False) == 0
    poller.poll_once.assert_called_once_with()
    engine.dispose.assert_called_once_with()
    assert [record.message for record in caplog.records] == ["worker_booted", "worker_stopped"]
    assert caplog.records[-1].reason == "poll_once_completed"


def test_skip_db_check_opens_no_engine(
    monkeypatch: pytest.MonkeyPatch, runtime: tuple[MagicMock, MagicMock]
) -> None:
    engine, poller = runtime
    create_engine = MagicMock(side_effect=AssertionError("database must remain unopened"))
    monkeypatch.setattr(worker_main, "create_worker_engine", create_engine)
    assert worker_main.run_worker(WorkerSettings(), once=False, skip_db_check=True) == 0
    create_engine.assert_not_called()
    poller.poll_once.assert_not_called()
    engine.dispose.assert_not_called()


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
def test_termination_signal_stops_loop_and_restores_handler(
    runtime: tuple[MagicMock, MagicMock], signum: signal.Signals
) -> None:
    engine, poller = runtime
    previous_handler = signal.getsignal(signum)
    poller.poll_once.side_effect = lambda: signal.raise_signal(signum)
    assert worker_main.run_worker(WorkerSettings(), once=False, skip_db_check=False) == 0
    poller.poll_once.assert_called_once_with()
    engine.dispose.assert_called_once_with()
    assert signal.getsignal(signum) == previous_handler


def test_keyboard_interrupt_disposes_engine(runtime: tuple[MagicMock, MagicMock]) -> None:
    engine, poller = runtime
    poller.poll_once.side_effect = KeyboardInterrupt
    assert worker_main.run_worker(WorkerSettings(), once=False, skip_db_check=False) == 0
    engine.dispose.assert_called_once_with()


def test_database_failure_exits_nonzero_without_exposing_driver_details(
    runtime: tuple[MagicMock, MagicMock], caplog: pytest.LogCaptureFixture
) -> None:
    engine, poller = runtime
    poller.poll_once.side_effect = OperationalError(
        "SELECT private_payload", {"password": "private-password"}, RuntimeError("private-driver")
    )
    caplog.set_level(logging.INFO)
    assert worker_main.run_worker(WorkerSettings(), once=True, skip_db_check=False) == 1
    engine.dispose.assert_called_once_with()
    assert "worker_database_error" in caplog.text
    assert "private" not in caplog.text
    assert caplog.records[-1].reason == "database_error"


def test_unexpected_failure_is_not_reported_successful_and_releases_engine(
    runtime: tuple[MagicMock, MagicMock],
) -> None:
    engine, poller = runtime
    poller.poll_once.side_effect = RuntimeError("unexpected")
    with pytest.raises(RuntimeError, match="unexpected"):
        worker_main.run_worker(WorkerSettings(), once=True, skip_db_check=False)
    engine.dispose.assert_called_once_with()


def test_engine_bounds_connection_attempt_without_connecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = MagicMock()
    monkeypatch.setattr("zeromerma_worker.db.session.create_engine", factory)
    settings = WorkerSettings(database_connect_timeout_seconds=3)
    assert create_worker_engine(settings) is factory.return_value
    factory.assert_called_once_with(
        settings.database_url, pool_pre_ping=True, connect_args={"connect_timeout": 3}
    )


def test_cli_boots_and_exits_without_database(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "zeromerma_worker", "--once", "--skip-db-check"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert '"message":"worker_booted"' in result.stderr
    assert '"reason":"database_check_skipped"' in result.stderr


def test_invalid_cli_configuration_is_nonzero_and_redacted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ZEROMERMA_WORKER_DATABASE_URL", "invalid-private-password")
    result = subprocess.run(
        [sys.executable, "-m", "zeromerma_worker", "--once", "--skip-db-check"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 2
    assert "worker_configuration_error" in result.stderr
    assert "database_url" in result.stderr
    assert "private-password" not in result.stderr


def test_actual_database_unavailable_exits_without_secrets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Reserve a loopback port without listening: no database can receive this connection.
    with socket.socket() as unavailable_endpoint:
        unavailable_endpoint.bind(("127.0.0.1", 0))
        port = unavailable_endpoint.getsockname()[1]
        monkeypatch.setenv(
            "ZEROMERMA_WORKER_DATABASE_URL",
            f"postgresql+psycopg://unit:private-password@127.0.0.1:{port}/unavailable",
        )
        monkeypatch.setenv("ZEROMERMA_WORKER_DATABASE_CONNECT_TIMEOUT_SECONDS", "1")
        result = subprocess.run(
            [sys.executable, "-m", "zeromerma_worker", "--once"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    assert result.returncode == 1
    assert '"message":"worker_database_error"' in result.stderr
    assert '"reason":"database_error"' in result.stderr
    assert "private-password" not in result.stderr
