# ZM-FIN-030 order command validation

Branch: `codex/zm-fin-030-order-idempotency`.

The accepted base is `e1678b3b8b036e274f1dceea5bed2c53baab559a`, whose
Foundation execution validates the previous sale adoption. It does not validate
this later order change. This record documents the executed local validation of
the order adoption. Integrated acceptance requires all eight Foundation stages and
`Foundation required` for the delivered commit; its immutable SHA and run link
will accompany delivery without a later source change solely to insert the URL.

## Scope and command composition

The adoption covers seven existing HTTP mutations and their current payment
composition. It does not introduce an independent payment flow or migration.

| Surface | Command | Existing effects covered by the same intention |
|---|---|---|
| POS | `POST /v1/orders` | Create order and items, plus any initial `ADVANCE` payment legs |
| POS | `POST /v1/orders/{order_id}/mark-ready` | `PENDING` to `READY` |
| POS | `POST /v1/orders/{order_id}/deliver` | Final `SETTLEMENT` legs, if due, and `READY` to `DELIVERED` |
| POS | `POST /v1/orders/{order_id}/cancel` | Applicable `REFUND` legs and transition to `CANCELED` |
| Backoffice | `POST /v1/admin/orders/{order_id}/mark-ready` | `PENDING` to `READY` |
| Backoffice | `POST /v1/admin/orders/{order_id}/deliver` | Delivery only when no settlement remains; financial capture stays in POS |
| Backoffice | `POST /v1/admin/orders/{order_id}/cancel` | Cancellation only when no refund must be captured; financial capture stays in POS |

Every new command receives its own UUIDv7 `Idempotency-Key`. A retry keeps that
key, operation, actor, surface, context and canonical payload. An incompatible
reuse returns 409 without a new effect. `X-Request-ID` remains separate attempt
correlation. The old optional `AdminOrderActionRequest.idempotency_key` body
field is removed rather than accepted as a compatibility alias.

All four POS request models require the original `cash_session_id` explicitly.
The command result is `OrderCommandResultView`, containing order identity,
state, amounts and payment identities, without customer or operator personal
data, notes, cancellation free text or dynamic available actions. Authenticated
detail GETs retain the display information needed by existing screens.

Read-only recovery uses
`GET /v1/orders/commands/{command_code}/{idempotency_key}` with
`workstation_code` and `cash_session_id`, or the Backoffice equivalent
`GET /v1/admin/orders/commands/{command_code}/{idempotency_key}` with `branch_id`.
The codes are `create`, `mark-ready`, `deliver` and `cancel`; Backoffice has no
create command. Recovery neither reserves a key nor executes the action. Missing
or uncommitted results remain explicit uncertainty, never permission to submit
the economic operation with a replacement key.

## Transaction, state and privacy boundaries

The executor owns the root transaction for the idempotency result, order/items,
payment legs, audit and outbox. Order actions must not independently commit.
Existing order transitions take the `CustomerOrder` row lock before validating
state or payment balance, including POS-versus-Backoffice races. Different keys
do not bypass domain transition constraints; unrelated orders must not share a
global order lock. Replays use the saved result, not the order's later state.

The implemented state subset remains `PENDING`, `READY`, `DELIVERED` and
`CANCELED`. A new invalid transition conflicts; a completed retry returns its
original acknowledgement even after later authorized transitions. Current
authorization and exact context remain mandatory for replay and recovery; a key
is not a credential. Historical cash closure does not erase a committed result.

The browser may retain minimal recovery metadata. The request body stays in
memory, and DEC-15 forbids persistent queues of pending economic mutations.
Customer names, telephone numbers, notes, payment bodies and authentication
material must not be copied into recovery metadata or persisted replay snapshots.
Server-side domain records and authenticated detail queries remain separate from
the minimized replay result. Existing v1 order audit/outbox payloads retain their
historical personal fields. This change minimizes the new replay snapshot and
browser recovery metadata; it does not claim that every domain, audit or outbox
record is free of PII.

## Required acceptance evidence

