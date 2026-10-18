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

- Python `3.12.x` (canonical runtime line in `.python-version`)
- `uv` `0.11.4` (exact version enforced by `pyproject.toml`)
- Node.js `22.x` (canonical runtime line in `.node-version`)
- Corepack from the canonical Node.js distribution, explicitly enabled
- `pnpm` `10.33.0` (exact version and integrity in root `packageManager`)
- Docker with Docker Compose
- PowerShell 7 (`pwsh`) for canonical validation on Windows and Linux

Do not work from a random external Python virtual environment. ZeroMerma scripts resolve the `uv` CLI directly and let `uv` manage the repository `.venv`.

## Windows Setup

Install the exact canonical `uv` release with the versioned official installer:

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/0.11.4/install.ps1 | iex"
```

Open a new PowerShell terminal, install the canonical Python line if needed, enable Corepack, and prepare the pnpm version declared by `packageManager`:

```powershell
uv python install 3.12
corepack enable
$packageManager = (Get-Content -Raw package.json | ConvertFrom-Json).packageManager
$pnpmSpec = ([string]$packageManager).Split("+")[0]
corepack prepare $pnpmSpec --activate
```

The preflight is offline after those tools are prepared: it reads the versioned policy, resolves an already installed Python without downloading it, and rejects an incompatible runtime before installation.

```powershell
.\scripts\dev\check-toolchain.ps1
uv --version
uv python find --no-python-downloads 3.12
node --version
corepack --version
corepack pnpm --version
docker --version
docker compose version
```

## First-Time Setup

Run from the repository root:

```powershell
.\scripts\dev\check-toolchain.ps1
uv sync --all-packages --dev --frozen
corepack pnpm install --frozen-lockfile
uv run python -m compileall -q apps/api/src apps/worker/src
corepack pnpm typecheck
```

POS web workstation configuration:

```powershell
Copy-Item apps\pos-web\.env.example apps\pos-web\.env
```

The canonical local workstation is `POS-01`.

Install the Chromium browser for Playwright e2e smoke tests when needed:

```powershell
corepack pnpm --filter @zeromerma/pos-web exec playwright install chromium
```

## Start Locally

Use PowerShell 7 to start the development stack, including PostgreSQL, migrations,
API, worker, POS and Backoffice:

```powershell
.\scripts\dev\start-local.ps1
```

The script runs the canonical toolchain preflight and prepares the local development
database and seed. It launches background processes and records logs under
`.tmp/validation/local`. This local stack uses the development database; automated
validation uses the separate disposable harness described below.

Local URLs:

- API: `https://127.0.0.1:8000`
- Health endpoint: `https://127.0.0.1:8000/health`
- POS web: `https://127.0.0.1:5173`
- Backoffice web: `https://127.0.0.1:5174`

Canonical local browser-to-API setup:

- The launcher creates temporary loopback TLS material without installing system trust.
  An interactive browser may require approving that local certificate for each origin.
- POS and Backoffice sign in separately with Secure, HttpOnly cookies. Session restore
  uses the selected audience and does not create a session in the other application.
- `ZEROMERMA_API_CORS_ORIGINS` is an exact JSON allowlist; separate
  `SESSION_POS_ORIGINS` and `SESSION_BACKOFFICE_ORIGINS` lists select audience authority.
- API docs are disabled by default. Local contract generation still uses OpenAPI;
  staging and production expose neither interactive docs nor development endpoints.

## Manual Startup

For individual process control, use the explicit TLS, environment and process commands
in `scripts/dev/start-local.ps1`. Preserve its audience origins, certificate paths and
Uvicorn `--no-proxy-headers` setting. Plain HTTP cannot provide the required session
cookie boundary. See [runtime security and secrets](docs/operations/runtime-secrets.md)
for deployment configuration and private runtime files.

## Local Seed Data

The canonical local bootstrap seeds:

- Branches:
  - `MAIN` / `Main Branch` / `America/Hermosillo`
  - `NORTE` / `North Branch` / `America/Hermosillo`
- Workstations:
  - `POS-01` / `Front Register 01`
  - `POS-NORTE-01` / `North Register 01`
- Cashier user: `cashier@zeromerma.local`
- The disposable development password is defined by the local seed; it is not a
  production account or an owner bootstrap credential.
- Operational waste reasons:
  - `OLD_COUNTER`
  - `DAMAGED`
  - `CONTAMINATED`
  - `EXPIRED`
  - `OTHER`
