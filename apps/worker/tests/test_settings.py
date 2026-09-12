import pytest
from pydantic import ValidationError

from zeromerma_worker.core.config import WorkerSettings


def test_worker_settings_have_safe_foundation_defaults() -> None:
    settings = WorkerSettings()

    assert settings.environment == "local"
    assert settings.batch_size > 0
    assert settings.poll_interval_seconds > 0
    assert settings.database_connect_timeout_seconds == 5


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("BATCH_SIZE", "0"),
        ("BATCH_SIZE", "501"),
        ("POLL_INTERVAL_SECONDS", "0"),
        ("DATABASE_CONNECT_TIMEOUT_SECONDS", "0"),
        ("DATABASE_CONNECT_TIMEOUT_SECONDS", "61"),
        ("LOG_LEVEL", "verbose"),
        ("DATABASE_URL", "not-a-url"),
        ("DATABASE_URL", "sqlite:///worker.db"),
        ("DATABASE_URL", "postgresql+psycopg://localhost"),
        ("DATABASE_URL", "postgresql+psycopg://localhost:99999/worker"),
    ],
)
def test_invalid_worker_settings_fail_before_runtime(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(f"ZEROMERMA_WORKER_{name}", value)
    with pytest.raises(ValidationError):
        WorkerSettings()


def test_worker_environment_overrides_and_normalizes_log_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ZEROMERMA_WORKER_ENVIRONMENT", "test")
    monkeypatch.setenv("ZEROMERMA_WORKER_LOG_LEVEL", "debug")
    monkeypatch.setenv("ZEROMERMA_WORKER_BATCH_SIZE", "17")
    monkeypatch.setenv("ZEROMERMA_WORKER_POLL_INTERVAL_SECONDS", "2")
    monkeypatch.setenv("ZEROMERMA_WORKER_DATABASE_CONNECT_TIMEOUT_SECONDS", "3")
    settings = WorkerSettings()
    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.batch_size == 17
    assert settings.poll_interval_seconds == 2
    assert settings.database_connect_timeout_seconds == 3
