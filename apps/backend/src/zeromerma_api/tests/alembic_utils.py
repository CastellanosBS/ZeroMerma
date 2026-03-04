# apps/backend/tests/alembic_utils.py
from __future__ import annotations

from pathlib import Path

from alembic.config import Config


def make_alembic_config() -> Config:
    """
    Build an Alembic Config that ALWAYS points to the repo's alembic.ini and migrations folder,
    regardless of where pytest is executed from.

    This prevents: "No 'script_location' key found in configuration."
    """
    backend_root = Path(__file__).resolve().parents[1]  # tests/ -> backend/
    ini_path = backend_root / "alembic.ini"

    cfg = Config(str(ini_path))

    # Defensive: ensure script_location is always set even if ini is edited later
    cfg.set_main_option("script_location", str(backend_root / "migrations"))

    return cfg
