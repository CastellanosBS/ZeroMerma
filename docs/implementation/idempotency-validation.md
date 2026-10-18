# ZM-FIN-028 validation

Branch: `codex/zm-fin-028-idempotency`.

This record describes the implementation and executed local validation. Integrated
acceptance is the Foundation run for the exact SHA delivered with this block:
all eight stages and `Foundation required` must succeed. Its immutable run link
and SHA accompany the delivery; this document does not invent a future CI result.

The user authorized only the shared idempotency foundation in ZM-FIN-028 and a
separate adjustment to 30 minutes of inactivity for POS and Backoffice. Existing
business commands are adopted in later tasks, beginning with sale confirmation
in ZM-FIN-029. All data used by this validation is disposable development/test
data; no normal local database is migrated, seeded, reset or restored.

## Acceptance criteria

| Criterion | Required evidence |
|---|---|
| Canonical identity | UUIDv7 header validation, global uniqueness, independent request correlation and contextual fingerprint |
| Replay | Sequential and concurrent same-key requests return one logical result and one effect |
| Incompatible reuse | Payload, operation and context mismatch return 409 without new effects |
| Atomicity | Reservation, business effect, audit, outbox and result commit or roll back together |
| Recovery | Pre-commit failure can retry; post-commit response loss returns the persisted result |
| Authorization | Current actor/capability/scope validated before replay; session replacement does not erase committed identity |
| Privacy/retention | Sensitive responses rejected/minimized; response purge preserves identity and replayable result |
| Concurrency | Different keys and branches advance independently; bounded same-key contention |
| Migration | Fresh database, populated 0041 transition, all historical checkpoints, model parity and restore |
| Contract | Runtime OpenAPI equals generated artifacts; generated TypeScript remains the shared wire source |

The executable acceptance map is:

- `apps/api/unit_tests/test_idempotency_core.py`: UUIDv7, typed canonicalization,
  precision/defaults/presence, sensitive values and aliases, safe response policy.
- `apps/api/unit_tests/test_idempotency_http.py`: empty response statuses and
  distinct retry advice for contention versus unknown external outcome.
- `apps/api/tests/test_idempotency.py`: PostgreSQL transactions and concurrency,
  real HTTP/session admission, replay, changed context, current authorization,
  rollback/retry and a measured replay baseline without an invented latency SLA.
- `apps/api/tests/test_cold_api_startup.py`: a fresh Python subprocess logs into
  POS and executes the first scoped cash-session query without prior executor imports.
- `apps/api/migration_tests/test_migration_validation.py`: the full 42-revision
  chain, populated transition, exact schema parity, direct database defenses and
  matching dump/restore of business data with idempotency identity.

The test-only HTTP probe is assembled inside the tests. It is not registered in
the deployed application and does not pretend that existing sale, order or payment
routes have adopted the foundation.

## Canonical commands

Use the pinned toolchain and activate the existing local Node toolchain when the
host default differs. Database validation uses the guarded ephemeral harness:

```powershell
./scripts/dev/run-migration-validation.ps1 -Mode Full
./scripts/dev/run-api-tests.ps1 -TestTarget @(
  'apps/api/unit_tests/test_idempotency_core.py',
  'apps/api/unit_tests/test_idempotency_http.py',
  'apps/api/tests/test_idempotency.py',
  'apps/api/tests/test_cold_api_startup.py'
)
./scripts/dev/check-foundation.ps1 -Stage Contracts
./scripts/dev/check-foundation.ps1 -Stage All
```

## Executed local results

| Validation | Result | Evidence |
|---|---|---|
| Core idempotency units and operation-policy classification | 28 passed, 23.182 seconds | `.tmp/validation-published/idempotency-focused/idempotency-unit-final.xml`; isolated run `2db7e9f20bfa4addbb4d42dadcf80c97` |
| PostgreSQL and HTTP idempotency acceptance | 47 passed, 146.040 seconds | `.tmp/validation-published/idempotency-focused/idempotency-focused.xml` |
| Entry-before-write and replay after closing the cash session | 2 passed, 12.461 seconds; no errors or skips | `.tmp/validation-published/idempotency-focused/idempotency-context-contracts.xml` |
| Cold API startup regression | 1 passed, 16.789 seconds; fresh subprocess login and first scoped cash query | `.tmp/validation-published/idempotency-focused/idempotency-cold-startup.xml` |
| Combined API and unit collection | Passed after giving the core unit module a unique basename; collection only | `.tmp/idempotency-collection.xml` |
| API session inactivity at 30 minutes | 29 passed, 162.084 seconds | `.tmp/validation-published/idempotency-focused/idle-thirty-api.xml` |
| Full migration validation | 15 passed, 203.57 seconds; 42/42 historical checkpoints and nine data-preservation cases | `.tmp/idempotency-migrations-final.log`; isolated run `126c95e2a93a4735820eb06e718a6fdc` |
| Foundation Contracts | 51 passed, 141.79 seconds; 240 OpenAPI operations, 59 collections, zero generated drift | `.tmp/validation-published/foundation/63c65dc090b24f9a8b6cbcb586a0d696/Contracts.json` |
| Foundation Web | 489 unit tests and 11 mocked browser tests passed in 152.57 seconds; lint, types and production builds passed | `.tmp/validation-published/foundation/063ac6633b654e1792c1af3849facb22/Web.json` and `Web-output.log` |
| Foundation Browser after startup correction | 8 real browser tests passed: POS 2, Backoffice 6; exit 0 | `.tmp/validation-published/foundation/c44bfd3ca6954abcbc4613df43fa40fe/Browser.json`; isolated browser run `ee721542c6834e49891db10baf76927f` |
| Migration source and tests | Ruff passed | `uv run --frozen ruff check apps/api/alembic/env.py apps/api/alembic/versions/20261018_0042_idempotency.py apps/api/migration_tests/test_migration_validation.py` |
| Integrated Python quality | Ruff passed; strict mypy passed for 330 source files | Canonical API and worker source validation |
| Bounded secret scan | 2,206 files inspected, zero findings; no supplied secret files | Git index/worktree, the protected 47-test, 28-test and 29-test XML reports, and the final migration log |

