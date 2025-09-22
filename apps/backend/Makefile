# apps/backend/Makefile

.PHONY: run lint test format

run:
\tpoetry run uvicorn zeromerma_api.main:app --reload --host 0.0.0.0 --port $${PORT:-8000}

lint:
\tpoetry run ruff check .
\tpoetry run black --check .

format:
\tpoetry run ruff check . --fix
\tpoetry run black .

test:
\tpoetry run pytest -q