- Correction reasons:
  - `WRONG_QUANTITY`
  - `WRONG_PRODUCT`
  - `DUPLICATE_CAPTURE`
  - `DAMAGED_DURING_HANDLING`
  - `COUNT_MISMATCH`
  - `OTHER`
- Cash close denomination catalog:
  - `1000.00`
  - `500.00`
  - `200.00`
  - `100.00`
  - `50.00`
  - `20.00`
  - `10.00`
  - `5.00`
  - `2.00`
  - `1.00`
  - `0.50`

Operational seed products now exist under every movable class used by the POS shell:

- `PAN-DULCE`: `CONCHA-VAN`, `CONCHA-CHOCO`, `CUERNO-MANTEQUILLA`
- `BOLILLO`: `BOLILLO-STD`
- `TELERA`: `TELERA-STD`
- `BEBIDAS`: `CAFE-AMERICANO`, `COCA-355`
- `PASTELES`: `PASTEL-CHOC-IND`, `REBANADA-TRES-LECHES`

## Contracts

Backend OpenAPI is the source of truth. Regenerate TypeScript contracts with:

```powershell
corepack pnpm contracts:generate
corepack pnpm contracts:check
```

`contracts:generate` writes the three reviewed derived artifacts:

- `packages/api-client/openapi.json`
- `packages/api-client/src/generated/schema.ts`
- `docs/architecture/API_CONTRACT_INVENTORY.json`

`contracts:check` generates into a temporary directory and fails on drift without rewriting
tracked files. The policy, collection classifications, error envelope, wire types, and endpoint
change workflow are documented in
[`docs/architecture/api-contracts.md`](docs/architecture/api-contracts.md).

Do not handwrite shared domain types between Python and TypeScript.

## Validation

Foundation validation always uses disposable PostgreSQL databases for database work. It never
uses the application `DATABASE_URL` or the local Compose database. Run the complete pipeline
from PowerShell 7 with Linux Docker and the canonical toolchain available:

```powershell
.\scripts\dev\check-foundation.ps1 -Stage All
```

The eight stages are `Preflight`, `Backend`, `Worker`, `Migrations`, `Contracts`, `Web`,
`Browser`, and `Negative`. Select a single stage with `-Stage Worker`, for example. Each
stage records logs and a result manifest under `.tmp/validation/foundation/<run-id>/`.
The same stages run as isolated CI jobs; `Foundation required` aggregates their results.
The pipeline and its evidence boundaries are documented in
[`docs/implementation/foundation-validation.md`](docs/implementation/foundation-validation.md).

Run the Python suites through the isolated harness:

```powershell
.\scripts\dev\run-api-tests.ps1
```

Without `-TestTarget`, this discovers every suite declared in `pyproject.toml`: API integration,
API unit and migration tests, worker unit and integration tests, and development-script tests.
To narrow a run, pass an explicit target, such as
`-TestTarget apps/worker/integration_tests`. Full discovery also runs the contract and toolchain
gate probes, so it needs the frozen Node dependencies and PowerShell 7.

Each invocation generates a unique run ID, database name, container name, test-only credential,
and loopback port. PostgreSQL 16 stores its data in container `tmpfs`; the harness removes the
container in `finally`, including when pytest fails. Concurrent harness invocations therefore use
different databases and cannot truncate one another.

The protected fixture requires all four dedicated values below. The harness owns them; do not put
fixed values in `.env`:

- `ZEROMERMA_TEST_ENVIRONMENT=test`
- `ZEROMERMA_TEST_DATABASE_URL` pointing to the generated loopback database
- `ZEROMERMA_TEST_RUN_ID` matching the database and application name
- `ZEROMERMA_TEST_DESTRUCTIVE_CONFIRMATION` bound to that run ID

Unknown environments, remote hosts, ordinary database names, shared users, missing confirmation,
or mismatched identities abort before engine creation. After connecting, a read-only identity query
must confirm the real database, user, application name, and PostgreSQL 16 before Alembic or
`TRUNCATE` can run. Error messages redact credentials.

Run the guard unit suite without Docker or database access:

```powershell
uv run --frozen pytest apps/api/unit_tests/test_database_safety.py
```

Calling `uv run pytest apps/api/tests` directly without the dedicated generated configuration is
intentionally unsupported and fails closed before connecting. CI uses the same ephemeral harness on
a Linux job and receives no operational or production database secret.

