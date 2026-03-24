# ZeroMerma Backend — Operations Runbook

## 1. Purpose

This document is the canonical operational guide for the **ZeroMerma backend**. It is intended to help developers and technical operators diagnose, recover, and stabilize the backend in local, development, and early deployment environments.

This runbook answers four practical questions:

1. How do I verify that the backend environment is healthy?
2. How do I recover the database and migration state safely?
3. How do I bootstrap a usable environment consistently?
4. How do I debug the most common POS, inventory, payment, and production failures quickly?

This file is deliberately operational. It is not a product specification and it is not a substitute for architectural documentation.

---

## 2. Scope

This runbook covers the currently stabilized backend modules and workflows:

- environment setup
- database connectivity
- Alembic migration state
- canonical seed/bootstrap execution
- POS flows
- cash sessions
- payments
- inventory ledger and snapshot
- production runs
- pricing and catalog support
- quality gates (format/lint/tests)
- local reset and recovery

---

## 3. Canonical assumptions

The procedures below assume the following project conventions are already in place:

- backend root: `apps/backend/`
- Windows command surface: `tasks.ps1`
- Unix/CI-friendly command surface: `Makefile`
- Python package root: `src/zeromerma_api/`
- migration entrypoint: `migrations/env.py`
- canonical CLI bootstrap entrypoint: `apps/backend/seed.py`
- canonical importable seed compatibility module: `src/zeromerma_api/scripts/seed.py`
- canonical shared bootstrap implementation: `src/zeromerma_api/scripts/bootstrap_db.py`

The backend is expected to use:

- Python 3.12
- Poetry
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- Pytest
- Ruff
- Black
- pre-commit

The backend is also expected to be canonized around:

- `Decimal` for money and quantity-sensitive workflows
- domain errors for service-layer business failures
- strict request schemas
- reproducible seed/bootstrap behavior

---

## 4. Quick diagnostic sequence

When the backend behaves unexpectedly and you do not yet know the cause, run this exact sequence first.

### 4.1 General recovery sequence

```powershell
.\tasks.ps1 db-check
.\tasks.ps1 db-upgrade
.\tasks.ps1 seed-core
.\tasks.ps1 lint
.\tasks.ps1 test
```

### 4.2 POS-focused recovery sequence

```powershell
.\tasks.ps1 db-check
.\tasks.ps1 db-upgrade
.\tasks.ps1 seed-dev
.\tasks.ps1 test-pos
```

### 4.3 Why this order matters

This order validates the most failure-prone layers in the correct sequence:

1. connection and target DB sanity
2. migration state sanity
3. canonical bootstrap viability
4. static code health
5. behavioral correctness

Do not start by modifying database rows manually unless you already know the exact failure mode.

---

## 5. Official command surface

### 5.1 PowerShell tasks (official on Windows)

Show all commands:

```powershell
.\tasks.ps1 help
```

Install dependencies:

```powershell
.\tasks.ps1 install
```

Install pre-commit hooks:

```powershell
.\tasks.ps1 precommit
```

Check DB and Alembic state:

```powershell
.\tasks.ps1 db-check
```

Apply migrations:

```powershell
.\tasks.ps1 db-upgrade
```

Seed profiles:

```powershell
.\tasks.ps1 seed-core
.\tasks.ps1 seed-dev
.\tasks.ps1 seed-inventory-fixture
```

Format code:

```powershell
.\tasks.ps1 format
```

Run lint checks:

```powershell
.\tasks.ps1 lint
```

Run all tests:

```powershell
.\tasks.ps1 test
```

Run POS-focused tests:

```powershell
.\tasks.ps1 test-pos
```

Run smoke tests:

```powershell
.\tasks.ps1 smoke
```

Run local CI-equivalent pipeline:

```powershell
.\tasks.ps1 ci-local
```

### 5.2 Makefile equivalents

```bash
make help
make db-check
make db-upgrade
make seed-core
make seed-dev
make seed-inventory-fixture
make format
make lint
make test
make test-pos
make smoke
make ci-local
```

