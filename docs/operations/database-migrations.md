# Database migration validation and operations

## Authority and safety boundary

The canonical Alembic chain is `0001_foundation_schema` through
`20260520_0039_system_settings`. PostgreSQL 16 is the supported validation engine. Migration tests
must run through `scripts/dev/run-migration-validation.ps1`, which reuses the ZM-FIN-005 ephemeral
PostgreSQL harness and its preconnect and postconnect guards. A migration validation run must never
use the local Compose database, staging, production, `zeromerma-postgres`,
`zeromerma_zeromerma_postgres_data`, or `zeromerma_pgdata`.

The current chain has one root, one head, no branch, no merge revision, no cycle, and no orphan.
Every tracked revision is a supported upgrade checkpoint. Changing that support boundary requires
explicit versioned evidence; a failing checkpoint is not silently excluded.

## Reproducible commands

Run the bounded check used by foundation CI:

```powershell
.\scripts\dev\run-migration-validation.ps1 -Mode Fast
```

It proves a fresh PostgreSQL 16 database can reach head, runs the model/schema drift comparison,
verifies constraints and indexes, and checks that the current bootstrap seed is schema-compatible.

Run the complete acceptance matrix before approving a migration-chain change:

```powershell
.\scripts\dev\run-migration-validation.ps1 -Mode Full
```

The full command additionally creates a unique ephemeral database for every supported revision,
materializes that revision from base, upgrades it to head, executes the data-preservation matrix,
injects a controlled transactional failure, and performs a bounded `pg_dump`/`pg_restore` sanity
check. Every child database is dropped and the harness container is removed in `finally`.

Do not invoke the migration integration tests directly with an application `DATABASE_URL`.
Injected Alembic connections are accepted only when accompanied by the validated ZM-FIN-005 test
identity, and Alembic rechecks the connected database before running migration operations.

## Canonical revision inventory

`Data` means the upgrade inserts, updates, deletes, backfills, or otherwise interprets existing
rows. `Destructive` means the upgrade drops structures/data or replaces constraints in a way that
can reject existing rows. Lock risk is qualitative; it is not a production timing estimate.