Validate the canonical Alembic chain through the same protected harness:

```powershell
# Fresh database, schema drift, constraints/indexes, and seed compatibility.
.\scripts\dev\run-migration-validation.ps1 -Mode Fast

# Every canonical checkpoint plus data preservation, interruption, and dump/restore.
.\scripts\dev\run-migration-validation.ps1 -Mode Full
```

The complete migration policy, checkpoint inventory, lock-risk classification, and required
roll-forward evidence are documented in
[`docs/operations/database-migrations.md`](docs/operations/database-migrations.md).

Run browser integration against a fresh database and dedicated API/POS/Backoffice servers:

```powershell
corepack pnpm --filter @zeromerma/pos-web exec playwright install chromium
.\scripts\dev\run-web-integration.ps1 -Surface All
```

The browser harness also accepts `-Surface POS` or `-Surface Backoffice`. It supplies unique
test users, credentials, database identity and loopback ports; runs canonical migrations and
fixture loading behind the database guards; and cleans up its processes and database on exit.
Real suites use `playwright.real.config.ts` and do not intercept API requests. Existing
`corepack pnpm test:e2e` browser/component tests remain a separate layer with fixtures/mocks.

Read the task-specific baselines and their limitations:

- [API foundation](docs/implementation/api-foundation-baseline.md)
- [Worker foundation](docs/implementation/worker-foundation-baseline.md)
- [POS and Backoffice foundation](docs/implementation/web-foundation-baseline.md)

Individual commands:

```powershell
uv run --frozen ruff check .
uv run --frozen mypy apps/api/src apps/worker/src
uv run --frozen pytest apps/api/unit_tests/test_database_safety.py
uv run --frozen pytest apps/worker/tests
.\scripts\dev\run-api-tests.ps1
uv run --frozen --project apps/worker python -m zeromerma_worker --once --skip-db-check
corepack pnpm contracts:check
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm build
corepack pnpm test:e2e
.\scripts\dev\run-web-integration.ps1 -Surface All
```

Session authentication uses audience-bound cookies and CSRF protection. Use the
canonical isolated API/browser suites for mutation validation; those suites cover
cash opening, sales, physical operations, corrections and close without manual
credential-bearing command lines. The cookie/session contract is generated from
backend OpenAPI; no bearer compatibility path exists.

Manual POS validation for the Phase 2 corrective patch:

1. Copy `apps\pos-web\.env.example` to `apps\pos-web\.env`.
2. Start the stack with `.\scripts\dev\start-local.ps1`.
3. Open `https://127.0.0.1:5173` and approve only the local temporary certificate if requested.
4. Sign in with the local cashier credentials provisioned by the development seed.
5. Confirm the desktop shell shows the top bar, left module rail, central sale area, and right checkout panel.
6. Confirm the shell uses the `EL_MEJOR_PAN` theme for the `MAIN` branch.
7. Confirm the search field is visible but does not receive initial focus.
8. Confirm class selection is the initial control point and class cards show all `CLASS_CAPTURE` entries before `PRODUCT_DIRECT` entries.
9. Validate the Bolillo flow:
    - select `Bolillo`
    - confirm the UI moves directly to quantity capture
    - type `3` with the physical keyboard
    - press `Enter`
    - confirm the line is added and control returns to class selection
10. Validate the Bebidas flow:
    - select `Bebidas`
    - confirm product selection appears
    - select `Cafe americano`
    - type `2` with the physical keyboard
    - press `Enter`
    - confirm the line is added and control returns to class selection
11. Confirm mixed class-capture and product-direct lines coexist correctly in the ticket.
12. Confirm checkout rows stay dense and readable, with plus, minus, and remove controls working correctly.
13. Move to payment, confirm the cash field becomes the active control point, type `100`, and confirm change or remaining due updates clearly.
14. Press `Enter` only while payment capture is active and confirm the sale succeeds, the ticket clears, the cash field resets, and the POS returns to class selection.
15. Collapse and expand the sidebar, open a placeholder module such as `Pedidos`, and confirm the shell remains stable.

Existing browser/component smoke tests, also run by the foundation `Web` stage:

```powershell
corepack pnpm test:e2e
```

## Database Reset

This deletes the local PostgreSQL volume, reruns migrations, and reseeds the current local operational data:

```powershell
.\scripts\dev\reset-db.ps1 -Force
```
