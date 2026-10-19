# ZM-FIN-042 order payments in cash flow and close

Branch: `codex/zm-fin-042-order-cash-flow`.
Accepted base: `69f48aab1f8126bcffef2674e4b14dbd393a52fc` (ZM-FIN-041).

## Implementation and invariants

`orders/application/financial_services.py` admits one canonical operation and
confirmed actual-method entry for each newly recorded order payment. The causal
source is `ORDER_PAYMENT` and the payment UUID; the economic subject is `ORDER`
and the order UUID. Each fact carries the actual cashier, branch, workstation,
session and operation context. The same idempotent transaction owns the order,
payment, financial facts, audit, outbox and acknowledgement. There is no additional
commit or mirrored order `CashMovement`.

The scoped `financial_queries.py` joins confirmed entries to their causal payment
and order. It also follows explicit technical compensations back to that source.
POS summary/preview/close and Backoffice flow/cut consume this one order source.
Non-order flows continue using their existing sources until their assigned tasks;
the source sets are disjoint. CASH alone changes the expected drawer balance.
CARD is ACCOUNTING_ONLY, with the operator's payment record as the external
recording reference. It does not prove BBVA capture or bank settlement.

Order detail GETs expose financial IDs and actual session/workstation. Existing
030/032 command acknowledgement snapshots retain their shape and fingerprint.
OpenAPI and its generated TypeScript contract carry the new read fields. No new
public endpoint or database migration is required; Alembic head remains 0044.

POS fixes its cash-difference display to compare counted CASH with expected CASH,
excluding the CARD count. Backoffice identifies order advances, settlements,
refunds and technical compensations separately from sale revenue, with links
from each movement/cut to the actual order.

## Acceptance cases

| Evidence | Verification |
|---|---|
| `test_order_cash_flow.py::test_audited_missing_six_pesos_reconciles_to_527_in_pos_and_backoffice` | 500.00 opening + 21.00 real sale receipt + 6.00 order settlement = 527.00 expected; count 527.00, variance 0.00; one payment/operation/entry across replay; POS, flow, cut and cross-linked IDs agree. |
| `test_order_financial_entries.py` | Create/deliver/cancel × CASH/CARD/MIXED; operation context, source/subject, GET references, immutable replay/recovery; audit/outbox faults roll back every effect and permit retry with the same key. |
| `test_order_cash_flow.py` | Partial payment (3.00 advance + 3.00 later settlement), actual later collection/refund turn, previous close preserved, real-method breakdown, no synthetic Sale, five non-confirmed states excluded, confirmed technical compensation retained with its original, scoped reads exclude another branch. |
| `test_cash_concurrency.py` | Payment-versus-close in both commit orders, rollback releases close with no orphan financial facts, CARD has no drawer impact, two settlement intentions cannot collect one remaining balance twice. |
| `test_order_financial_entries.py::test_paid_order_without_open_cash_session_rejects_without_partial_facts` | Authenticated CASH/CARD/MIXED order attempts without an open session are rejected; no order/payment/financial fact, trace or idempotency reservation survives. |
| `test_admin_orders.py` | Paid orders can be delivered without another receipt; outstanding balance blocks Backoffice delivery and monetary cancellation. |
| POS/Backoffice browser and component tests | Cash-only variance, separate order amounts, actual flow/cut/order navigation, generated contract consumption. |

The first local reproduction attempt failed at its test setup: the selected bakery
class does not permit PRODUCT_DIRECT. The fixture was corrected to its supported
CLASS_CAPTURE mode with a real counter baseline. This setup failure is not claimed
as a reproduced missing-order defect. The audited arithmetic is an isolated
reconstruction of the reported 521-versus-527 omission, not a mutation of historical
audit records.

## Commands and evidence

Use the pinned toolchain and protected disposable-PostgreSQL harness. Focused runs
use `.tmp/run-040-validation.ps1 -Targets @(...) -Label '042-integration'`, a retained
wrapper around `Invoke-ZeroMermaIsolatedDatabase` and protected JUnit publication.
Source-controlled entry points remain `scripts/dev/run-api-tests.ps1` and
`scripts/dev/check-foundation.ps1`.

The broad local regression command was:

```powershell
. ./.tmp/toolchain/activate.ps1
./.tmp/run-040-validation.ps1 -Label '042-integration-final' -Targets @(
  'apps/api/tests/test_order_financial_entries.py',
  'apps/api/tests/test_order_cash_flow.py',
  'apps/api/tests/test_cash_concurrency.py',
  'apps/api/tests/test_orders_module.py',
  'apps/api/tests/test_admin_orders.py',
  'apps/api/tests/test_order_idempotency.py',
  'apps/api/tests/test_admin_cash_flow.py',
  'apps/api/tests/test_admin_cash_cuts.py',
  'apps/api/tests/test_phase_7a_cash_close.py',
  'apps/api/tests/test_phase_7b_cash_close.py'
)
```

Browser validation uses `scripts/dev/check-foundation.ps1 -Stage Browser` through
`Invoke-ZeroMermaProtectedValidationProcess`, preserving the canonical isolated
database, HTTPS runtime and sanitized artifact workflow.

Local validation results:

- `uv run --frozen ruff check .`: passed.
- `uv run --frozen mypy apps/api/src apps/worker/src`: passed, 368 source files.
- `scripts/dev/check-foundation.ps1 -Stage Contracts`: 101 passed in 110.96 seconds,
  run `dbffb4451d6c45b78c23a4f8fb14dee2`. All 257 OpenAPI operations have generated
  client coverage, with no orphan, unjustified raw request or manual-contract drift.
