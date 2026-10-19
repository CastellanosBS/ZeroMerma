# ZM-FIN-040 operation-context validation

Status: implemented, with the local evidence recorded below. The design is
[operation-context.md](../architecture/operation-context.md). The immutable-commit
delivery rule below distinguishes these edited-tree checks from integrated CI
acceptance; this record does not assert a future workflow result.

## Acceptance and evidence

| Criterion | Direct evidence | Local result |
|---|---|---|
| Request identity | `test_operation_context.py`, error-contract and idempotency-HTTP tests cover valid/absent/invalid/duplicate inputs, safe errors and CORS; shared transport creates a fresh UUID per attempt. | API unit suite: 173 passed; API-client: 35 passed; affected POS tests: 84 passed. |
| Trusted source, actor and operation | `test_operation_context_http.py` covers verified POS/Backoffice origin, spoofed metadata, denial, command replay/recovery and precommit rollback; storage/projection tests use canonical columns rather than payload hints. | All HTTP context cases passed in the 53-case regression described below; storage/audit: 13 unique cases passed across two runs. |
| Transactional producers | Twelve previously audit-only operations now append minimal events in their existing transaction; failure is injected after real flush. Direct POS reprint independently resolves the same station/cash context for both writers. | 24 initial producer cases passed; final reprint run: 3 passed, including one additional case and two repeated cases. Total: 25 unique producer cases. |
| Context isolation and security | Savepoint/root rollback, lazy transactions, nested context managers, connection reuse and authenticated rate-limit actor consistency. | Final combined context/rejection regression: 10/10 passed. |
| Historical preservation | Fresh schema/model parity, 0042-to-0043 historical upgrade, version-1 downgrade refusal, and exact trace/idempotency dump/restore. | Final migration subset: 3/3 passed; 43 revisions and 203 expected checks in the fresh-schema baseline. The full migration gate remains part of immutable-commit CI. |
| Worker boundary | Unit and real PostgreSQL polling preserve historical schema version 0 and current version 1; logging contains allowlisted context without payload/credentials; no processing or writes. | Final worker unit: 29 passed, including arbitrary-extra/PII rejection; final PostgreSQL: 5/5 passed. |
| Contracts and ownership | Canonical UUID request parameters and response IDs, idempotent normalization, generated artifacts, transaction inventory and functional matrix. | API-contract tests: 73 passed; `contracts:check`: 257 operations without drift; ownership: four gates passed. Matrix validation and its tests are reported with final source checks. |

Database tests run through the canonical isolated-database harness exposed by
`scripts/dev/run-api-tests.ps1`. No validation uses the normal local database,
production data or a persistent operational volume. Logs and JUnit evidence use
the existing protected-output/publication helpers.

## Existing trace-gap reconciliation

The 26 matrix findings assigned to 040 were reconciled against the actual call
graph: twelve missing producers were implemented and tested, twelve findings
were stale because an existing delegate/helper already wrote the traces, and two
remain with availability task 068. Source-based corrections do not claim that an
existing feature suite was newly executed in 040.

| Existing gap IDs | Inspected path | Final disposition |
|---|---|---|
| 0357, 0358 | Price update delegates to product/class catalog owners | Closed as source findings: the selected owner already writes both traces; the existing nested-delegate transaction test is referenced. |
| 0424, 0425 | Commercial-discount duplicate delegates to create | Closed as source findings: the selected create owner already writes both traces. |
| 0572, 0577 | Role assignment/removal helper | Closed as source findings: the existing shared recorder emits outbox. |
| 0647, 0648, 0653, 0654, 0659, 0660 | User branch assignment/default/deactivation helper | Closed as source findings: the existing shared recorder emits audit and outbox. |
| 0353, 0468 | Input/supply supplier relations | Closed with canonical outbox producer and success/flush-failure tests. |
| 0380, 0598 | Setting update/reset | Closed with minimal setting-key/scope events and transactional tests; values/notes are excluded. |
| 0388, 0392, 0606, 0610, 0614 | Supplier contact/product/branch relation writes | Closed with minimal identity/state events and transactional tests. |
| 0557 | Administrative report export | Closed with generated-export event and transactional tests; no exported rows/filters in the event. |
| 0582, 0753 | Administrative and POS ticket reprint | Closed with accepted-reprint-request events and transactional tests; no claim of successful physical printing. |
| 0510, 0511 | Product branch availability | The endpoint still returns 501 pending the canonical schema in 068. Context work cannot claim this product function is implemented. |

The matrix cites the producer/delegator and tests or the named remaining task.
The nineteen administrative idempotency gaps, purchase PATCH UI gap, physical POS
and financial/reconciliation limitations remain open. No new transaction owner
was introduced: the AST inventory remains 162 sites and 93 explicit-commit symbols.

## Reproducible local evidence

All paths below are ignored protected evidence directories, not repository source.
Counts are per run; overlapping reruns must not be added as unique coverage.