The PostgreSQL/HTTP module has 49 distinct passing cases across the 47-case and
two-case runs above; they are separate executions, not one 49-case full run. The
bounded scan does not cover Git history, container image layers or regression
artifacts published afterward.

The PostgreSQL probe measured one new-command execution at 79.552 ms and an
average replay of 24.233 ms across eight repetitions. This is a local baseline on
a shared development host, not a production SLA, throughput capacity or tail
latency guarantee. The assertion of interest is also behavioral: replay does not
repeat the domain action or its effects.

The final migration run verified all 80 pre-existing tables unchanged across the
populated 0041→0042 transition, no fabricated historical intentions, twelve invalid
record variants rejected, and 24 immutable terminal fields. It exercised an actual
premature connection commit and confirmed rollback of the accompanying business
effect. Expired payload purge retained the reference and response hash; deletion,
incompatible identity mutation, early/unsafe purge and `UNKNOWN`→`PROCESSING` were
rejected. Empty downgrade succeeded; populated downgrade was refused. Dump/restore
preserved the complete idempotency record alongside audit/outbox and business
data. The guarded harness exited successfully and cleaned its disposable database.

These local commands ran against the evolving working tree. Final acceptance
uses a clean checkout of the delivered commit; a manifest's end-of-run HEAD alone
does not prove which source a long-running process imported. Earlier failing
diagnostic runs are not counted as acceptance. In particular,
`.tmp/idempotency-migrations-full.log` passed before the final response-digest and
JSON-shape hardening and cannot certify that later schema.

## First CI diagnostic and corrective validation

[Foundation run 39150148122](https://github.com/CastellanosBS/ZeroMerma/actions/runs/39150148122)
tested commit `e2598fe7cd55a31d321c5303254bfc84eccb4b59`. Six stages succeeded;
Backend and Browser failed, and `Foundation required` failed. Its eight protected
artifacts were downloaded and verified against GitHub's SHA-256 digests. Their
manifests identify that exact commit and a clean checkout. This run is diagnostic
evidence, not acceptance for the corrective commit.

Backend stopped during collection because the integration and unit files both
used the module basename `test_idempotency.py`. No functional Backend suite ran.
The unit file is now `test_idempotency_core.py`, and combined collection passes
without relaxing pytest's discovery or excluding tests.

Browser exposed a cold-start defect in the first scoped cash query: a late import
registered SQLAlchemy session listeners while a session event was already being
handled. The API failed that query, leaving POS at `/` instead of the required
cash-opening route. Idempotency event helpers now load before request handling.
The fresh-process regression and all eight real browser cases pass after this
correction. No UI navigation workaround or increased timeout was used.

The protected first-run summary is
`.tmp/validation/hosted/39150148122/summary.json`. The corrected code still requires
all eight Foundation stages and `Foundation required` for its own delivered SHA;
neither this first run nor the local regressions claim that final CI result.

## Migration and recovery plan

Migration `20261018_0042_idempotency` extends `20261018_0041_auth_sessions` with an additive shared
store. It must preserve existing documents, sessions, audit and outbox records;
no old request identifiers are imported as business intentions. The historical
chain remains intact and model metadata must match the new constraints and
indexes without broad drift exceptions. Nine model CHECK constraints and the
partial expiry index have exact reviewed reflection fingerprints; changing a
predicate or expression does not inherit an exception. PostgreSQL enforces UUIDv7,
global key uniqueness, complete terminal results with a SHA-256 response digest,
and JSON objects or SQL NULL for response material. Deferred transaction and
immutable-identity triggers add protections beyond SQLAlchemy model comparison.

An interrupted PostgreSQL migration must leave neither partial schema nor an
advanced revision. Before rollout in an eventual operational environment, take
and verify a backup using the applicable deployment runbook. Prefer a corrective
roll-forward migration after records exist. Dropping a populated idempotency store
would erase duplicate-prevention history and is not an acceptable operational
rollback. Restore must recover the matching business state and idempotency
identity together; restoring only one side is unsafe.

This block validates that strategy using isolated PostgreSQL dump/restore and
transition tests. It does not certify an installed operational backup system,
production deployment, external-provider reconciliation or system-wide adoption
of idempotency.