---

## 6. Environment configuration

### 6.1 Canonical files

- example file: `.env.example`
- real local file: `.env`

### 6.2 Initial setup

```powershell
Copy-Item .env.example .env
```

### 6.3 Rules

- `.env.example` must contain declarative variables only
- `.env` must not contain Python code
- `DATABASE_URL` must point to a valid PostgreSQL database
- local JWT secrets may be simple, but non-local secrets must be strong and private

### 6.4 Typical required variables

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
- `APP_ENV`
- `APP_DEBUG`
- `LOG_LEVEL`
- `CORS_ALLOW_ORIGINS`

---

## 7. Database lifecycle

### 7.1 Health check

Run:

```powershell
.\tasks.ps1 db-check
```

Expected outcomes:

- the database is reachable
- current Alembic revision is readable
- head Alembic revision is readable
- the configured target looks correct

### 7.2 Migrations

Run:

```powershell
.\tasks.ps1 db-upgrade
```

This is the canonical way to bring the configured database to the latest real schema.

### 7.3 Seed profiles

#### Core

Purpose:
- minimum operable backend baseline

Typical contents:
- `MAIN` branch
- roles
- admin user
- cashier user

Command:

```powershell
.\tasks.ps1 seed-core
```

#### Dev

Purpose:
- richer development state

Typical contents:
- core seed
- categories
- products
- opening balance ledger rows
- snapshot rebuild
- optional sample POS sale and payment

Command:

```powershell
.\tasks.ps1 seed-dev
```

#### Inventory fixture

Purpose:
- deterministic fixture for inventory endpoint checks and tests

Typical contents:
- one sellable product
- +10 opening balance movement
- -3 sale movement
- snapshot rebuilt from ledger

Command:

```powershell
.\tasks.ps1 seed-inventory-fixture
```

---

## 8. Alembic operations

### 8.1 Healthy migration state

A healthy migration state means:

- `current_revision` exists
- `head_revision` exists
- `current_revision == head_revision`

Check with:

```powershell
poetry run python .\devcheck_db.py
```

### 8.2 Common migration failure modes

#### Case A — revision not found

Symptoms:
- Alembic cannot locate a revision
- tests fail before service logic executes

Typical cause:
- temporary migration file was created and later removed
- local DB still points to a deleted revision

Recovery:
1. inspect current/head
2. if local DB is disposable, recreate it
3. rerun migrations
4. rerun seeds

#### Case B — current/head mismatch

Symptoms:
- migrations behave inconsistently
- seed scripts fail because the DB is not at the expected schema

Recovery:

```powershell
.\tasks.ps1 db-check
.\tasks.ps1 db-upgrade
.\tasks.ps1 seed-core
```

If mismatch persists and the DB is local-only, recreate it.

#### Case C — unexpected autogenerate drift

Symptoms:
- `alembic revision --autogenerate` proposes dropping or recreating objects you did not intend to change

Typical causes:
- model package not fully imported in Alembic env
- ORM/schema desynchronization
- temporary drift-check revision left around

Recovery:
- verify `migrations/env.py` imports the models package
- verify `Base.metadata` contains all canonical models
- confirm no temporary drift-check revision was left under `migrations/versions`

---

## 9. Canonical seed architecture

The backend uses three layers on purpose.

### 9.1 CLI entrypoint

```text
apps/backend/seed.py
```

Use this when running seed/bootstrap from the terminal.

### 9.2 Importable compatibility module

```text
src/zeromerma_api/scripts/seed.py
```

Use this when tests or internal Python code need seed functions such as `run_all(...)`.

### 9.3 Shared canonical implementation

```text
src/zeromerma_api/scripts/bootstrap_db.py
```

This contains the real reusable seed/bootstrap logic.

### 9.4 Operational rule

- If you want to **execute** seed/bootstrap from terminal → use `apps/backend/seed.py`
- If a test or internal module wants to **import** seed/bootstrap behavior → use `zeromerma_api.scripts.seed`