| # | Revision | Parent | Main upgrade | Data | Destructive | Lock risk | Downgrade |
|---:|---|---|---|---:|---:|---|---|
| 1 | `0001_foundation_schema` | base | audit/outbox tables and indexes | No | No | Medium | Lossy |
| 2 | `0002_phase_1a_core_identity_cash` | `0001_foundation_schema` | identity, branch, workstation, cash tables | No | No | Medium | Lossy |
| 3 | `0003_phase_2a_pos_sales` | `0002_phase_1a_core_identity_cash` | catalog, sales, payment, movement tables | No | No | Medium | Lossy |
| 4 | `0004_phase_2_pos_catalog_order` | `0003_phase_2a_pos_sales` | display-order columns and code-based backfill | Yes | Yes | High | Lossy |
| 5 | `0005_phase_3a_operations` | `0004_phase_2_pos_catalog_order` | operation documents and waste reasons | No | No | Medium | Lossy |
| 6 | `0006_phase_4a_corrections` | `0005_phase_3a_operations` | correction documents and reasons | No | No | Medium | Lossy |
| 7 | `0007_phase_7a_cash_close` | `0006_phase_4a_corrections` | cash-close tables and indexes | No | No | Medium | Lossy |
| 8 | `0008_phase_7b_cash_close` | `0007_phase_7a_cash_close` | constraint expansion, columns, reconciliation tables | No | Yes | High | Lossy |
| 9 | `0009_cash_close_payment_methods` | `0008_phase_7b_cash_close` | aggregate cash backfill; replace denomination detail | Yes | Yes | High | Lossy/synthetic |
| 10 | `0010_orders_module` | `0009_cash_close_payment_methods` | customer-order tables | No | No | Medium | Lossy |
| 11 | `0011_returns_module` | `0010_orders_module` | returns tables | No | No | Medium | Lossy |
| 12 | `0012_payments_module` | `0011_returns_module` | nullable change, operational payments, categories | Yes | Yes | High | Lossy |
| 13 | `0013_discounts_module` | `0012_payments_module` | operational discounts and categories | Yes | No | Medium | Lossy |
| 14 | `0014_remove_other_payment_method` | `0013_discounts_module` | convert/merge `OTHER` into `CARD`; narrow checks | Yes | Yes | High | Not meaningful |
| 15 | `20260416_0015_corr_dest` | `0014_remove_other_payment_method` | destination FK and constraint expansion | No | Yes | High | Lossy |
| 16 | `20260417_0016_order_cancel` | `20260416_0015_corr_dest` | order-payment constraint expansion | No | Yes | High | Unsafe |
| 17 | `20260422_0017_returns_reason` | `20260417_0016_order_cancel` | non-null return-reason defaults | Yes | Yes | High | Lossy |
| 18 | `20260511_0018_user_surface` | `20260422_0017_returns_reason` | default surface and check | Yes | No | Medium | Lossy |
| 19 | `20260518_0019_close_mode` | `20260511_0018_user_surface` | non-null close mode and check | Yes | Yes | High | Lossy |
| 20 | `20260518_0020_counter_empty` | `20260518_0019_close_mode` | counter flag and close-mode normalization | Yes | Yes | High | Lossy |
| 21 | `20260519_0021_brand_scope` | `20260518_0020_counter_empty` | brands, branch/class backfill, non-null FKs | Yes | Yes | High | Lossy |
| 22 | `20260520_0022_recipes_costs` | `20260519_0021_brand_scope` | recipe/cost tables and catalog columns | No | No | Medium | Lossy |
| 23 | `20260520_0023_discounts` | `20260520_0022_recipes_costs` | commercial-discount schema | No | No | Medium | Lossy |
| 24 | `20260520_0024_branch_admin` | `20260520_0023_discounts` | nullable branch profile columns | No | No | Medium | Lossy |
| 25 | `20260520_0025_inventory_admin` | `20260520_0024_branch_admin` | inventory tables and constraint replacement | No | Yes | High | Lossy |
| 26 | `20260520_0026_transfer_moves` | `20260520_0025_inventory_admin` | inventory-movement constraint expansion | No | Yes | High | Unsafe |
| 27 | `20260520_0027_production` | `20260520_0026_transfer_moves` | production tables and constraint expansion | No | Yes | High | Lossy |
| 28 | `20260520_0028_admin_waste` | `20260520_0027_production` | inventory-movement constraint expansion | No | Yes | High | Unsafe |
| 29 | `20260520_0029_admin_suppliers` | `20260520_0028_admin_waste` | supplier tables | No | No | Low | Lossy |
| 30 | `20260520_0030_admin_purchases` | `20260520_0029_admin_suppliers` | purchase tables and constraint replacement | No | Yes | High | Lossy |
| 31 | `20260520_0031_inputs_supplies` | `20260520_0030_admin_purchases` | procurement columns, defaults, and checks | Yes | Yes | High | Lossy |
| 32 | `20260520_0032_fin_recon` | `20260520_0031_inputs_supplies` | financial-reconciliation schema | No | No | Medium | Lossy |
| 33 | `20260520_0033_cleaning_logs` | `20260520_0032_fin_recon` | cleaning-log tables | No | No | Low | Lossy |
| 34 | `20260520_0034_sanitary` | `20260520_0033_cleaning_logs` | sanitary-verification tables | No | No | Low | Lossy |
| 35 | `20260520_0035_equipment` | `20260520_0034_sanitary` | equipment-maintenance tables | No | No | Low | Lossy |
| 36 | `20260520_0036_incidents` | `20260520_0035_equipment` | quality-incident tables | No | No | Low | Lossy |
| 37 | `20260520_0037_admin_users` | `20260520_0036_incidents` | user fields and deterministic assignment backfills | Yes | No | High | Lossy |
| 38 | `20260520_0038_roles_permissions` | `20260520_0037_admin_users` | role, permission, and assignment tables | No | No | Low | Lossy |
| 39 | `20260520_0039_system_settings` | `20260520_0038_roles_permissions` | settings/history tables and index | No | No | Medium | Lossy |

## Data-preservation evidence

The full matrix uses synthetic, non-production fixtures at the historical schema that actually
existed before each transition. It covers:

- code-specific and default display-order backfills;
- cash-close-to-payment-method aggregate backfill with Decimal values;
- static payment and discount category inserts;
- duplicate `CARD`/`OTHER` merge without losing the economic amount;
- return-reason, close-mode, and empty-counter defaults;
- deterministic brand assignment across multiple branches;
- procurement defaults, nullable values, and Numeric precision;
- user-surface and earliest-active-branch backfills.

Fixtures include stable UUIDs, valid FKs, NULLs where historically legal, Unicode, timestamps,
multiple branches, one-row and empty-table cases, duplicates that the migration is expected to
merge, and Decimal/Numeric values. A deliberately invalid FK is not inserted because the historical
checkpoint already prohibited it.

