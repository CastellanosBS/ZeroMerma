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
- Windows PowerShell for local scripts

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

Start PostgreSQL, run migrations, and open separate terminals for the API, worker, POS web, and backoffice web:

```powershell
.\scripts\dev\start-local.ps1
```

The script runs the toolchain preflight, executes `uv sync --all-packages --dev --frozen`, installs Node dependencies with `corepack pnpm install --frozen-lockfile`, regenerates API contracts, starts PostgreSQL, applies Alembic migrations, and launches the four local processes.
It also seeds the local cashier, branches, workstations, operational catalog products, waste reasons, correction reasons, and the cash close denomination catalog.

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
corepack pnpm --filter @zeromerma/pos-web dev
corepack pnpm --filter @zeromerma/backoffice-web dev
```

## Local Seed Data

The canonical local bootstrap seeds:

- Branches:
  - `MAIN` / `Main Branch` / `America/Hermosillo`
  - `NORTE` / `North Branch` / `America/Hermosillo`
- Workstations:
  - `POS-01` / `Front Register 01`
  - `POS-NORTE-01` / `North Register 01`
- Cashier user: `cashier@zeromerma.local`
- Password: `ChangeMe123!`
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
It also seeds the local operational and correction data before running the backend test suite.

Individual commands:

```powershell
uv run ruff check apps/api/src apps/api/tests apps/worker/src apps/worker/tests
uv run mypy apps/api/src apps/worker/src
uv run pytest
uv run --project apps/worker python -m zeromerma_worker --once --skip-db-check
corepack pnpm contracts:generate
corepack pnpm lint
corepack pnpm test
corepack pnpm build
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

Manual API validation for Phase 3A operational modules:

```powershell
$login = Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/auth/login -ContentType "application/json" -Body '{"email":"cashier@zeromerma.local","password":"ChangeMe123!"}'
$token = $login.access_token
$headers = @{ Authorization = "Bearer $token"; "X-Request-ID" = "manual-phase-3a-check" }

$operationsBootstrap = Invoke-RestMethod -Uri "http://localhost:8000/v1/operations/bootstrap?workstation_code=POS-01" -Headers $headers
$operationsBootstrap.destination_branches

$catalog = Invoke-RestMethod -Uri "http://localhost:8000/v1/operations/catalog?workstation_code=POS-01&module=COUNTER_TRANSFER" -Headers $headers
$bolilloClassId = ($catalog.classes | Where-Object code -eq "BOLILLO").id
$classProducts = Invoke-RestMethod -Uri "http://localhost:8000/v1/operations/classes/$bolilloClassId/products?workstation_code=POS-01&module=COUNTER_TRANSFER" -Headers $headers
$bolilloProductId = ($classProducts.products | Where-Object code -eq "BOLILLO-STD").id
$northBranchId = ($operationsBootstrap.destination_branches | Where-Object code -eq "NORTE").id

$counterTransfer = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/v1/operations/counter-transfer/commit" -Headers $headers -ContentType "application/json" -Body (@{
  workstation_code = "POS-01"
  lines = @(@{ product_id = $bolilloProductId; quantity = "3" })
  notes = "Manual counter replenishment"
} | ConvertTo-Json -Depth 5)

$wasteRecord = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/v1/operations/waste/commit" -Headers $headers -ContentType "application/json" -Body (@{
  workstation_code = "POS-01"
  source_bucket_code = "COUNTER"
  reason_code = "DAMAGED"
  lines = @(@{ product_id = $bolilloProductId; quantity = "1" })
  notes = "Manual waste test"
} | ConvertTo-Json -Depth 5)

$dispatch = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/v1/transfers/dispatch/commit" -Headers $headers -ContentType "application/json" -Body (@{
  workstation_code = "POS-01"
  destination_branch_id = $northBranchId
  lines = @(@{ product_id = $bolilloProductId; quantity = "2" })
  notes = "Manual transfer dispatch"
} | ConvertTo-Json -Depth 5)

$pending = Invoke-RestMethod -Uri "http://localhost:8000/v1/transfers/inbound/pending?workstation_code=POS-NORTE-01" -Headers $headers
$transferId = $dispatch.shipment.id
$detail = Invoke-RestMethod -Uri "http://localhost:8000/v1/transfers/$transferId?workstation_code=POS-NORTE-01" -Headers $headers
$receive = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/v1/transfers/$transferId/receive" -Headers $headers -ContentType "application/json" -Body (@{
  workstation_code = "POS-NORTE-01"
  lines = @(@{
    shipment_line_id = $dispatch.shipment.lines[0].id
    expected_quantity = "2"
    received_quantity = "2"
  })
  notes = "Manual receipt"
} | ConvertTo-Json -Depth 5)
```

Manual API validation for Phase 4A corrections:

```powershell
$login = Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/auth/login -ContentType "application/json" -Body '{"email":"cashier@zeromerma.local","password":"ChangeMe123!"}'
$token = $login.access_token
$headers = @{ Authorization = "Bearer $token"; "X-Request-ID" = "manual-phase-4a-correction" }

$bootstrap = Invoke-RestMethod -Uri "http://localhost:8000/v1/corrections/bootstrap?workstation_code=POS-01" -Headers $headers
$counterTransferCatalog = Invoke-RestMethod -Uri "http://localhost:8000/v1/operations/catalog?workstation_code=POS-01&module=COUNTER_TRANSFER" -Headers $headers
$bolilloClassId = ($counterTransferCatalog.classes | Where-Object code -eq "BOLILLO").id
$classProducts = Invoke-RestMethod -Uri "http://localhost:8000/v1/operations/classes/$bolilloClassId/products?workstation_code=POS-01&module=COUNTER_TRANSFER" -Headers $headers
$bolilloProductId = ($classProducts.products | Where-Object code -eq "BOLILLO-STD").id

$targetDocument = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/v1/operations/counter-transfer/commit" -Headers $headers -ContentType "application/json" -Body (@{
  workstation_code = "POS-01"
  lines = @(@{ product_id = $bolilloProductId; quantity = "4" })
  notes = "Manual correction target"
} | ConvertTo-Json -Depth 5)

$search = Invoke-RestMethod -Uri "http://localhost:8000/v1/corrections/search?workstation_code=POS-01&document_type=COUNTER_TRANSFER&query=Manual" -Headers $headers
$detail = Invoke-RestMethod -Uri "http://localhost:8000/v1/corrections/$($targetDocument.id)?workstation_code=POS-01" -Headers $headers
$correction = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/v1/corrections/commit" -Headers $headers -ContentType "application/json" -Body (@{
  workstation_code = "POS-01"
  target_document_id = $targetDocument.id
  reason_code = "WRONG_QUANTITY"
  notes = "Should have been two fewer units"
  lines = @(@{
    product_id = $bolilloProductId
    delta_quantity = "-2"
    notes = "Manual delta correction"
  })
} | ConvertTo-Json -Depth 6)
```

Manual API validation for Phase 7A cash close preview:

```powershell
$login = Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/auth/login -ContentType "application/json" -Body '{"email":"cashier@zeromerma.local","password":"ChangeMe123!"}'
$token = $login.access_token
$headers = @{ Authorization = "Bearer $token"; "X-Request-ID" = "manual-phase-7a-close" }

$open = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/v1/cash-sessions/open" -Headers $headers -ContentType "application/json" -Body '{"workstation_code":"POS-01","opening_amount":"150.00"}'
$sale = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/v1/sales/confirm" -Headers $headers -ContentType "application/json" -Body (@{
  workstation_code = "POS-01"
  lines = @(
    @{
      capture_mode = "CLASS_CAPTURE"
      product_class_id = (
        (Invoke-RestMethod -Uri "http://localhost:8000/v1/pos/catalog?workstation_code=POS-01" -Headers $headers).classes |
        Where-Object code -eq "PAN-DULCE"
      ).id
      quantity = "2"
    }
  )
  payments = @(@{
    payment_method_code = "CASH"
    tendered_amount = "50.00"
  })
} | ConvertTo-Json -Depth 6)

$bootstrap = Invoke-RestMethod -Uri "http://localhost:8000/v1/cash-close/bootstrap?workstation_code=POS-01" -Headers $headers
$summary = Invoke-RestMethod -Uri "http://localhost:8000/v1/cash-close/summary?workstation_code=POS-01" -Headers $headers
$preview = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/v1/cash-close/preview" -Headers $headers -ContentType "application/json" -Body (@{
  workstation_code = "POS-01"
  denomination_counts = @(
    @{ denomination_value = "100.00"; unit_count = 1 }
    @{ denomination_value = "50.00"; unit_count = 1 }
    @{ denomination_value = "20.00"; unit_count = 1 }
    @{ denomination_value = "2.00"; unit_count = 2 }
  )
  notes = "Manual financial preview"
} | ConvertTo-Json -Depth 6)
```

Manual POS validation for the Phase 2 corrective patch:

1. Copy `apps\pos-web\.env.example` to `apps\pos-web\.env`.
2. Start the stack with `.\scripts\dev\start-local.ps1`.
3. Open `http://localhost:5173` or `http://127.0.0.1:5173`.
4. Sign in with `cashier@zeromerma.local` / `ChangeMe123!`.
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

Optional Playwright e2e smoke tests:

```powershell
corepack pnpm test:e2e
```

## Database Reset

This deletes the local PostgreSQL volume, reruns migrations, and reseeds the current local operational data:

```powershell
.\scripts\dev\reset-db.ps1 -Force
```