### 9.5 Expected seed properties

Canonical seeds should be:

- idempotent
- schema-aware
- transaction-safe
- deterministic enough for tests/dev
- aligned with the current domain rules

---

## 10. POS troubleshooting

The POS backend is currently the most operationally sensitive part of the system.

### 10.1 Sale creation fails

Check all of the following:

- cash session exists
- cash session is `OPEN`
- actor user exists and is active
- actor can access the requested branch
- all products exist
- products being sold are not `is_input = true`
- effective price is resolvable if `unit_price` is omitted
- stock is sufficient in `inventory_balance`

Useful commands:

```powershell
.\tasks.ps1 seed-dev
.\tasks.ps1 test-pos
```

Focused test suite:

```powershell
poetry run pytest -q `
  src/zeromerma_api/tests/test_cash_session_endpoints.py `
  src/zeromerma_api/tests/test_pos_sales_endpoints.py `
  src/zeromerma_api/tests/test_pos_payments_endpoints.py `
  src/zeromerma_api/tests/test_pos_server_side_pricing.py `
  src/zeromerma_api/tests/test_pos_inputs_not_sellable.py `
  src/zeromerma_api/tests/test_concurrency_inventory_balance.py
```

### 10.2 Payment append fails

Check:

- sale exists
- sale is `OPEN`
- payment method is valid
- amount is > 0
- amount does not exceed total due

Useful test:

```powershell
poetry run pytest -q src/zeromerma_api/tests/test_pos_payments_endpoints.py
```

### 10.3 Effective price resolution fails

Typical causes:

- no branch override exists
- no catalog base `sale_price` exists
- request omitted `unit_price`
- pricing service sees no effective price

Expected behavior:
- this should fail explicitly as a business/domain error, not silently default to zero

---

## 11. Cash session troubleshooting

### 11.1 Open cash session fails

Check:

- branch exists
- user exists and is active
- user can operate on the branch
- no other `OPEN` session exists for that branch

Expected failure mode:
- domain conflict if the branch already has an open session

### 11.2 Close cash session fails

Check:

- session exists
- session is `OPEN`
- user can operate on the session branch
- closing amount is a valid decimal >= 0

---

## 12. Inventory troubleshooting

### 12.1 Stock endpoint looks wrong

Remember:

- stock reads are grouped from the ledger
- mutation safety relies on `inventory_balance`

So wrong stock can come from:

- incorrect movement history
- stale snapshot
- mismatched seed fixture

### 12.2 Reconciliation sequence

1. inspect ledger movements for the product
2. compute aggregate quantity from the ledger
3. compare against snapshot `inventory_balance`
4. rebuild snapshot from ledger if the workflow explicitly supports it

### 12.3 Useful validation test

```powershell
poetry run pytest -q src/zeromerma_api/tests/test_inventory_endpoints.py
```

### 12.4 Deterministic fixture flow

```powershell
.\tasks.ps1 seed-inventory-fixture
poetry run pytest -q src/zeromerma_api/tests/test_inventory_endpoints.py
```

---

## 13. Production troubleshooting

### 13.1 Production run fails

Check:

- branch exists
- actor user exists
- all input products exist
- all output products exist
- input stock is sufficient
- input products are true inputs/raw materials
- output products are finished goods

### 13.2 Expected side effects

A valid production run should:

- decrement inputs in the snapshot
- increment outputs in the snapshot
- append movement ledger rows for both directions

### 13.3 Useful tests

```powershell
poetry run pytest -q `
  src/zeromerma_api/tests/test_production_stub.py `
  src/zeromerma_api/tests/test_production_validations.py
```

---

## 14. Catalog and pricing troubleshooting

### 14.1 Product creation or update fails

Check:

- category exists
- SKU uniqueness is respected
- `uom` is valid
- money fields are valid decimals
- request schema does not contain forbidden extra fields

### 14.2 Pricing override fails

Check:

