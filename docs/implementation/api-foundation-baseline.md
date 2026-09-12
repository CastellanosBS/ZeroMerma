# API foundation baseline

ZM-FIN-010 establishes an executed backend baseline without implementing the later
security, ledger, idempotency, or feature-completion tasks. FastAPI/Pydantic remains
the HTTP contract authority, SQLAlchemy/PostgreSQL remains the persistence boundary,
and monetary values remain `Decimal`/`Numeric`.

## Initial findings and corrections

The full `apps/api` Ruff scan reported 412 findings in 50 files, including historical
Alembic formatting that was outside the narrower foundation command. Strict mypy
reported 213 errors in 26 files. The existing default pytest discovery omitted
`apps/api/unit_tests` and `apps/api/migration_tests`.

The corrections preserve business rules and database schema:

- Sorted imports, removed unused names, wrapped long expressions/strings, and added
  the missing product-readiness type import. Alembic edits are formatting only;
  no revision, constraint value, migration operation, or schema target changed.
- Typed SQL filter expressions, selectable results, tuple rows, read-only sequences,
  and list-returning interfaces according to the actual SQLAlchemy APIs.
- Validated persisted closed values against their existing Pydantic aliases at
  response boundaries. Module-level typed adapters reuse the compiled validation
  schema instead of rebuilding it for each row.
- Narrowed optional values before use, gave heterogeneous internal structures exact
  types, and separated loop variables that represented different record types.
- Kept empty monetary sums as `Decimal`, preserved literal constants, and supplied
  concrete request types for recipe inputs, removing the old attribute-ignore there.
- Updated API assertions from the retired `detail` error alias to canonical `message`
  as part of the ZM-FIN-009 contract cutover. Error status and business-message checks
  remain in place.
- Fixed correction/return history searches to match the `COR-`/`DEV-` folios already
  emitted by the API. Existing UUID, operator, reason, workstation, and scope filters
  remain in place; the original failing assertions are preserved.
- Corrected tests to inspect the mapped audit/outbox fields `metadata_` and
  `occurred_at`, use the existing seed's exact reason label (`Wrong Quantity`), and
  retain explicit supplier UUID conversion after the lint cleanup.

No mypy strict option or Ruff rule was relaxed. No test was deleted, skipped, or marked
expected-failing. No new business capability, database migration, or endpoint was added
by ZM-FIN-010. Contract policy/generation changes are recorded separately in ZM-FIN-009.

## Discovery and isolation

`pyproject.toml` and the shared validation scripts define the canonical discovered
suites. The API contains 43 integration-test modules, four unit-test modules, and one
migration-test module. Counts of executed cases include parameterization and are
reported by pytest rather than inferred from the number of test functions.

Run database-backed pytest only through the protected harness:

```powershell
& .\scripts\dev\run-api-tests.ps1
```

No explicit targets means every test path in `pyproject.toml`. A focused API run is:

```powershell
& .\scripts\dev\run-api-tests.ps1 -TestTarget @(
  'apps/api/tests',
  'apps/api/unit_tests'
)
```

The harness provisions a uniquely named PostgreSQL 16 database/container, publishes
only a loopback port, uses a tmpfs data directory, validates the destructive-test
identity before SQL, and removes its container in cleanup. It never falls back to an
operational database. API fixtures migrate the fresh database to head, truncate only
that authorized test database between tests, and execute the real local seed.

The migration suite additionally checks graph/fresh schema drift/seed and representative
historical transitions. It uses its own protected, temporary databases. Test functions
contain no skip/xfail exclusions; no flaky-test retries were introduced.

## Executed evidence

Validation environment: Windows, Python 3.12.6, uv 0.11.4, Node 22.23.2, Corepack 0.34.6,
pnpm 10.33.0, and disposable PostgreSQL 16. The repository toolchain preflight passed.

