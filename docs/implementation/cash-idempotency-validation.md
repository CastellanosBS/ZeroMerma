# ZM-FIN-032 cash command validation

Branch: `codex/zm-fin-032-cash-idempotency`.

The accepted base is `3efca6a9cc53fe568b280939a239a2692482e3ee`. This record
describes the four-command adoption in development and isolated tests. Dedicated
PostgreSQL acceptance and real browser recovery passed; the execution table
records the existing-caller regression result separately. Integrated delivery requires all
eight Foundation stages and `Foundation required` on the delivered commit;
the immutable SHA and run link accompany delivery.

## Scope and contract

| Existing command | Operation identity | Successful acknowledgement |
|---|---|---|
| `POST /v1/cash-sessions/open` | `cash_session.open` | 201 `CashSessionOpenResultView` |
| `POST /v1/payments` | `operational_payment.commit` | 201 `OperationalPaymentCommitResultView` |
| `POST /v1/discounts` | `operational_discount.commit` | 201 `OperationalDiscountCommitResultView` |
| `POST /v1/cash-close/commit` | `cash_session.close` | 200 `CashCloseCommitResultView` |

Each intention supplies a UUIDv7 `Idempotency-Key`. Payment, operational discount
and close also supply the original intention's `cash_session_id`; opening has no
cash ID before it creates the session. The command key is independent of the
request attempt's `X-Request-ID`. Retries retain the original key, body, actor,
surface, workstation and applicable cash session. Current POS capability and
branch scope are revalidated: `pos.operate` for opening, payment and close;
`discounts.manage` for the operational discount.

Operational discounts are the existing operational inflow, not the commercial
price-discount engine assigned to ZM-FIN-072. CASH payments create an OUT cash
movement; CASH operational discounts create an IN cash movement. Existing CARD
records remain noncash records without a drawer movement or a new external
provider call. MIXED remains unsupported for these operational commands.

The snapshots preserve resource and cash movement identities, state and amounts.
They omit operator personal data, payee names, concepts, notes and mutable display
fields. Existing authenticated detail/current-session GETs retain their richer
contracts. Existing domain, audit and outbox data may still contain business
text; snapshot minimization does not claim that all existing records are free of
personal information.

Read-only recovery uses `GET /v1/{cash-sessions,payments,discounts,cash-close}/confirmations/{idempotency_key}`
with `workstation_code`, plus `cash_session_id` for every operation except opening.
Recovery does not reserve a key or execute an economic action. A missing or
uncommitted result remains uncertain and never authorizes an automatic new key.

## Atomicity and existing cash policy

The shared executor owns the transaction for the business effects, audit,
outbox and terminal response. Opening preserves the existing unique active
session constraints for user and workstation. It locks the actor and workstation
with the branch lock ordering retained. Zero opening fund is valid; an opening
does not fabricate a separate cash movement.

Payment, operational discount and close lock the exact `CashSession` row with
`FOR NO KEY UPDATE` and recheck its state after any wait. The opening actor and
workstation use the same non-key lock mode. These writes do not change referenced
keys, so this mode permits PostgreSQL's foreign-key `KEY SHARE` acquired during
identity reservation while still serializing competing economic writes. Tests
place both distinct-key reservations behind a barrier before either action
locks, covering the lock-upgrade cycle that an ordinary staggered race misses.
A new command cannot silently move to a later
shift. The completed replay path returns its historical snapshot without requiring
the historical shift to remain open. This block does not extend the same locking
protocol to every other economic command; that broader boundary remains 037.

Close retains mandatory explicit money counting and the existing `WITH_COUNT`
mode. `WITHOUT_COUNT` is invalid. A zero count is an explicit count, while an
empty bread counter does not waive the money count. The reconciliation formula,
existing class-capture resolution and physical close effects are preserved.
Preview is read-only and does not authorize a later stale commit; the new close
is recalculated under its shift lock.

A repeated close with the same key returns the saved close. A different key for
the already-closed shift produces durable `409 CASH_CLOSE_ALREADY_EXISTS`, with
no second close, business audit/outbox or session-revocation effect. The existing
database-triggered revocation of POS sessions bound to the closed cash session
remains in that transaction. Recovery after close therefore requires a new valid
login for the same authorized actor and original workstation; it does not require
opening a replacement shift.

## Browser and operator recovery

The browser stores only permitted intention metadata. Economic bodies remain
in memory; no payee, concept, notes, count breakdown, response snapshot or
authentication secret is stored in the recovery record. One live intention keeps
its key through retries, page transitions and competing tabs. After reload,
metadata permits lookup, not reconstruction or automatic resubmission of a body.
DEC-15 remains ONLINE_ONLY.

