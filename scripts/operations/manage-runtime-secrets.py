"""Run from the canonical API workspace; secret values are never command-line arguments."""

from zeromerma_api.core.runtime_secret_cli import main

if __name__ == "__main__":
    raise SystemExit(main())