| Evidence | Result |
|---|---|
| `.tmp/validation-published/trace-producers/acceptance.xml` | 24/24, 119.097 s; run `04dcc4c5762142ccb8ec4cb762c53f73`. |
| `.tmp/validation-published/trace-reprint-final/acceptance.xml` | 3/3, 19.415 s; run `32c8b0ac628d4e2d8c33d1cc673a4071`; direct service and both HTTP paths on the final reprint fix. |
| `.tmp/validation-published/operation-trace-storage/acceptance.xml` and `operation-trace-final/acceptance.xml` | 12 initial passes and three final passes, with overlap: 13 unique storage/audit cases. The final XML reports 14.805 s. |
| `.tmp/validation-published/operation-context/http-regressions/d50f22da311a4836b47d1c6a3aedb256/operation-context.xml` | 52/53 passed, 153.431 s. The remaining failure exposed cleanup obtaining a new Session connection inside a closed nested context; the fix reuses the transaction's owned Connection. |
| `.tmp/validation-published/operation-context/savepoint-final/368824ecc2f34d2fbf41a39ea6301a8a/operation-context.xml` | 10/10, 20.733 s: the previously failing authentication rejection plus all nine context transaction cases, including actor consistency. This is a focused corrected run, not a claim of one complete green 53-case rerun. |
| `.tmp/validation-published/operation-context/migration-final/6543ed4033b24e3ba1e2f2c3899b647a/operation-context.xml` | 3/3, 13.605 s, after historical/raw outbox version was explicitly set to 0. |
| `.tmp/validation-published/trace-worker/trace-worker-unit.xml` and `trace-worker-final/trace-worker-postgres-final.xml` | Initial 28 worker unit tests; final PostgreSQL 5/5 in 3.736 s, run `86ef3d73f6b24a62bd566fc113efd971`. |
| Final worker/logging and API runtime-security command output | 80 passed in 15.29 s: 29 worker unit tests plus 51 API security cases, after restricting structured log extras to the explicit allowlist. This final additional unit case is not represented by the earlier 28-case XML. |
| `.tmp/validation-published/operation-context/ci-denial-fix/0a196df489ce4018ba62cea72f3524d3/operation-context.xml` | 23/23 authorization tests, 57.32 s. The isolated denial app installs the canonical middleware and verifies response/audit correlation and authenticated source. |
| `.tmp/validation-published/operation-context/disconnect-final/774aa050826b45eb93e3762ff70ded23/operation-context.xml` | 11/11, 21.07 s: all ten context transaction cases and the original idempotency disconnect regression. The new real-disconnect case failed before the fix (run `2fb0a3e591aa415a8c8b98234e3e4ce4`, 6.55 s), then passed while proving original exception identity, memory restoration, rollback of interrupted traces and safe reuse of the same session. |

The migration and HTTP diagnostic attempts are retained as failures. Contract
normalization was corrected to use uniform UUID request parameters and remain
idempotent; final contract tests pass on the regenerated artifacts. Static checks
also passed full API/worker mypy (356 source files) and both web typechecks.
Whole-repository Ruff passed. The functional validator passed 333 operations,
257 public OpenAPI operations and zero invalid test references, retaining the
nineteen administrative idempotency gaps and two availability trace gaps.
These observations do not establish production load, migration-lock duration or
an end-to-end delivery guarantee.

The first immutable CI run, `39204296401` on
`aaabeb472f17430965eae707153f62cfc973fe2d`, passed seven stages but failed Backend:
1,093 of 1,095 cases passed. A real PostgreSQL disconnect exposed savepoint
cleanup attempting to reapply settings on an invalidated connection, masking the
original database exception. The second failure was an isolated denial-test app
missing the canonical context middleware. This failed run is retained as
diagnostic evidence; it is not acceptance of the corrected commit.
The correction restores in-memory snapshots but skips PostgreSQL settings on an
invalidated connection, preserving the original database exception. Both failed
cases passed in the focused runs above; full-repository Ruff and mypy across 356
source files also passed. Integrated acceptance still requires the corrected
immutable commit's complete CI run.

## Validation commands

Use the pinned toolchain in the repository README. Run database targets through
the protected validation wrapper used by Foundation; the following canonical
harness commands identify the reproducible suites and require disposable data.

```powershell
uv run ruff check .
uv run mypy apps/api/src apps/worker/src
uv run pytest apps/api/unit_tests/test_transaction_ownership.py -q
uv run pytest scripts/dev/tests/test_functional_operation_matrix.py -q
uv run python scripts/dev/check-functional-operation-matrix.py
uv run pytest scripts/dev/tests/test_api_contracts.py -q
uv run pytest apps/api/unit_tests -q
uv run pytest apps/worker/tests apps/api/unit_tests/test_runtime_security.py -q
.\scripts\dev\run-api-tests.ps1 -TestTarget @('apps/api/tests/test_trace_producers.py', 'apps/api/tests/test_operation_trace_storage.py', 'apps/api/tests/test_admin_audit.py', 'apps/api/tests/test_operation_context_http.py', 'apps/api/tests/test_operation_context_transactions.py', 'apps/api/tests/test_auth_transaction_boundaries.py')
.\scripts\dev\run-migration-validation.ps1 -Mode Full
.\scripts\dev\check-foundation.ps1 -Stage Worker
.\scripts\dev\check-foundation.ps1 -Stage Web
corepack pnpm contracts:generate
corepack pnpm contracts:check
.\scripts\dev\check-foundation.ps1 -Stage All
```

Contract generation is a deliberate preparation step before source freeze;
verification after freeze uses `contracts:check` and does not regenerate artifacts.

## Delivery rule and limits

Acceptance is established by the eight Foundation stages and required aggregate
for the immutable delivered commit; its exact SHA and workflow link accompany
delivery. Local edited-tree manifests establish only the tests actually executed,
not immutable-commit acceptance.

The worker remains a read-only baseline. This block does not implement 087's
processing machine, 093's analytical projections or 109's production observability.
Historical data is not promoted to productive history, and unknown causal/source
information is not fabricated. Logs do not substitute for audit and added trace
metadata does not change existing financial or physical semantics.