- Focused POS component/model tests: 28 distinct cases passed across cash-close
  screen/model, orders screen and order payment history. Backoffice component/API tests: 15 passed across
  cash flow, cash cuts and order details. Both apps pass typecheck, lint and build;
  the existing router React Refresh, Browserslist and bundle-size warnings remain.
- Final order producer run: 17 passed in 105.56 seconds, run
  `91625e9824c344808d2d3332a8921ae6`, including unsupported currency rejection with
  no partial facts. Command: `.tmp/run-040-validation.ps1 -Targets
  @('apps/api/tests/test_order_financial_entries.py') -Label '042-producer-final'`.
- Missing-session acceptance: 3 passed in 17.82 seconds, run
  `21348bcc84b8427880e3312e933b9893`, with the no-open-session producer test selected
  explicitly and label `042-no-session`.
- The 146-case PostgreSQL regression run `44e6b3bb4c96484a950a772421eb1dc2`
  passed 145 and failed one new test setup in 871.81 seconds: its read-scope binding
  omitted the required `mutation=False` argument. That fixture is corrected and the
  entire 13-case consumer file is rerun. The passing regression cases include order
  commands, idempotency, concurrency, flow, cuts and both cash-close phases. This is
  not represented as a fully green 146-case run.
- Corrected consumer rerun: all 13 passed in 85.35 seconds, run
  `c3081e3558334586a64809282f125082`. Command: `.tmp/run-040-validation.ps1 -Targets
  @('apps/api/tests/test_order_cash_flow.py') -Label '042-consumer-final'`.
  Together with the final producer and missing-session runs, all 150 distinct cases
  selected by the regression set plus the four later additions have passing evidence.
  The full immutable-commit suite is still required separately.
- Final Browser run: all 19 real scenarios passed (POS 8, Backoffice 11), Foundation
  run `1ede7b51110f4634a9c02947a93fff2c` and isolated runtime
  `635505573ab04f66a7ee5b0cc11247d9`. The Backoffice order scenario
  closes its dedicated session only after
  submitting explicit physical counts from the isolated fixture and obtaining a READY
  preview without blockers. It then verifies flow-to-cut-to-order navigation and the
  same financial identities. The POS scenario preserves lost-response recovery while
  checking a single cash delta and cash-only variance with a separate card count.

The first integration run was interrupted when the local Docker engine became
unavailable and has no completion result. A subsequent startup attempt
(`1ff125df6ff14e9890bf2f50e63c0a19`) failed before creating a database. Docker Desktop
was reopened and fresh guarded validation started; neither attempt is counted as
a passing run. The first Contracts attempt also detected stale OpenAPI digests in
the operation matrix; those were synchronized before the successful run above.

The first Browser run (`6a1cce330dfe4b0da7f0b12168ab68bd`) passed seven POS
scenarios and failed the new order-history interaction; Backoffice did not start.
The history was mounted in an unused detail surface instead of the live decision
panel. The integration now uses the active panel with scrollable content, and the
E2E checks both reference visibility and the delivery button after expansion.
The complete Browser harness is rerun after this correction.

The second Browser attempt (`3f5df163999a48f2831768bf9f1c4e7c`) reached the
history successfully but exposed a close-screen loading race: the right-panel
action was visible before its session bootstrap completed and ignored the click.
The panel now waits for authenticated bootstrap and an active session, covered by
a component regression. The real order scenario also waits for the ready heading
before entering close counts. This attempt is not counted as passing Browser evidence.

The third Browser run (`4979296069094d64ad62ce8300d370d2`) passed all eight POS
scenarios and ten of eleven Backoffice scenarios. The order navigation test selected
two valid "Abrir origen" links without identifying the document-origin section.
Its selectors are scoped to the actual detail section before the final full rerun;
this failed attempt is retained separately from the final acceptance result.

The final full Browser result above passes all scenarios after these corrections.

Integrated acceptance
requires the eight Foundation stages and `Foundation required` for the immutable
delivered SHA; the SHA and run URL accompany delivery. Edited-tree local evidence
does not replace that immutable-commit validation.

Review corrections include SQL subqueries for order method/refund cash-cut filters
(no Python materialization of historical session IDs), an explicit non-settlement
flag for accounting-only CARD, and domain rejection of unsupported payment currency
without partial order/financial facts. Existing unsigned user-count validation stays
separate from signed backend expected-cash display.

## Retained work and findings

- Existing cancellation eligibility uses its prior time-based cutoff and refunds
  through the original methods. Full approved cancellation policy, CASH_FIRST,
  partial refund obligations and provider execution remain 044/046 and the order
  workflow task. This task does not silently change those commercial rules.
- Order receipts do not become ordinary sales. Delivery is the approved recognition
  event, while revenue analytics and physical/order integration retain their tasks.
- General unresolved-obligation close blockers and full financial consumer adoption
  remain 045; current order commands synchronously record confirmed local/accounting
  effects. Diagnostic pending-state fixtures do not create an operational pending
  order payment workflow.
- The pre-existing Backoffice method net calculation subtracts operational discounts
  although their cash movement is IN. This unrelated operational-charge issue was
  identified in `admin_services.py::_get_payment_breakdown`; retain correction and
  reconciliation in 043/045. It is not counted as an order refund.
- No historical development payment is backfilled. Missing old financial links stay
  null; 047 owns classification, cutover and historical reconciliation under DEC-19.
- No operational database, persistent data volume or external terminal was modified.

See [the cash manual](../operations/order-payments-and-cash-close.md) for the
operator workflow and [the financial ADR](../architecture/financial-ledger.md)
for the broader adoption boundary. This task alone does not establish Production Ready.
