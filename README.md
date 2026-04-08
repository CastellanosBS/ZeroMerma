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

POS web workstation configuration:

```powershell
Copy-Item apps\pos-web\.env.example apps\pos-web\.env
```

The canonical local workstation is `POS-01`.

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
It also seeds the local Phase 1A cashier, branch, workstation, and branch assignment data.

Local URLs:

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Health endpoint: `http://localhost:8000/health`
- POS web: `http://localhost:5173`
- POS web alternate loopback origin: `http://127.0.0.1:5173`
- Backoffice web: `http://localhost:5174`
- Backoffice web alternate loopback origin: `http://127.0.0.1:5174`

Canonical local browser-to-API setup:

- Keep the API on `http://localhost:8000`.
- The backend CORS allowlist explicitly supports POS and backoffice browser origins on both `localhost` and `127.0.0.1` for ports `5173` and `5174`.
- If you override `ZEROMERMA_API_CORS_ORIGINS`, keep it as an explicit JSON array in `.env`; do not use `*`.

## Manual Startup

Use this when you want individual process control:

```powershell
docker compose -f infra\docker\docker-compose.yml up -d postgres
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/api python scripts/bootstrap/seed-local-data.py
uv run --project apps/api uvicorn zeromerma_api.main:create_app --factory --app-dir apps/api/src --reload --host 0.0.0.0 --port 8000
uv run --project apps/worker python -m zeromerma_worker
pnpm --filter @zeromerma/pos-web dev
pnpm --filter @zeromerma/backoffice-web dev
```

## Local Seed Data

The canonical local bootstrap seeds:

- Branch: `MAIN` / `Main Branch` / `America/Hermosillo`
- Workstation: `POS-01` / `Front Register 01`
- Cashier user: `cashier@zeromerma.local`
- Password: `ChangeMe123!`

Do not replace this with ad hoc local data when validating the Phase 1A POS slice.

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
It also seeds the local Phase 1A data before running the backend test suite.

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

Manual API validation for Phase 1A:

```powershell
$login = Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/auth/login -ContentType "application/json" -Body '{"email":"cashier@zeromerma.local","password":"ChangeMe123!"}'
$token = $login.access_token
$headers = @{ Authorization = "Bearer $token"; "X-Request-ID" = "manual-phase-1a-check" }
Invoke-RestMethod -Uri http://localhost:8000/v1/auth/me -Headers $headers
Invoke-RestMethod -Uri "http://localhost:8000/v1/pos/bootstrap?workstation_code=POS-01" -Headers $headers
Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/cash-sessions/open -Headers $headers -ContentType "application/json" -Body '{"workstation_code":"POS-01","opening_amount":"150.00"}'
Invoke-RestMethod -Uri "http://localhost:8000/v1/cash-sessions/current?workstation_code=POS-01" -Headers $headers
```

Manual POS validation for Phase 1B:

1. Copy `apps\pos-web\.env.example` to `apps\pos-web\.env`.
2. Start the stack with `.\scripts\dev\start-local.ps1`.
3. Open `http://localhost:5173` or `http://127.0.0.1:5173`.
4. Sign in with `cashier@zeromerma.local` / `ChangeMe123!`.
5. Confirm the open screen shows branch, workstation, operator, local date/time, and the opening amount input.
6. Enter `150.00` and submit.
7. Confirm the active cash-session state is shown.
8. Refresh the browser and confirm the active session state is preserved.

Optional Playwright e2e smoke tests:

```powershell
pnpm test:e2e
```

## Database Reset

This deletes the local PostgreSQL volume, reruns migrations, and reseeds the local Phase 1A data:

```powershell
.\scripts\dev\reset-db.ps1 -Force
```