Confirm once. If the response is uncertain, use the recovery action before
creating another opening, movement or close. Retry only the same intention while
its original body remains in memory. After reload, query the result; an unresolved
result requires operational review, with no safe reset/reconciliation workflow
invented by this block. A detail, print or navigation failure after confirmation
does not reverse the financial effect. For an uncertain close, log in again and
query the original close before attempting another shift operation.

The operational-discount route remains hidden by the current release policy.
Its HTTP contract and adapter participate in this adoption, but authenticated
browser-origin API coverage is not evidence of a newly released discount UI.

## Acceptance checklist

| Criterion | Required observation |
|---|---|
| Four replay paths | Identical resource/movement IDs and saved amounts; one business effect, audit and outbox set |
| Identity conflicts | Changed payload, operation, actor, branch, workstation or cash context cannot reuse a key |
| Admission | Missing, duplicate or malformed keys and invalid input do not create business effects |
| Opening race | Same and distinct keys cannot bypass active user/workstation uniqueness; zero opening succeeds |
| Movement races | Duplicate keys yield one IN/OUT movement; different intentions remain distinct; locking against close preserves state |
| Close race | Same-key recovery and distinct-key durable conflict; one close and one revocation effect |
| Rollback | Failure after real business flush rolls back resource, cash effect, audit, outbox and identity together |
| Historical recovery | Lost committed response and fresh-login lookup recover the original context after closure |
| Authorization | Current capability, scope and actor/context checks apply to replay and GET recovery |
| Contract/privacy | Generated backend DTOs, replay headers and minimized snapshots; no handwritten shared wire types |
| Browser | Lost responses, reload, metadata-only recovery and tab/draft protection; no automatic replacement key |

## Existing callers and reproducible validation

Twenty-two existing API files contain 49 direct POST call sites: 28 opening,
7 payment, 7 operational discount and 7 close. Each supplies an explicit fresh
intention key. The latter three read an already-open cash session with
`testing.idempotency.current_cash_session_id`; the helper never opens a session
or patches TestClient. Existing no-open-session negatives remain before opening.
AST comparison confirms that other POST calls in these files are unchanged.
Rich detail assertions use authenticated GETs; post-close detail queries log in
again because close revokes the previous POS session.

Use the guarded PostgreSQL harness; no ordinary database is targeted. The
following commands reproduce dedicated acceptance and the existing caller suite.

```powershell
. .\.tmp\toolchain\activate.ps1
& .\scripts\dev\run-api-tests.ps1 -TestTarget @(
  'apps/api/tests/test_cash_idempotency.py',
  '--junitxml=.tmp/validation/cash-idempotency/acceptance.xml'
)
& .\scripts\dev\run-api-tests.ps1 -TestTarget @(
  'apps/api/tests/test_admin_cash_cuts.py',
  'apps/api/tests/test_admin_cash_flow.py',
  'apps/api/tests/test_admin_orders.py',
  'apps/api/tests/test_admin_reconciliation.py',
  'apps/api/tests/test_admin_returns_corrections.py',
  'apps/api/tests/test_admin_sales_tickets.py',
  'apps/api/tests/test_auth_session_lifecycle.py',
  'apps/api/tests/test_dev_audit_snapshot.py',
  'apps/api/tests/test_discounts_module.py',
  'apps/api/tests/test_orders_module.py',
  'apps/api/tests/test_order_idempotency.py',
  'apps/api/tests/test_payments_module.py',
  'apps/api/tests/test_phase_1a_pos_bootstrap.py',
  'apps/api/tests/test_phase_2a_pos_sales.py',
  'apps/api/tests/test_phase_3a_operations.py',
  'apps/api/tests/test_phase_4a_corrections.py',
  'apps/api/tests/test_phase_7a_cash_close.py',
  'apps/api/tests/test_phase_7b_cash_close.py',
  'apps/api/tests/test_returns_module.py',
  'apps/api/tests/test_return_idempotency.py',
  'apps/api/tests/test_sale_idempotency.py',
  'apps/api/tests/test_tickets_module.py',
  '--junitxml=.tmp/validation/cash-idempotency-callers/callers.xml'
)
uv run ruff check .
uv run mypy apps/api/src apps/worker/src
& .\scripts\dev\check-foundation.ps1 -Stage Contracts
& .\scripts\dev\check-foundation.ps1 -Stage Web
& .\scripts\dev\run-web-integration.ps1 -Surface All
uv run python scripts/dev/check-functional-operation-matrix.py --json
uv run pytest scripts/dev/tests/test_functional_operation_matrix.py -q
git diff --check
```