- product exists
- branch exists
- actor has the required role
- branch scoping is valid
- price is a non-negative decimal

Useful test:

```powershell
poetry run pytest -q src/zeromerma_api/tests/test_pricing_endpoints.py
```

---

## 15. Quality gate troubleshooting

### 15.1 Ruff or Black fails

First response:

```powershell
.\tasks.ps1 format
.\tasks.ps1 lint
```

Typical causes:

- import ordering drift
- long lines in newly edited code
- missing exception chaining (`raise ... from e`)
- dead imports or unused variables

Policy:

- Black formats
- Ruff lints
- line length is canonical and should not be redefined per file without a strong reason

### 15.2 Pre-commit does not run

Install hooks:

```powershell
poetry run pre-commit install
```

Run manually if needed:

```powershell
poetry run pre-commit run --all-files
```

---

## 16. Test suite troubleshooting

### 16.1 Decimal/string mismatch in API responses

This is common after canonicalization.

Rule:
- if API responses serialize `Decimal` values as JSON strings, tests should convert those values back to `Decimal` before comparing
- do not use float subtraction for money-sensitive values

### 16.2 Tests fail because of stale local state

Symptoms:
- test passes in isolation but fails in suite
- reused rows retain modified state

Fix strategy:

- make seed fixtures deterministic
- clear dependent tables in correct FK order
- avoid shared mutable fixtures unless explicitly intended

### 16.3 Tests fail before logic runs

Typical causes:

- Alembic revision mismatch
- DB connectivity issue
- import/compatibility mismatch in seed/bootstrap helpers

First commands:

```powershell
.\tasks.ps1 db-check
.\tasks.ps1 db-upgrade
poetry run pytest -q
```

---

## 17. Local reset checklist

If the local environment is too dirty to trust, use a controlled reset workflow.

### 17.1 Recommended reset order

1. recreate or reset the local database
2. apply migrations
3. run canonical dev seed
4. run POS-focused suite
5. run full suite

Commands:

```powershell
.\tasks.ps1 db-upgrade
.\tasks.ps1 seed-dev
.\tasks.ps1 test-pos
.\tasks.ps1 test
```

If DB recreation is required, do it before step 1.

---

## 18. Escalation package

If a problem survives:

- clean bootstrap
- migration verification
- targeted rerun
- full rerun

then collect all of the following before escalating:

1. exact command executed
2. full traceback
3. `current_revision`
4. `head_revision`
5. whether it reproduces on a fresh DB
6. whether it reproduces in an isolated targeted test

Without this information, debugging becomes slower and noisier.

---

## 19. Operational discipline rules

1. Do not commit temporary Alembic drift-check revisions.
2. Do not bypass canonical bootstrap with ad hoc SQL unless strictly necessary.
3. Do not reintroduce float-based money semantics in services or tests.
4. Do not bypass branch scoping checks casually.
5. Do not patch DB state manually before checking current/head revision.
6. Prefer canonical tasks over improvised one-off command sequences.

---

## 20. Reference commands

### DB

```powershell
.\tasks.ps1 db-check
.\tasks.ps1 db-upgrade
```

### Seed

```powershell
.\tasks.ps1 seed-core
.\tasks.ps1 seed-dev
.\tasks.ps1 seed-inventory-fixture
```

### Quality

```powershell
.\tasks.ps1 format
.\tasks.ps1 lint
```

### Tests

```powershell
.\tasks.ps1 test
.\tasks.ps1 test-pos
.\tasks.ps1 smoke
.\tasks.ps1 ci-local
```

### Manual direct commands

```powershell
poetry run python .\devcheck_db.py
poetry run alembic upgrade head
poetry run pytest -q
```

---

## 21. Final note

This runbook exists to reduce improvisation.

When in doubt, the recovery rule is simple:

1. verify DB connectivity
2. verify Alembic state
3. run canonical seed
4. run targeted tests
5. run full suite

If the backend still fails after that, the issue is likely real and worth debugging at code level.
