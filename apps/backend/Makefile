.PHONY: run lint test format seed  # declare phony targets so make doesn't look for files

run:
	poetry run uvicorn zeromerma_api.main:app --reload --host 0.0.0.0 --port $${PORT:-8000}

lint:
	poetry run ruff check .
	poetry run black --check .

format:
	poetry run ruff check . --fix
	poetry run black .

test:
	poetry run pytest -q

seed:
	poetry run python seed.py
