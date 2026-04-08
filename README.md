# ZeroMerma

Canonical greenfield monorepo for a multi-branch bakery operations platform.

## Strategic Principles

- One canonical architecture
- No legacy coexistence
- Backend is the source of truth for contracts
- Separate POS web and backoffice web
- Independent worker
- Auditability and traceability first
- Clean runway for inventory, production, purchasing, transfers, analytics, and AI/ML

## Workspace

- `apps/api`: FastAPI backend, SQLAlchemy, Alembic, vertical-slice modules, OpenAPI source of truth
- `apps/worker`: independent Python worker for transactional outbox polling
- `apps/pos-web`: POS React application on port `5173`
- `apps/backoffice-web`: backoffice React application on port `5174`
- `packages/api-client`: generated TypeScript contracts from backend OpenAPI
- `packages/ui`: shared UI primitives
- `packages/eslint-config`: shared ESLint flat config
- `packages/typescript-config`: shared TypeScript config
- `infra/docker`: local PostgreSQL

## Prerequisites

- Python `3.12`
- `uv` installed globally and available as `uv` in PowerShell
- Node.js `22`
- `pnpm` `9.15.4`
- Docker with Docker Compose
- Windows PowerShell for local scripts

Do not work from a random external Python virtual environment. ZeroMerma scripts resolve the `uv` CLI directly and let `uv` manage the repository `.venv`.

## Windows Setup

Install `uv` globally:

```powershell
winget install --id Astral-sh.UV
```

If `winget` is unavailable, use the official installer:

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Open a new PowerShell terminal and verify the required tools:

```powershell
uv --version
node --version
corepack enable
corepack prepare pnpm@9.15.4 --activate
pnpm --version
docker --version
docker compose version
```

## First-Time Setup

Run from the repository root:

```powershell
uv sync --all-packages --dev
pnpm install
pnpm contracts:generate
```

Install the Chromium browser for Playwright e2e smoke tests when needed:

```powershell
pnpm --filter @zeromerma/pos-web exec playwright install chromium
```

## Start Locally

Start PostgreSQL, run migrations, and open separate terminals for the API, worker, POS web, and backoffice web:

```powershell
.\scripts\dev\start-local.ps1
```

The script runs `uv sync --all-packages --dev`, installs Node dependencies with `pnpm install --frozen-lockfile`, regenerates API contracts, starts PostgreSQL, applies Alembic migrations, and launches the four local processes.

Local URLs:

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Health endpoint: `http://localhost:8000/health`
- POS web: `http://localhost:5173`
- Backoffice web: `http://localhost:5174`

## Manual Startup

Use this when you want individual process control:

```powershell
docker compose -f infra\docker\docker-compose.yml up -d postgres
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/api uvicorn zeromerma_api.main:create_app --factory --app-dir apps/api/src --reload --host 0.0.0.0 --port 8000
uv run --project apps/worker python -m zeromerma_worker
pnpm --filter @zeromerma/pos-web dev
pnpm --filter @zeromerma/backoffice-web dev
```

## Contracts

Backend OpenAPI is the source of truth. Regenerate TypeScript contracts with:

```powershell
pnpm contracts:generate
```

This writes:

- `packages/api-client/openapi.json`
- `packages/api-client/src/generated/schema.ts`

Do not handwrite shared domain types between Python and TypeScript.

## Validation

Run the foundation checks without requiring a running database:

```powershell
.\scripts\dev\check-foundation.ps1
```

This script starts PostgreSQL, waits for readiness, applies migrations, verifies the API health endpoint, verifies worker bootability, and verifies both web apps through lint/test/build and bounded Vite boot checks.

Individual commands:

```powershell
uv run ruff check apps/api/src apps/api/tests apps/worker/src apps/worker/tests
uv run mypy apps/api/src apps/worker/src
uv run pytest
uv run --project apps/worker python -m zeromerma_worker --once --skip-db-check
pnpm contracts:generate
pnpm lint
pnpm test
pnpm build
docker compose -f infra\docker\docker-compose.yml config
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/worker python -m zeromerma_worker --once
```

Optional Playwright e2e smoke tests:

```powershell
pnpm test:e2e
```

## Database Reset

This deletes the local PostgreSQL volume and reruns migrations:

```powershell
.\scripts\dev\reset-db.ps1 -Force
```
