from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from zeromerma_worker.core.config import get_settings


@pytest.fixture(autouse=True)
def isolated_worker_configuration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[None]:
    for name in os.environ:
        if name.startswith("ZEROMERMA_WORKER_"):
            monkeypatch.delenv(name)
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
