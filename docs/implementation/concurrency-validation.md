# ZM-FIN-036–038 concurrency validation

Branch: `codex/zm-fin-036-038-concurrency`.
Accepted base: `9376bf126a97a13f72db17a630cd1d97509b60d5`.

This record covers the common cash admission boundary, concurrent inventory
mutations and safe retry of transient PostgreSQL conflicts. The protocol is
documented in [concurrency.md](../architecture/concurrency.md). Local acceptance is
complete: the final combined 49-case runner and all 124 inventory-writer regressions
passed. Only completed executions below count as evidence for this block, without
reusing results from the accepted base.

Integrated acceptance requires all eight Foundation stages and `Foundation
required` on the delivered immutable commit. The commit and verified workflow
link accompany delivery. Local test results do not establish a future CI result.

## Acceptance coverage

| Area | Required evidence | Current result |
| --- | --- | --- |
| Sale versus close | Separate transactions, both lock orderings, committed sale included in the existing close projection or rejected without effect | Final combined runner and complementary cash coverage passed |
| Other cash effects | Operational payment, operational discount, return refund and POS order payment admission versus close; both orderings and correct rollback | Cash-boundary and complementary CASH/CARD cases passed |
| Independent cash contexts | Different shifts progress without a global boundary | Cash-boundary cases and three prior concurrency regressions passed |
| Close and replay | Two close intentions, same-key replay, historical result recovery and no second effect | Complementary cash/close/FK-reservation cases passed |
| First inventory row | Two concurrent creators leave one natural-key row and both committed movements | Dedicated inventory suite passed |
| Existing inventory rows | No lost increments/decrements, ordered multi-balance access, stock-shortage rejection and independent keys | Dedicated inventory suite passed |
| Atomic stock effects | Failure after a movement/balance flush leaves neither effect; unexpected integrity violations are not swallowed | Dedicated inventory suite passed |
| Retryable conflicts | Real lock timeout/deadlock, full rollback, safe 409 and same-key retry; original context and body retained | 9 command tests and 29 API-client tests passed |
| Local regression | Cash/inventory callers, shared coordinator, generated contracts and static checks | 124 writer cases, complementary cash cases and static/contract checks passed |
| Integrated delivery | All eight Foundation stages and required aggregate on the delivered commit | Verified SHA and workflow link accompany delivery; no future run result is presumed |

Tests must coordinate real database connections with barriers or events and inspect
PostgreSQL wait relationships. Sleeping and hoping that two requests overlap is
not acceptance evidence. `testing/concurrency.py` guards its database connection
before exposing transaction/process identities and uses `pg_blocking_pids` to
confirm the intended waiter and blocker.

HTTP authentication already locks the user and authentication-session rows.
Same-cookie HTTP requests can therefore serialize before reaching the economic
boundary. Domain concurrency tests use separate transactions without those HTTP
locks, preserving the actual command executor, authorization and economic action.
HTTP tests separately check the public error contract and recovery behavior.

## Scope boundaries

ZM-FIN-037 guarantees when a POS order action may write relative to close. The
existing `CustomerOrderPayment` to `CashMovement` omission remains ZM-FIN-042;
the close formula and totals are unchanged. Evidence for orders must not be
reported as proof of complete order-payment inclusion in the financial ledger.
For cash effects already represented in that ledger, acceptance checks reconcile
the final close equation as well as the effect count.

ZM-FIN-038 centralizes the five existing administrative stock writers and preserves
their physical semantics. It does not add a POS inventory ledger, inventory
reservations, new production costing or broader financial reconciliation. The
existing balance uniqueness constraint is reused; no migration is introduced.

The 5-second lock timeout and `CONCURRENCY_RETRY` mapping belong to the shared
idempotency executor and its adopted commands. They do not bound earlier HTTP
authentication waits or establish that contract for administrative routes that
have not yet adopted the executor.

