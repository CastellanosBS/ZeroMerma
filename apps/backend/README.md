# ZeroMerma Backend

Backend service for **ZeroMerma**, a bakery-oriented operational platform focused on:

- point of sale (POS)
- cash sessions
- inventory integrity
- production tracking
- branch-specific pricing
- reproducible database bootstrap
- consistent engineering workflows

This repository is structured around **FastAPI + SQLAlchemy + Alembic + PostgreSQL**, with a strong emphasis on:

- deterministic behavior
- explicit business rules
- inventory traceability
- reproducible developer workflows
- long-term maintainability

---

## 1. Project intent

ZeroMerma is not a generic CRUD backend. It is meant to support the real operational needs of a bakery / pastry business, including:

- fast sales execution
- stock consistency
- opening/closing cash sessions
- production-to-inventory transitions
- auditable payment flows
- branch-level pricing behavior
- stable test/bootstrap flows

The project is evolving toward a **keyboard-first POS workflow** with strong backend authority over:

- pricing
- inventory
- authorization
- transactional integrity

---

## 2. Current system status

The backend has already gone through a major stabilization phase and now has:

- canonical ORM models aligned with the real schema
- canonical Pydantic schemas with `Decimal`-oriented contracts
- canonical domain errors and centralized error translation
- canonical DB bootstrap / seed flow
- cleaner router and dependency structure
- a reproducible local developer workflow

This is the engineering baseline intended for the next phase of POS implementation.

---

## 3. Current functional scope

### 3.1 Authentication and security
- JWT-based authentication
- active user enforcement
- `AuthContext` support
- role-aware router/service flows
- standardized security helpers

### 3.2 Admin / master data
- branches
- roles
- users

### 3.3 Catalog
- product categories
- products
- sellable products vs input/raw-material products
- product activation state

### 3.4 Inventory
- immutable movement ledger (`inventory_movement`)
- operational snapshot (`inventory_balance`)
- stock queries
- movement queries

### 3.5 POS
- open cash session
- close cash session
- create sale
- list sales
- retrieve sale detail
- append payments
- server-side pricing fallback during sale creation
- guardrail: input/raw-material products cannot be sold through POS

### 3.6 Pricing
- catalog/base sale price
- branch override price
- effective price resolution

### 3.7 Production
- production run creation
- input consumption
- output generation
- snapshot and ledger synchronization

---

## 4. Architecture principles

### 4.1 Ledger + snapshot inventory model
Inventory uses a hybrid model:

- `inventory_movement` = immutable ledger / audit trail
- `inventory_balance` = operational snapshot / fast stock state

This provides:

- traceability
- auditability
- atomic decrement workflows
- efficient reads for operational flows

### 4.2 Money and quantity semantics
The system treats money and quantity as exact decimal values:

- money → `NUMERIC(18,2)`
- quantity → `NUMERIC(18,3)`

In Python and Pydantic, the backend uses `Decimal`-oriented contracts.
JSON responses may serialize numeric values as strings. Consumers and tests must treat those values as exact decimals, not floating-point approximations.

### 4.3 Domain errors
The service layer expresses business failures through canonical domain exceptions such as:

- `DomainValidationError`
- `DomainNotFoundError`
- `DomainConflictError`
- `DomainAuthorizationError`
- `DomainInvariantError`

These are translated centrally by the API layer into a consistent error envelope.

### 4.4 Soft-delete preference
Master data is generally modeled using `is_active` flags rather than physical deletion whenever historical integrity matters.

### 4.5 Backend authority
The backend is intended to be the source of truth for:

- sellability rules
- effective pricing
- inventory mutation safety
- branch scoping
- transactional integrity

---

## 5. Main modules

### `zeromerma_api/core`
Core infrastructure:
- auth context
- security helpers
- dependency aliases
- authorization helpers
- request context / logging helpers
- domain error types

### `zeromerma_api/db`
Database access:
- engine
- session factory
- request-scoped DB dependency

### `zeromerma_api/models`
Canonical ORM models aligned with the current Alembic schema.

### `zeromerma_api/schemas`
Canonical API contracts:
- strict request schemas
- ORM-friendly response schemas
- `Decimal`-based contracts

### `zeromerma_api/services`
Business logic:
- cash sessions
- sales
- payments
- inventory balance
- pricing
- production
- catalog

### `zeromerma_api/routers`
HTTP routes grouped by module:
- auth
- admin
- catalog
- inventory
- pos
- pricing
- production
- health / ready

### `zeromerma_api/scripts`
Importable internal scripts and canonical DB bootstrap utilities.

### `zeromerma_api/tests`
Automated tests covering:
- smoke behavior
- seeds
- POS flows
- inventory
- catalog
- pricing
- production
- concurrency scenarios

---

## 6. Repository structure

```text
apps/backend/
├── alembic.ini
├── dev_seed.py
├── dev_seed_inventory.py
├── devcheck_db.py
├── Makefile
├── pyproject.toml
├── README.md
├── seed.py
├── tasks.ps1
├── docs/
│   └── runbook/
│       └── backend-operations.md
├── migrations/
│   ├── env.py
│   └── versions/
└── src/
    └── zeromerma_api/
        ├── core/
        ├── db/
        ├── models/
        ├── routers/
        ├── schemas/
        ├── scripts/
        ├── services/
        └── tests/
