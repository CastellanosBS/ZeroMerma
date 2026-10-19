# ZM-FIN-039 transaction boundary validation

Branch: `codex/zm-fin-039-transaction-boundaries`.
Accepted base: `864f5ba0670d191d578760f74fb0f44c004277fe`.

The implementation is frozen and dedicated local acceptance is complete: 76
cases passed together, followed by three passing PostgreSQL regressions for the
final first-INSERT exception-boundary correction. These are 79 unique dedicated
cases, plus four static ownership gates. The broader seven-file regression also
passed all 134 cases. Local validation is complete. Accepted-base results are not
new evidence for 039. The convention is documented in
[transaction-boundaries.md](../architecture/transaction-boundaries.md), with its
[ownership inventory](../architecture/TRANSACTION_BOUNDARY_MATRIX.json).

Integrated delivery requires all eight Foundation stages and `Foundation
required` on the delivered immutable commit. The verified SHA and workflow link
accompany delivery; no future CI result is presumed by this document.

## Required acceptance

| Area | Required observation | Execution evidence |
| --- | --- | --- |
| Ownership inventory | Every discovered database boundary has a declared role and owner; standalone service owners expose failure cleanup | 4 static gates passed against 162 sites, 93 symbols with explicit commit and 32 executor delegators |
| Unexpected failure | Failures before/after flush, audit/outbox exceptions and unrelated integrity violations leave no additional business effects | Combined 76 passed; three subsequent PostgreSQL uniqueness cases passed after the final exception-boundary correction |
| Session reuse | A failed owner leaves the session reusable; no hidden helper commit confirms caller changes | Combined and final focused cases passed |
| Nested calls | Participating helpers compose atomically; an inner executor is rejected before assuming the outer transaction | Combined core nested-entry and administrative delegate cases passed |
| Authentication | Successful login persists `last_login_at`; security rejections retain only the documented security evidence | All 45 identity cases passed within the combined 76-case execution |
| Read-only paths | Request cleanup never commits forgotten writes; replay/recovery and worker reads preserve their explicit boundaries | Core cleanup cases and static gate passed; worker baseline is unchanged and not reclassified as a processor |
| Existing locks and recovery | Cash/document/inventory boundaries, same-key recovery and failure rollback remain valid | 134/134 regression cases passed, including the 49 common idempotency and 49 concurrency cases |
| Integrated delivery | Eight Foundation stages plus required aggregate pass on the delivered SHA | Verified SHA and workflow link accompany delivery; no future result is presumed |

An assertion of zero added rows applies to unexpected failure within the owned
transaction. Declared terminal rejections and independent authorization-denial
audits have different, explicit acceptance counts; they must not be erased to
satisfy an overbroad zero-row assertion.

An exception after a successful commit cannot reverse that durable transaction.
Failure cleanup rolls back only unfinished work, including any subsequent read
transaction. A lost acknowledgement remains a recovery case, not proof that the
business mutation failed.

## Completed local executions

| Execution | Result | Evidence |
| --- | --- | --- |
| Ownership architecture gate | 4/4 passed, exit 0; exact AST sites, valid owner references, cleanup decorators, endpoint contexts and participant restrictions | `apps/api/unit_tests/test_transaction_ownership.py` |
| Combined dedicated acceptance | 76/76 passed, 0 failures/errors/skips, 197.784 s: core 20, identity 45, administrative 11 | `.tmp/validation-published/transactions/acceptance/c0560d1c53b841cf9a262a946b72450a/{transactions.xml,result.json}` |
| Final first-INSERT uniqueness correction | 3/3 passed, 0 failures/errors/skips, 13.938 s: cleaning folio, sanitary folio and equipment code; administrative file now has 14 cases | `.tmp/validation-published/quality-unique-boundaries/acceptance.xml` |
| Seven-file regression | 134/134 passed, 0 failures/errors/skips, 491.192 s | `.tmp/validation-published/transactions/regression/879644d539e944e0bc5d0ff9c0624f00/{transactions.xml,result.json}` |
| Static and contract checks | Repository Ruff, mypy over 353 source files and contract check over 257 OpenAPI operations passed; no contract regeneration | Canonical checks reported by the integrating owner |
| Core failure boundary | 20/20 passed, 0 failures/errors/skips, 48.256 s | `.tmp/validation-published/transactions/core/a34f131352bb47c9bbaa5357eaddd749/{transactions.xml,result.json}` |
| Initial administrative selection | 10 passed, 1 failed, 43.728 s; the report-export fixture lacked its actual JSON/authorization context | `.tmp/validation/admin-transaction-published/admin-transaction-boundaries.xml` |
| Administrative corrected/focused selection | 5/5 passed, 20.026 s; includes the corrected report case and integrity checks | `.tmp/validation/admin-transaction-published/admin-transaction-integrity.xml` |
| Initial identity selection | 41 passed, 2 failed, 103.229 s; the privileged-change fixture selected `USER_UPDATE` where dual control was not required | `.tmp/validation-published/auth-transaction-boundaries/acceptance.xml` |
| Identity corrected/additional selection | 4/4 passed, 13.606 s; two corrected `USER_LOCK` cases plus actual PostgreSQL login integrity failure and independent HTTP-denial audit | `.tmp/validation-published/auth-transaction-boundaries-final/acceptance.xml` |