The functional matrix must retain the 19 administrative idempotency gaps assigned
to 077/080/085, purchase PATCH UI gap `GAP-0991` and reconciliation gaps. Rows may
record verified concurrency without becoming `FeatureComplete` or closing their
other future tasks.

## Reproduction and evidence handling

Use PowerShell 7 from the repository root and install the pinned toolchain as
described in the [README](../../README.md). PostgreSQL
checks must run through the guarded disposable harness, never against the normal
development volume. Run the three dedicated suites with:

```powershell
pwsh -NoProfile -File scripts/dev/run-concurrency-validation.ps1 -Suite All
```

The runner also accepts `-Suite Commands`, `-Suite Cash` and `-Suite Inventory`.
It executes `test_command_concurrency.py`, `test_cash_concurrency.py` and
`test_inventory_concurrency.py` respectively, using the canonical isolated
PostgreSQL harness and protected child-process output. It publishes sanitized
`concurrency.xml` and `result.json` under
`.tmp/validation-published/concurrency/<run_id>/`, including failed runs. The
manifest records the selected targets, timing, current commit and working-tree
state. A local run against an edited tree is evidence of that loaded source, not
immutable-commit acceptance.

The final combined runner retains passing-test capture in JUnit so transaction
probes and observed wait relationships remain reviewable without raw SQL or secret
parameters. Early individual executions may predate that capture setting; they
are not substituted for the final combined evidence.

Static and semantic checks:

```powershell
uv run ruff check .
uv run mypy apps/api/src apps/worker/src
uv run python scripts/dev/check-functional-operation-matrix.py
git diff --check
```

Run a complete Foundation gate through the protected process boundary:

```powershell
. .\scripts\powershell\ZeroMerma.ValidationArtifacts.ps1
$exitCode = Invoke-ZeroMermaProtectedValidationProcess `
  -FilePath pwsh `
  -ArgumentList @('-NoProfile', '-File', 'scripts/dev/check-foundation.ps1', '-Stage', 'All') `
  -CaptureDirectory (Join-Path (Get-Location) '.tmp/validation-private/concurrency')