Revision `0009_cash_close_payment_methods` backfills a missing CASH aggregate from the canonical
close. Its conditional compatibility cleanup for denomination tables is statically classified; the
canonical `0008` fixture does not invent those tables. Revision `0014_remove_other_payment_method`
intentionally merges an `OTHER` close row into an existing `CARD` row. These are accepted only when
row-count changes are explained and the causal entity, Decimal amount, and surviving IDs remain
verified; they are not evidence that arbitrary historical loss is acceptable.

## Model/schema drift and database objects

The fast and full modes run Alembic's raw autogenerate check with type and server-default
comparison. Raw autogenerate currently reports known differences; that output is not described as
clean. Every reported operation must map to the versioned fingerprint baseline in the migration
test. Index fingerprints include schema, table, name, uniqueness, ordered columns/expressions, and
predicate. Server-default fingerprints include schema, table, column, the normalized database
default, and the expected metadata-default state. Check fingerprints include schema, table, name,
and normalized SQL expression.

The validation also compares model and database tables, columns, primary keys, foreign keys
including `ON DELETE`, unique constraints, named check constraints, and indexes including
uniqueness and column order. Naming/truncation differences are accepted only through an exact
versioned pair containing both names and both semantic expressions. `alembic_version` is the only
intentional database-only table.

Any difference must be classified before correction:

- `REAL_SCHEMA_DRIFT`: fix with a new forward migration when model intent is canonical.
- `KNOWN_INTENTIONAL_DB_ONLY`: retain only when its complete fingerprint is in the reviewed
  baseline.
- `KNOWN_NAMING_ONLY`: retain only when the versioned model/database pair proves equivalent
  semantics.
- `ALEMBIC_AUTOGENERATE_LIMITATION`: add an explicit catalog assertion.
- `UNKNOWN_SCHEMA_DRIFT`: fails closed and blocks acceptance until resolved.

The database under validation never teaches the classifier what to accept. A new DB-only index,
default, check, unrecognized autogenerate operation, or changed semantic fingerprint must fail. It
requires explicit review and a version-controlled baseline change; entire categories are never
ignored. Alembic's raw check plus the exact classifier and catalog assertions jointly form the
migration drift gate.

Do not alter a historical revision or change a model merely to make autogenerate output empty.

## Expand, migrate, contract

### Expand

- Add backward-compatible structures before requiring them.
- Use nullable columns or safe server defaults while old application versions may still run.
- Analyze table rewrites, constraint validation, and index locks before production.
- Add dual-read or dual-write only under a later task with an explicit convergence plan.

### Migrate or backfill

- Make the operation idempotent, observable, resumable, and reconcilable.
- Process bounded batches when volume can cause long transactions or locks.
- Preserve source IDs or write a durable source-to-target mapping.
- Record before/after counts, Decimal totals, NULL handling, failures, and reconciliation evidence.

### Contract

Remove old structures only after the new application version is deployed, compatibility is proven,
the backfill is complete, reconciliation passes, and an approved operational window exists.

## Roll-forward and downgrade policy

Roll-forward is the primary recovery strategy. A previous application artifact may be restored only
while it remains schema-compatible. Generic Alembic downgrade is not a release rollback procedure.
Most current downgrades drop tables or columns and are therefore lossy. Constraint-narrowing
downgrades can fail on values admitted by the newer revision. The `0014` downgrade cannot recreate
the original `OTHER` classification or split a merged amount and is not semantically meaningful.

A future migration must include:

- fresh-base and every-supported-checkpoint upgrade evidence;
- data-preservation fixtures for every transformation;
- schema-drift and catalog-object results;
- lock-risk analysis and an estimated operational window based on representative data;
- interruption behavior, idempotency, observability, and reconciliation;
- an application compatibility and roll-forward plan;
- restore evidence when the change can corrupt or discard data.

## Interruption and export sanity

The full matrix injects a failure after transactional DDL, data insertion, and a temporary revision
update. PostgreSQL must roll all three back, leaving neither a partial object nor a falsely advanced
revision. No temporary Alembic file is added to the canonical chain.

The bounded dump/restore check exports a head database containing synthetic audit/outbox rows in
custom format and restores it into another empty ephemeral database. It verifies schema revision and
selected rows. This is only baseline exportability evidence; it is not backup policy, PITR, disaster
recovery, or production restore proof.
