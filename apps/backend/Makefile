# ============================================================================
# ZeroMerma Backend - Canonical Developer Commands
# ============================================================================
# This Makefile is the official Unix-like command surface for local development
# and CI-friendly usage. On Windows/PowerShell, use tasks.ps1 for the same tasks.
# ============================================================================

.PHONY: help install precommit db-check db-upgrade seed-core seed-dev seed-inventory-fixture format lint test test-pos smoke ci-local

PYTHON := poetry run python
PYTEST := poetry run pytest
RUFF := poetry run ruff
BLACK := poetry run black
PRECOMMIT := poetry run pre-commit

help:
	@echo ""
	@echo "ZeroMerma Backend - Official Commands"
	@echo ""
	@echo "  make install                  Install dependencies"
	@echo "  make precommit                Install pre-commit hooks"
	@echo "  make db-check                 Check DB connectivity + Alembic state"
	@echo "  make db-upgrade               Apply Alembic migrations to head"
	@echo "  make seed-core                Seed minimum operable data"
	@echo "  make seed-dev                 Seed development data + sample POS transaction"
	@echo "  make seed-inventory-fixture   Seed deterministic inventory fixture"
	@echo "  make format                   Auto-format code"
	@echo "  make lint                     Run lint checks"
	@echo "  make test                     Run full test suite"
	@echo "  make test-pos                 Run POS-focused tests"
	@echo "  make smoke                    Run smoke tests"
	@echo "  make ci-local                 Run the local CI-equivalent pipeline"
	@echo ""

install:
	poetry install

precommit:
	$(PRECOMMIT) install

db-check:
	$(PYTHON) .\devcheck_db.py

db-upgrade:
	poetry run alembic upgrade head

seed-core:
	$(PYTHON) .\seed.py --profile core

seed-dev:
	$(PYTHON) .\seed.py --profile dev

seed-inventory-fixture:
	$(PYTHON) .\seed.py --profile inventory-fixture

format:
	$(RUFF) check src --fix
	$(BLACK) src

lint:
	$(RUFF) check src
	$(BLACK) --check src

test:
	$(PYTEST) -q

test-pos:
	$(PYTEST) -q \
		src/zeromerma_api/tests/test_cash_session_endpoints.py \
		src/zeromerma_api/tests/test_pos_sales_endpoints.py \
		src/zeromerma_api/tests/test_pos_payments_endpoints.py \
		src/zeromerma_api/tests/test_pos_server_side_pricing.py \
		src/zeromerma_api/tests/test_pos_inputs_not_sellable.py \
		src/zeromerma_api/tests/test_concurrency_inventory_balance.py

smoke:
	$(PYTEST) -q src/zeromerma_api/tests/test_smoke.py

ci-local: lint test