The initial administrative and identity failures remain visible as diagnostics;
the later combined run passed all 76 corrected cases. That combined run preceded
the final correction which widened three existing `try` blocks to include the
first INSERT flush. The additional three tests exercised those final boundaries
against real PostgreSQL. No commit location or AST call count changed. This is
76 plus 3 passing cases in separate executions, not a claimed single 79-case run.
Integrated acceptance requires Foundation to validate the complete delivered source together.
Overlapping focused reruns are not additional unique tests.

The regression comprises `test_idempotency.py` (49), `test_cash_concurrency.py`
(29), `test_command_concurrency.py` (9), `test_inventory_concurrency.py` (11),
`test_auth_session_lifecycle.py` (29), `test_tickets_module.py` (4) and
`test_admin_sales_tickets.py` (3). These are the executed counts, without inferring
coverage of unexecuted worker or future functional paths.

The core manifest records base HEAD `864f5ba` and `working_tree_clean=false`:
it identifies a local execution of the edited tree, not acceptance of that base
commit or of a future delivery commit.

## Reproduction

Use PowerShell 7 and the pinned toolchain documented in the [README](../../README.md).
Database tests use the canonical isolated-database harness, exposed by
`scripts/dev/run-api-tests.ps1`. The scoped execution wrappers also invoke
`Invoke-ZeroMermaIsolatedDatabase` directly with the same guards and protected
output. The harness creates and destroys disposable PostgreSQL. Never point this
validation at the normal local database or a persistent operational volume.

The existing protected wrapper captures child output before emitting a sanitized
version. For the complete canonical backend check:

```powershell
. ./scripts/powershell/ZeroMerma.ValidationArtifacts.ps1
$validationExit = Invoke-ZeroMermaProtectedValidationProcess `
  -FilePath (Get-Command pwsh).Source `
  -ArgumentList @('-NoProfile', '-File', 'scripts/dev/check-foundation.ps1', '-Stage', 'Backend') `
  -CaptureDirectory '.tmp/validation-private/transaction-boundaries'
if ($validationExit -ne 0) { throw "Backend validation failed with exit $validationExit." }
```

The three dedicated PostgreSQL files can be reproduced independently with the
same isolated runner and protected output:

```powershell
foreach ($testTarget in @(
  'apps/api/tests/test_transaction_boundaries.py',
  'apps/api/tests/test_admin_transaction_boundaries.py',
  'apps/api/tests/test_auth_transaction_boundaries.py'
)) {
  $validationExit = Invoke-ZeroMermaProtectedValidationProcess `
    -FilePath (Get-Command pwsh).Source `
    -ArgumentList @('-NoProfile', '-File', 'scripts/dev/run-api-tests.ps1', '-TestTarget', $testTarget) `
    -CaptureDirectory '.tmp/validation-private/transaction-boundaries'
  if ($validationExit -ne 0) { throw "Validation failed for $testTarget with exit $validationExit." }
}
```

Static ownership and source checks remain:

```powershell
uv run --frozen pytest apps/api/unit_tests/test_transaction_ownership.py -q
uv run --frozen ruff check .
uv run --frozen mypy apps/api/src apps/worker/src
git diff --check
```

Final publication must preserve failure/error/skip counts and the original exit
status. Raw pytest representations, cookies, CSRF/reset values and private files
must not enter published artifacts. A local manifest from an edited tree records
that execution, not acceptance of a later commit.

## Known boundaries and follow-up

No migration, API contract or client-type change was introduced. The worker remains a
read-only outbox poller; processing belongs to later worker tasks. Financial totals,
the missing order-payment ledger in 042 and POS physical attribution are unchanged.
Existing administrative idempotency and reconciliation gaps remain assigned to
their later tasks.

The plan records an older `AuthService.login` persistence diagnosis. That class
has been replaced by `SessionService`, whose accepted-base login already persisted
`last_login_at`. This task verifies that behavior directly; it does not claim a
new repair of an absent login commit. No omitted success commit was found in the
reviewed routes. The implemented fixes address failure cleanup, nested ownership,
security-helper composition and exact error classification.

One separate trace-identity defect remains for 040:
`modules/quality/application/equipment_services.py::AdminEquipmentMaintenanceService.create_maintenance`
constructs an `EquipmentMaintenanceRecord` whose Python UUID default is materialized
at flush, but builds audit/outbox identifiers from `record.id` before that flush.
The model and call order must be corrected and tested under correlation work; 039
does not claim that all existing trace payloads already contain valid identities.

No runtime database, production deployment or external credential was modified by
the documentation work. This transaction convention is not a release-readiness
claim.