| Command | Observed result |
| --- | --- |
| `uv run ruff check apps/api` | All checks passed. |
| `uv run mypy apps/api/src` | Success: no issues found in 285 source files. |
| `uv run python -m compileall -q apps/api/src apps/api/tests apps/api/unit_tests apps/api/migration_tests` | Exit 0. |
| `git diff --check -- apps/api` | Exit 0; no whitespace errors. |
| Executable AST comparison of Alembic revisions against the baseline | 39 revisions checked; zero executable changes after excluding import ordering. |
| Test structure comparison against the baseline | 46 tracked API test modules checked; no removed test functions or reduced assertion counts. |
| Protected initial API/unit pytest snapshot | 301 passed, 6 failed in 1201.71 seconds; all 307 discovered cases executed. See failure analysis below. |
| Protected API/unit collection before the final contract-policy review | 309 tests collected; subsequent contract cases are included in the clean-checkout CI count. |
| Canonical full migration stage | Passed; stage evidence `366da7f65e604ae6bdb3776ef67e43aa/Migrations.json`. |
| First focused rerun of the six initial failures | 4 passed, 2 failed in 33.03 seconds; exposed two further incorrect test expectations, corrected below. |
| Final focused rerun of the six initial failures | 6 passed in 38.74 seconds on disposable run `67180e04c4b34d2f9ee192e11fd26a44`; cleanup completed. |
| First hosted backend run, commit `972909772274f6c43e367d778b7d36cc5ee9eb57` | 313 passed, 1 failed in 366.58 seconds; Ruff and strict mypy (295 files) passed. The remaining test expected a server-error detail intentionally removed by ZM-FIN-009. |
| Focused server-error contract correction | 2 passed in 6.49 seconds: database-backed product-availability test and explicit safe-server-error unit test; disposable run `18ee3930a2e64e89aa356ebadf1c0327` cleaned up. |
| Final canonical backend stage | The `Validate Backend` CI job executes the complete integrated API/unit snapshot; its successful result and JUnit are required by `Foundation required`. See the foundation validation map. |

The first pytest process had already imported its test snapshot before the supplier
UUID and audit-field corrections were applied. Two supplier tests failed on the old
local name; the discounts test inspected SQLAlchemy's `MetaData` instead of audit JSON;
one corrections test used a nonexistent audit timestamp attribute. The remaining two
failures exposed the real history-folio search defects fixed above. No expectation was
weakened to clear these failures.

The first focused rerun verified both folio searches and exposed two later assertions
in the corrections tests: the outbox timestamp used the same nonexistent `_utc`
suffix, and the expected reason label did not match the unchanged canonical seed.
Both now assert the actual mapped field and exact seeded label.

The first hosted run executed all 314 API/unit cases on Ubuntu with Python 3.12.14.
Its single failure was the existing product-availability test expecting a schema
detail from a `501` response. ZM-FIN-009 deliberately hides all server-error details.
The test retains its name and `501` assertion and now verifies the exact canonical
envelope, request correlation, null details/field errors, and absence of schema
internals. The availability endpoint remains unimplemented; no handler, schema, or
business behavior was changed to satisfy this test.

The hosted log is `.tmp/ci-backend-34724946542.log`; the focused correction produced
`.tmp/api-foundation-safe-5xx.log` and `.tmp/api-foundation-safe-5xx.xml`.

Local command logs are in `.tmp/zm-fin-010-ruff.log`, `.tmp/zm-fin-010-mypy.log`,
`.tmp/api-baseline-tests.log`, `.tmp/api-foundation-failures.log`, and
`.tmp/api-foundation-failures-final.log`; focused reruns also write matching `.xml`
JUnit files. Migration stage evidence is under
`.tmp/validation/foundation/366da7f65e604ae6bdb3776ef67e43aa/`. These are validation
artifacts, not runtime inputs.

## Limits and later work

A green foundation baseline demonstrates the checked behavior, not production readiness.
Permissions/scopes, durable command idempotency, financial and inventory convergence,
electronic payment integration, and real outbox consumers remain assigned to their
existing ZM-FIN tasks. Current worker characterization is documented separately.

The [foundation validation map](foundation-validation.md) identifies the implementation
branch and whole-commit acceptance checks. The task delivery records the successful
hosted run and immutable commit; this document does not substitute a static-check
result for that execution evidence.
