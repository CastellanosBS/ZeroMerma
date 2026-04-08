from zeromerma_worker.core.config import WorkerSettings


def test_worker_settings_have_safe_foundation_defaults() -> None:
    settings = WorkerSettings()

    assert settings.environment == "local"
    assert settings.batch_size > 0
    assert settings.poll_interval_seconds > 0