| Criterion | Required observation |
|---|---|
| Seven mutations | Sequential replay of every POS/Backoffice command returns its original result and status without another effect |
| Identity separation | Separate command keys; changed payload, order, actor, surface, branch, station or cash session conflicts without mutation |
| Admission | Missing, duplicate or malformed keys and request validation failures do not consume an identity |
| Payments | Initial advance, final settlement and cancellation refund legs appear once; repeated delivery/cancellation cannot double-charge or refund |
| State | Same-key replay after a later transition returns the original snapshot; incompatible new transitions return conflict |
| Concurrency | Same-key contention is bounded; different-key competing delivery/cancellation and cross-surface transitions leave one valid outcome |
| Independent work | Two separate orders in the same branch can progress without an operation-wide lock; the focused case does not establish cross-branch throughput |
| Atomic failure | Failure after real order/payment/audit/outbox flush rolls everything back; retry with the original key succeeds |
| Lost response | Actual committed result can be recovered after transport failure without creating another order/payment/transition |
| Authorization | Current capability/scope, actor and original context protect saved results, including after session rotation and cash closure |
| Privacy | Acknowledgements and stored replay payloads omit PII; browser persistence contains only permitted recovery metadata |
| UI | POS and Backoffice preserve an intention across retry/unknown outcomes and recover through the backend; both use generated contracts |
| Contracts | Required header, explicit cash context, acknowledgement and recovery operations agree with OpenAPI, generated TypeScript and the matrix |
| Performance | State sample count/environment and compare new-command versus replay overhead without inventing an SLA |

The existing authentication layer locks user/auth-session rows. Same-user HTTP
requests can serialize before reaching the order coordinator. HTTP tests prove
client-visible results; separate real PostgreSQL command tests are needed to
exercise domain contention and independent-order progress without attributing
authentication serialization to the idempotency mechanism.

## Existing callers and validation commands

The existing regression suites contain 24 direct order POST call sites:
17 in `apps/api/tests/test_orders_module.py` and seven in
`apps/api/tests/test_admin_orders.py`. Each now supplies its own explicit key.
POS callers read an already-open cash session using
`testing.idempotency.current_cash_session_id`; no TestClient patch injects keys
or silently creates context. Tests needing personal fields or UI flags use an
authenticated detail GET after the safe acknowledgement.

The focused regression command is:

```powershell
. .\.tmp\toolchain\activate.ps1
& .\scripts\dev\run-api-tests.ps1 -TestTarget @(
  'apps/api/tests/test_orders_module.py',
  'apps/api/tests/test_admin_orders.py',
  '--junitxml=.tmp/validation/order-idempotency-callers/callers.xml'
)
```

Run it through `Invoke-ZeroMermaProtectedValidationProcess` from
`scripts/powershell/ZeroMerma.ValidationArtifacts.ps1`, preserving the original
exit status and publishing only protected evidence. The dedicated acceptance
suite is `apps/api/tests/test_order_idempotency.py`, kept separate from these
legacy consumer regressions.

The remaining canonical validation commands are:

```powershell
. .\.tmp\toolchain\activate.ps1
& .\scripts\dev\run-api-tests.ps1 -TestTarget @(
  'apps/api/tests/test_order_idempotency.py',
  '--junitxml=.tmp/validation/order-idempotency/acceptance.xml'
)
uv run ruff check .
uv run mypy apps/api/src apps/worker/src
uv run pytest scripts/dev/tests/test_foundation_gates.py scripts/dev/tests/test_validation_artifacts.py -q
& .\scripts\dev\check-foundation.ps1 -Stage Web
& .\scripts\dev\check-foundation.ps1 -Stage Browser
& .\scripts\dev\check-foundation.ps1 -Stage Contracts
```

Use the same protected process wrapper for captured acceptance and Foundation
output. The direct negative-gate pytest command is a test selection, not an
execution of the full `-Stage Negative` runner. Each Foundation stage also
remains separately reproducible through the canonical runner.

Browser-intention tests are explicit in
`packages/api-client/src/command-intention.test.ts`,
`apps/pos-web/src/features/orders/order-command-intent.test.ts` and
`apps/backoffice-web/src/features/admin/orders/order-command-intent.test.ts`.
The POS `use-order-intention.test.tsx` cases verify draft retention after a known
first rejection, preservation of unresolved identities and one-time cleanup after
confirmation. A reload without the request body permits only result lookup;
`UNKNOWN` never automatically creates a replacement key.
The two `e2e-real/zz-order-command.spec.ts` files exercise lost committed replies:
POS creation with an advance, reload/recovery and a separate mark-ready key;
Backoffice mark-ready, reload and recovery. Their execution status is recorded
below rather than inferred from the presence of the files.