For shareable output, run the commands through
`Invoke-ZeroMermaProtectedValidationProcess` and publish text/JUnit through
`Protect-ZeroMermaValidationArtifacts` from
`scripts/powershell/ZeroMerma.ValidationArtifacts.ps1`. Raw captures are private
local diagnostics, not uploaded evidence.

## Execution evidence

| Check | Result |
|---|---|
| Caller AST preservation and Ruff | Passed for 49 call sites across 22 files |
| Existing caller regression suites | 280 cases: 274 passed and 6 fixture failures in 1553.668 s; no errors/skips. The captured run used the older fixtures described below; protected `.tmp/validation-published/cash-idempotency-callers/callers.xml` |
| Sale fixture regression | 3/3 passed in 22.97 s after selecting the sale identity by its own key; protected `.tmp/validation-published/cash-sale-regression/sale.xml` |
| Administrative fixture regression | 3/3 passed in 28.45 s after reading the acknowledgement's explicit cash session ID; protected `.tmp/validation-published/cash-admin-regression/admin.xml` |
| Dedicated PostgreSQL/HTTP acceptance | 68/68 passed in 310.97 s, zero failures/errors/skips; final source and fixtures loaded; disposable run `12e6a8fe4bfa4ee3a1fb67df271ae036`; protected `.tmp/validation-published/cash-idempotency/acceptance.xml` |
| Final concurrency and close regressions | 16/16 passed in 79.71 s, including four simultaneous-FK-reservation barriers, same-key contention, distinct opening/close keys, movement/close ordering, real class-count replay and negative-expected-cash rejection; protected `.tmp/validation-published/cash-concurrency/final.xml` |
| Static checks | API compileall and whole-repository Ruff passed; combined API/worker mypy passed for 339 source files; diff check passed |
| Foundation Contracts | 68 passed in 153.82 s; 248 OpenAPI operations, 249 registered API operations and 323 matrix entries; run `641cc630aa564f33b0338f4942d18baa` |
| Final matrix | Semantic validator and 28 specific tests passed after closing only GAP-0701/0708/0716/0741; protected `.tmp/validation-published/cash-matrix/matrix.xml` |
| Foundation Web | 587 unit tests (POS 332, Backoffice 231, API client 21, UI 3) and 11 mocked E2E passed; lint, typecheck and builds passed; run `6058ab2925814918bdc8fcc82ef3b0ac` |
| Real Browser | 13/13 passed (POS 6, Backoffice 7), protected wrapper exit 0; run `1983be2e23774d6a96b5d41535b68347` |
| Exact-commit Foundation CI | Required at delivery; no future run assumed |

The wide caller run exposed six stale fixture assumptions, not six accepted
failures. Three sale replay variants selected the only idempotency row in the
database; opening now creates its own row, so the assertion selects the sale's
exact key. Three cash-cut/reconciliation tests accessed the removed nested
`cash_session.id` acknowledgement field; they now use `cash_session_id`, retaining
their subsequent administrative detail and financial assertions. The sale
variants passed their three-case rerun, and the administrative cases passed a
separate three-case rerun. All six corrected cases therefore passed, across those
two executions; the original wide-run artifact remains a failed diagnostic.
The full exact-commit Foundation run repeats the complete suite after these
fixture corrections.

The real cash scenario in `apps/pos-web/e2e-real/aa-cash-command.spec.ts`
loses actual committed responses for opening, payment and close, then reloads
and retrieves the original snapshots. It also checks another tab's protection
and historical close recovery after the old POS cookie is revoked and a new
login succeeds. Operational-discount replay/recovery uses authenticated HTTP
from the browser; it does not exercise or release the hidden discount UI.
Results and sanitized network evidence are under
`.tmp/validation/web/1983be2e23774d6a96b5d41535b68347`.

The final PostgreSQL JUnit records five new CASH-payment samples and five replay
samples: median 164.684 ms for a new intention and 52.011 ms for replay. These
measurements include TestClient and disposable PostgreSQL on a shared local
development machine. They are observations for that payment path, not a
production SLA or a benchmark of all four commands.

## Remaining boundaries

No migration, reconciliation formula change, invented cash history, terminal
integration or new payment flow is introduced. Tasks 036–037 retain the broader
cash/inventory concurrency review; 043 retains ledger unification, 057/061 the
complete payment/cash verticals, and 065 external terminal integration. The
commercial-discount engine remains 072. Completing this adoption does not declare
the system ready for production or settle an unknown external financial result.

An existing operational CASH outflow can exceed available drawer cash. The
existing close constraint disallows negative expected cash; this adoption
retains a controlled validation rejection instead of exposing a server error.
It does not invent funds, alter the expected-cash formula or add a new capacity
policy. Preventing and resolving that insufficient-cash state remains part of
the financial/payment work outside this bounded idempotency adoption.