if ($exitCode -ne 0) { throw "Foundation failed with exit code $exitCode" }
```

The eight stages are Preflight, Backend, Worker, Migrations, Contracts, Web,
Browser and Negative. CI uses fresh isolated jobs and requires the aggregate
`Foundation required` status. Protected process output preserves the original
exit code. Publication sanitizes supported text/JSON/JUnit evidence and retains
failed-test counts; it never falls back to uploading a raw tree. Verify exact SHA,
clean checkout, archive digests and source fingerprints for delivered CI evidence.

## Execution record

| Execution | Result | Protected evidence |
| --- | --- | --- |
| Final combined runner, run `110b38d483174d748f555ac9df9325dc` | 49 passed (29 cash, 9 command conflicts, 11 inventory), 0 failures/errors/skips; 200.769 s | `.tmp/validation-published/concurrency/110b38d483174d748f555ac9df9325dc/concurrency.xml` and `result.json` |
| Eight existing inventory-writer/idempotency suites, run `29c4ea3c819e4c92b61883c77b3820d0` | 124 passed, 0 failures/errors/skips; 580.933 s | `.tmp/validation/inventory-writers-published/inventory-writers-regression.xml` |
| Inventory concurrency, run `436f87ed60fe4e96aa7512e982cb8a78` | 11 passed, 0 failures/errors/skips; 42.790 s | `.tmp/validation/inventory-concurrency-published/inventory-concurrency.xml` |
| Cash boundary, run `36ebda8e0fd54ca880188fac8655e863` | 28 passed, 0 failures/errors/skips; 153.603 s: 25 dedicated cases and 3 prior sale/order/return concurrency regressions | `.tmp/validation-published/cash-boundary-final/acceptance.xml` |
| Complementary cash coverage, run `2477bae112a34428b6a5552d1143cb42` | 14 passed, 0 failures/errors/skips; 65.469 s: 4 new CARD operational cases and 10 prior CASH/close/FK-reservation cases | `.tmp/validation-published/cash-boundary-operational/acceptance.xml` |
| Transient command conflicts, run `053f9720f7b640a0941b1bdf63b7e506` | 9 passed, 0 failures/errors/skips; 23.756 s; edited working tree | `.tmp/validation-published/concurrency/053f9720f7b640a0941b1bdf63b7e506/concurrency.xml` and `result.json` |
| Full shared-executor regression, run `ee3bea92f2f6491cae64f078eeb6458a` | 49 passed, 0 failures/errors/skips; 108.762 s | `.tmp/validation-published/concurrency-executor/acceptance.xml` |
| Shared-document regression across independent cash contexts, run `31f4cfe05ec74a35b749b254e0709de9` | 6 passed, 0 failures/errors/skips; 36.547 s: 2 return, 3 POS order and 1 cross-surface order case | `.tmp/validation-published/document-lock-coverage/acceptance.xml` |
| API-client coordinator | 29 tests passed; lint and typecheck passed | Local execution reported by the implementation owner |
| Repository Ruff | Passed | `uv run ruff check .` |
| API and worker mypy | 352 source files passed | `uv run mypy apps/api/src apps/worker/src` |
| Contract drift check | 257 operations passed; generated artifacts byte-identical | `corepack pnpm contracts:check` |
| Functional matrix including the new internal runner | 333 operations passed; 19 administrative idempotency gaps retained | `uv run python scripts/dev/check-functional-operation-matrix.py` |

The final combined JUnit preserves 64 backend-process/transaction probes and 31
observed lock waits. Its manifest explicitly records `working_tree_clean=false`:
this is validation of the edited local source, not evidence of the accepted base
SHA or the future delivery commit. All disposable databases were cleaned up.

The 124 regressions comprise `test_admin_inventory` (6), `test_admin_waste` (5),
`test_admin_purchases` (8), `test_admin_production` (7), `test_admin_transfers` (7),
`test_purchase_idempotency` (32), `test_production_idempotency` (42) and
`test_transfer_idempotency` (17).

The inventory suite observes actual PostgreSQL waits. Its reversed-write-set case
also uses `NOWAIT` to prove that the waiter does not acquire later keys before the
minimum key. Other cases cover fresh state after waiting, repeated deltas before
flush, separate products/branches, the unrelated-integrity-error path, expired
transaction handles and rollback of business/audit/outbox after a movement.

The two cash executions cover 42 unique cases: 29 new cash-boundary tests, three
adapted sale/order/return concurrency tests and ten earlier cash/close/FK cases.
The final combined runner repeats the 29 new cases with the command and inventory
suites; those repeated cases must not be added to the unique total.

No production load, deployment, backup/restore or external-device acceptance is
implied by these bounded local concurrency tests.

The shared-executor regression updates the prior raw-DBAPI-error expectations for
serialization/deadlock aborts to `CommandConcurrencyConflict`, verifies the original
SQLSTATE in the cause, proves full rollback and retries the same key successfully.
An unrelated connection termination still propagates its database error. The
reservation timeout test checks restoration of the 5-second business budget before
the action; the dedicated command suite separately verifies restoration of the
caller's prior setting after success and replay. The complete 49-case rerun passed
after correcting these expectations; the preceding run had 48 passes and one
obsolete timeout assertion and is not acceptance evidence.

The six shared-document cases strengthen prior coverage without adding new test
counts. POS competitors use distinct cash sessions, workstations and users in the
same branch against one sale or customer order, so the cash boundary cannot mask
the document lock. PostgreSQL must report the exact winning backend as the blocker;
the original effect, entitlement and state-conflict assertions remain in place.
The focused JUnit records the passing outcomes but does not retain passing-test
stdout; it is not substituted for the combined runner's captured PID/XID evidence.