Contract validation follows final API and consumer stabilization:
`pnpm contracts:generate`, matrix fingerprint/semantic synchronization,
`uv run python scripts/dev/check-functional-operation-matrix.py`, then
`scripts/dev/check-foundation.ps1 -Stage Contracts`. The corresponding Backend,
Web and Browser stages validate the integrated Python and both frontend paths;
final CI runs all eight stages on the exact committed checkout. Every database
test uses the isolated harness, never the normal local database.

## Execution record

| Validation | Observed result | Evidence |
|---|---|---|
| Ruff for the two caller files and existing idempotency fixture helper | PASS | Local command output |
| Existing order callers | PASS: 16 tests, zero failures/errors/skips; 103.30 s | Protected `.tmp/order-legacy-callers.log` and `.tmp/validation-published/order-idempotency-callers/callers.xml`; isolated database run `2910257a6a1942879666af1f9fcadfc1` completed and cleaned up |
| Dedicated PostgreSQL/HTTP acceptance | PASS: 49 tests, zero failures/errors/skips; 359.64 s | `.tmp/validation-published/order-idempotency/acceptance.xml`; isolated database run `8f1ef380a9f445b698c63fc1a52c1657` completed and cleaned up |
| Static Python checks | PASS: repository Ruff and strict mypy across 333 source files | `uv run ruff check .`; `uv run mypy apps/api/src apps/worker/src` |
| Negative-gate tests | PASS: 15 tests | `uv run pytest scripts/dev/tests/test_foundation_gates.py scripts/dev/tests/test_validation_artifacts.py -q` |
| Focused contract tests | PASS: 33 tests, including nine order-specific cases | Focused contract execution, also covered by the Foundation Contracts stage |
| Functional matrix validator | PASS: 318 entries, 243 OpenAPI operations, no invalid test references or undefined targets | `uv run python scripts/dev/check-functional-operation-matrix.py --json`; runtime/tracked canonical fingerprint `d681077af541396bd3cacb92b859d0d386ddad104085576dc8633e9a67fd3072` |
| Foundation Contracts | PASS: 61 tests in 102.70 s; generated/runtime contracts have no drift | `.tmp/validation-published/foundation/07841b603c444a6a8f451517dec153f8` |
| Foundation Web | PASS: 533 unit tests (POS 283, Backoffice 231, client 16, UI 3), 11 mocked E2E (POS 10, Backoffice 1); lint, typecheck and builds passed | `.tmp/validation/foundation/78b816ab3df145b9823439f846506052/Web.json` and `Web.log` |
| Real browser flows | PASS: 11/11 (POS 4, Backoffice 7), including both new order recovery flows | `.tmp/validation/web/3b6d648bc88146bfb6f70441564fda25/{pos,backoffice}/results.json`; `pos/4-sanitized-network.json` and `backoffice/7-sanitized-network.json` |
| Exact-commit CI | Required for integrated delivery | Immutable SHA and Foundation run link accompany the completion report; local results do not substitute for that execution |

The acceptance run measured five new creations and five same-key replays using
TestClient and local disposable PostgreSQL: median 255.299 ms for a new command
and 93.409 ms for replay. These are observations on a shared local environment,
not a production SLA or parallel HTTP throughput claim. Its independent-order
case covers two orders in the same branch. Three simultaneous HTTP retries share
one authenticated session; separate domain-level PostgreSQL cases exercise
same-key contention and order-row races across POS and Backoffice.

## Remaining scope and known differences

`CustomerOrderPayment` still does not create the canonical `CashMovement`
consumed by cash-flow/cut reconciliation. Integrating those financial effects is
ZM-FIN-042. Exactly-once existing payment rows do not prove that ledger gap fixed.

The existing order implementation also differs from the complete approved
DEC-10 target: it does not yet enforce the mandatory 50% initial advance,
`PRODUCTION_COMMITTED` cancellation boundary, canonical inventory reservations,
subsequent independent advances, amendments, `EXPIRED` or `NO_SHOW`. The existing
refund cutoff is not presented as the approved final cancellation policy. These
business-flow changes belong to their later tasks, including 058 and 078, and are
not silently folded into an idempotency change. DEC-11 payment redesign, external
providers, production and customer communications are likewise outside 030.

The task's historical downstream reference to 062 does not authorize transfer
work: the current 062 title is POS transfers/receipts. The concrete dependencies
and unchanged acceptance requirements of those tasks remain authoritative.

Deployment must update API, POS and Backoffice together. Do not delete durable
identities or manufacture records from old request IDs. Restore business effects
and idempotency records consistently; prefer roll-forward fixes. This record
does not declare the complete order module, Feature Complete or Production Ready.
