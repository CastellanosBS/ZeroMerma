# ZeroMerma

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Framework-teal.svg)](https://fastapi.tiangolo.com/)
[![Poetry](https://img.shields.io/badge/Poetry-Dependencies-purple.svg)](https://python-poetry.org/)
[![Ruff](https://img.shields.io/badge/Linter-Ruff-informational.svg)](https://docs.astral.sh/ruff/)
[![Tests](https://img.shields.io/badge/Tests-Pytest-success.svg)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/License-TBD-lightgrey.svg)](#license)

Data‑driven, multi‑branch **bakery management system** (operations + analytics) built as a modern monorepo. The goal is operational excellence (≈ zero waste) across branches through clean processes, reliable data, and actionable insights.

---

## Table of Contents

-   [Vision & Scope](#vision--scope)
-   [Core Modules](#core-modules)
-   [Tech Stack](#tech-stack)
-   [Repository Layout](#repository-layout)
-   [Quickstart](#quickstart)
-   [Configuration](#configuration)
    -   [Environment Variables (`.env`)](#environment-variables-env)
-   [Quality Gates](#quality-gates)
    -   [Formatting & Linting](#formatting--linting)
    -   [Git Hooks (`pre-commit`)](#git-hooks-pre-commit)
    -   [Tests](#tests)
-   [Database & Migrations](#database--migrations)
-   [Conventions](#conventions)
    -   [Branching](#branching)
    -   [Commit Messages (Conventional Commits)](#commit-messages-conventional-commits)
-   [Roadmap](#roadmap)
-   [Troubleshooting](#troubleshooting)
-   [Examples](#examples)
-   [License](#license)
-   [Maintainers](#maintainers)

---

## Vision & Scope

ZeroMerma provides an end‑to‑end operational backbone for a multi‑branch bakery:

-   **Operations:** inventory, purchases, production, sales (POS), inter‑branch transfers, cash sessions.
-   **Analytics (phase II):** telemetry/IoT capture, demand & production forecasting, reporting.
-   **Governance:** roles/permissions, audit fields, soft deletes, data retention.

Target outcomes: reduced waste, accurate costing, reliable stock rotation (FIFO/PEPS), and decision‑quality data.

## Core Modules

-   **Branches & Users:** branches, roles/permissions, auth, audit trails.
-   **Catalogs:** products, recipes/BOM, units of measure (UoM) & conversions.
-   **Inventory:** stock per branch & location, lot/expiry tracking, cost method (FIFO/Avg).
-   **Purchases:** suppliers, POs, receipts, price & tax history.
-   **Sales (POS):** tickets, payments, discounts, tax rates, cash sessions (open/close).
-   **Production:** work orders, ingredient consumption, finished goods, scrap.
-   **Transfers:** inter‑branch movements, approvals, reconciliation.
-   **Telemetry (IoT):** sensors (temperature, humidity, people counting), time‑series storage.
-   **Forecasting:** demand predictions per branch/product/date, model versioning & confidence.

> Full ER model and specs are in `/docs/requirements/` (PDFs/diagrams).

## Tech Stack

-   **Backend:** Python 3.12+, FastAPI, Uvicorn
-   **Config:** Pydantic & pydantic‑settings
-   **Quality:** Ruff, Black, Pytest, pre‑commit
-   **Packaging:** Poetry
-   **DB (planned):** PostgreSQL 16/17 (+ TimescaleDB for telemetry), SQLAlchemy 2.x + Alembic
-   **Realtime & Jobs (planned):** WebSockets, Celery + Redis
-   **Frontend (planned):** TBD

## Repository Layout

```text
ZeroMerma/
├─ apps/
│  ├─ backend/
│  │  ├─ pyproject.toml
│  │  ├─ .pre-commit-config.yaml
│  │  ├─ .ruff.toml
│  │  ├─ README.md
│  │  └─ src/
│  │     └─ zeromerma_api/
│  │        └─ main.py
│  └─ frontend/            # placeholder for future UI
├─ docs/
│  └─ requirements/        # DB PDFs, ER diagrams, specs
├─ infra/                  # IaC / ops (WIP)
├─ ci/                     # CI pipelines (WIP)
├─ data/                   # seeds/samples (WIP)
├─ .vscode/
└─ .editorconfig
```

> Avoid sharing `.git/` in public archives. Ensure `.gitignore` includes `.env`, build artifacts, and local caches.

## Quickstart

```bash
# 1) Clone
git clone <https://github.com/CastellanosBS/ZeroMerma.git> && cd ZeroMerma

# 2) Backend setup
cd apps/backend
poetry install
poetry run pre-commit install

# 3) Run API (dev)
poetry run uvicorn zeromerma_api.main:app --reload
# Swagger UI: http://127.0.0.1:8000/docs

# 4) Run tests
poetry run pytest -q
```

## Configuration

### Environment Variables (`.env`)

Create `apps/backend/.env`:

```ini
# App
APP_NAME=ZeroMerma API
APP_ENV=development
APP_VERSION=0.1.0
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Security
SECRET_KEY=change-me

# Database (future ORM/Alembic)
DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/zeromerma

# Telemetry (optional, future)
REDIS_URL=redis://localhost:6379/0
```

Use **pydantic‑settings** to load this configuration into a `Settings` class.

## Quality Gates

### Formatting & Linting

```bash
poetry run ruff check .
poetry run ruff format .    # or: poetry run black . (if Black is configured)
```

### Git Hooks (`pre-commit`)

```bash
poetry run pre-commit run --all-files
```

### Tests

```bash
poetry run pytest -q
```

Recommended minimum:

-   `tests/test_health.py` — returns `200 OK`
-   `tests/test_version.py` — exposes app version

## Database & Migrations

-   ER model and detailed table specs live in `/docs/requirements/` (PDFs/diagrams).
-   Planned stack: **SQLAlchemy 2.x** + **Alembic** for migrations.
-   Suggested first migration: Branch/Role/User/Auth + audit fields.
-   Inventory invariants via DB constraints + lightweight triggers; nightly reconciliation job.

## Conventions

### Branching

-   `main`: stable, release‑ready
-   `develop` (optional): integration branch
-   Short‑lived topic branches: `feat/*`, `fix/*`, `chore/*` merged via PR

### Commit Messages (Conventional Commits)

```text
feat(inventory): add lot/expiry tracking to stock ledger
fix(pos): correct VAT rounding on mixed‑rate tickets
chore(ci): enable pre-commit in pipeline
docs(db): document UoM conversion strategy
refactor(api): split services by bounded context
test(forecast): add baseline model tests
```

## Roadmap

**MVP**

-   Health/version endpoints & tests
-   Config via pydantic‑settings
-   CI (lint + tests)
-   Auth (JWT) and basic RBAC

**Operations**

-   Products, UoM & conversions, suppliers
-   Inventory ledger (FIFO), purchases, production, transfers
-   POS tickets & cash sessions (unique open‑per‑branch)

**Analytics**

-   Telemetry ingestion (TimescaleDB)
-   Forecasting service (demand per branch/product)
-   Reporting/BI views and indices

## Troubleshooting

-   Poetry errors: ensure `pyproject.toml` is valid TOML (remove any placeholder lines like `...`).
-   Import errors: run commands from `apps/backend` and reference the app as `zeromerma_api.main:app`.
-   CORS: update `CORS_ORIGINS` in `.env` to include your frontend dev URL.

## Examples

**`tests/test_health.py`**

```python
# apps/backend/tests/test_health.py
from fastapi.testclient import TestClient
from zeromerma_api.main import app

client = TestClient(app)

def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
```

**`tests/test_version.py`**

```python
# apps/backend/tests/test_version.py
from fastapi.testclient import TestClient
from zeromerma_api.main import app

client = TestClient(app)

def test_version_exposed():
    r = client.get("/version")
    assert r.status_code == 200
    payload = r.json()
    assert "version" in payload and isinstance(payload["version"], str)
```

**Minimal endpoints to support the tests**

```python
# apps/backend/src/zeromerma_api/main.py
from fastapi import FastAPI

app = FastAPI(title="ZeroMerma API", version="0.1.0")

@app.get("/", tags=["meta"])
def root():
    return {"message": "Welcome to ZeroMerma API"}

@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}

@app.get("/version", tags=["meta"])
def version():
    return {"version": app.version}
```

## License

TBD. Until defined, all rights reserved to the project owner.

## Maintainers

-   **Sergio Castellanos** — Product Owner

Contributions welcome via pull requests.
