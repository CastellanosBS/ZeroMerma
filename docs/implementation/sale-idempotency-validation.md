# ZM-FIN-029 sale confirmation validation

Branch: `codex/zm-fin-029-sale-idempotency`.

The accepted foundation is commit `84517485047f9ff09bdcfcd9dc4afc0ede8c5d0d`.
Its green Foundation execution validates ZM-FIN-028, not this later adoption.
This record contains the commands and observed local results for ZM-FIN-029.
Integrated acceptance requires all eight Foundation stages and `Foundation
required` for the delivered adoption commit; its immutable SHA and run link
accompany delivery. No final CI result is claimed before that run completes.

## Scope and contract

The scope is POS sale confirmation, its generated API contract, the recovery
read and the existing sale consumers. It does not adopt orders, refunds, cash,
transfers, corrections or production commands. No new database migration is
required: the accepted 0042 store and transactional executor are reused.

`POST /v1/sales/confirm` requires a UUIDv7 `Idempotency-Key` header and an explicit
`cash_session_id`. Successful confirmation and replay return HTTP 201 with the
same `SaleConfirmationView`. That snapshot excludes operator email and full name;
`GET /v1/sales/{sale_id}` retains the authenticated display detail. Ticket identity
continues to derive from the sale ID.

`GET /v1/sales/confirmations/{idempotency_key}` accepts `workstation_code` and
`cash_session_id` to retrieve an already committed, authorized result. It creates
no business effect or reservation. A missing or unresolved result remains an
explicit HTTP 409; it must not be interpreted as permission to repeat the sale
with a new key. Both operations require the POS surface and `pos.operate` within
the actor's current scope.

## Acceptance evidence required

| Criterion | Observable evidence |
|---|---|
| Explicit admission | Missing, duplicate or invalid keys and invalid schemas fail before consuming an identity; an existing cash session is explicit in each admitted command |
| Sequential replay | Same HTTP result, sale ID, line/payment/movement IDs and snapshot; no additional business rows, audit or outbox |
| Concurrent replay | Concurrent HTTP retries return one sale; separate coordinated PostgreSQL command transactions exercise bounded same-key contention |
| Incompatible reuse | Changed payload, actor, operation or context returns 409 without another effect |
| Distinct intentions | Identical carts with different keys create distinct sales; PostgreSQL command tests isolate independent-key progress from the existing HTTP authentication locks |
| Pre-commit failure | Business effect, audit, outbox and idempotency identity all roll back; the original key remains retryable |
| Lost response | A committed result survives transport failure and is recovered without another sale |
| Historical context | Replay/recovery use the original cash session; a new intention still requires OPEN |
| Current authorization | Revocation and wrong actor/workstation/scope do not expose the stored result |
| Privacy | Confirmation snapshot and persisted response omit operator email/full name; no credentials or economic body in browser storage |
| POS lifecycle | Double submit, retry, reload and another tab preserve or recover the same intention; terminal outcomes permit the next intention |
| Contract integrity | Backend-generated header/body/response schemas and recovery operation match the generated TypeScript client and functional matrix |
| Performance | Measure new-command and replay paths with the environment and sample count stated; do not invent an SLA |

Business-effect counts cover `sales`, `sale_lines`, `sale_payments`,
`cash_movements`, the sale audit event and sale outbox event. Current confirmation
does not write canonical inventory movements. Showing that a replay does not add
inventory rows is not evidence that inventory integration has been implemented.

The existing authentication path takes user and auth-session row locks. Same-user
HTTP requests may serialize there. Four concurrent requests using the same cookie
can prove exactly one confirmed sale, but cannot demonstrate independent HTTP
throughput. Domain-level PostgreSQL concurrency tests retain real command scope
and transaction controls while bypassing that separate authentication lock.
Authentication-lock redesign is outside ZM-FIN-029.

## Existing callers and regression surface

Eleven existing API test files contain eighteen direct confirmation call sites.
They now choose a key explicitly per intention and obtain the existing open
cash-session ID through an authenticated read. The negative no-session case uses
an explicit nonexistent UUID. `testing/idempotency.py` generates UUIDv7 values;
it does not inject headers or modify arbitrary TestClient requests.

The regression files are `test_phase_2a_pos_sales.py`,
`test_phase_7a_cash_close.py`, `test_phase_7b_cash_close.py`,
`test_admin_cash_flow.py`, `test_admin_cash_cuts.py`,
`test_admin_reconciliation.py`, `test_admin_returns_corrections.py`,
`test_admin_sales_tickets.py`, `test_dev_audit_snapshot.py`,
`test_returns_module.py` and `test_tickets_module.py` under `apps/api/tests`.
The administrative ticket test obtains cashier display information from the
authenticated detail query instead of the minimized confirmation snapshot.

Dedicated adoption tests, POS unit tests, mocked browser tests and the real
HTTPS/API/PostgreSQL browser scenario must be identified separately. A mocked
response or a disabled submit button does not prove durable replay.

## Execution record

The caller update passed Ruff for the eleven test files and helper, and strict
mypy for the helper. Backend adoption and legacy caller regressions passed in
separate disposable PostgreSQL runs. Web unit, mocked browser and real
HTTPS/API/PostgreSQL browser acceptance also passed. The final integrated
generated-contract check and Foundation execution apply to the delivered commit.
The normal local database is not migrated, seeded, truncated or restored.

| Command | Observed result | Evidence |
|---|---|---|
| `uv run mypy apps/api/src/zeromerma_api/testing/idempotency.py` | PASS; one source file | Local command output |
| `uv run python scripts/dev/check-functional-operation-matrix.py` | PASS; 316 entries, 242 registered API routes, 241 OpenAPI operations; zero schema drift | Local command output; the final matrix classifies the executed sale adoption separately from later inventory and full POS work |
| `uv run pytest scripts/dev/tests/test_functional_operation_matrix.py --junitxml=.tmp/validation/sale-idempotency-callers/matrix.xml` | 28 passed in 123.93 s; no failures, errors or skips | JUnit at the specified ignored path |
| `uv run pytest scripts/dev/tests/test_api_contracts.py` | 24 passed in 17.61 s after declaring typed replay response headers | Local command output; final generated-inventory check follows matrix closure |
| `scripts/dev/run-api-tests.ps1 -TestTarget @('apps/api/tests/test_sale_idempotency.py', '--junitxml=.tmp/zm-fin-029-acceptance.xml')` | 26 passed in 160.38 s; no failures, errors or skips | Protected `.tmp/validation-published/sale-idempotency/acceptance.xml` |
| Canonical isolated caller regression, exact targets below | 47 passed in 320.00 s; no failures, errors or skips | Protected `.tmp/validation-published/sale-idempotency-callers/callers.xml`; protected output `.tmp/sale-legacy-callers.log`; database run `7d763019f6c04f8081dd71801c509a19` completed and cleaned up |
| `scripts/dev/check-foundation.ps1 -Stage Web` | PASS; 512 unit tests (POS 271, Backoffice 227, API client 11, UI 3), 11 mocked browser tests (POS 10, Backoffice 1), lint, typecheck and builds | `.tmp/validation/foundation/d891d8a675f345c2b556003890eae649/Web.json` and `Web.log` |
| `scripts/dev/run-web-integration.ps1 -Surface All` | PASS; 9 real browser cases (POS 3, Backoffice 6) over HTTPS, API and isolated PostgreSQL | `.tmp/validation/web/ec10ceb1ebf5474f8289ef8d13908b55/pos/results.json`, `backoffice/results.json` and protected `validation-output.log` |

These local runs use the working tree on the accepted base. Their manifests
therefore report `working_tree_clean: false`; the recorded base SHA does not
identify the uncommitted adoption changes. Final integrated acceptance is the
separate Foundation execution for the immutable delivered commit.

The real sale scenario loses an actual committed HTTP 201 response, reloads the
POS, retrieves the same snapshot through the recovery GET, clears a stale draft
in another tab and confirms that the next intention has a new key and sale ID.
Earlier browser attempts failed before sending a confirmation POST because the
background page did not have input focus; the final scenario explicitly focuses
the intended tab and amount field. No timeout increase or product bypass was
used to obtain the passing result. The final frontend typecheck also passed.

`GAP-0749` is closed by the executed PostgreSQL and real browser evidence. The
sale POST and POS route remain partial for the separate inventory, sale/close
and complete-workflow tasks. The functional matrix records the recovery GET as
implemented and directly verified without claiming those wider tasks complete.

The caller regression used this target list under the protected subprocess
wrapper from `scripts/powershell/ZeroMerma.ValidationArtifacts.ps1`:

```powershell
. .\.tmp\toolchain\activate.ps1
& .\scripts\dev\run-api-tests.ps1 -TestTarget @(
  'apps/api/tests/test_admin_cash_flow.py',
  'apps/api/tests/test_admin_cash_cuts.py',
  'apps/api/tests/test_admin_reconciliation.py',
  'apps/api/tests/test_admin_returns_corrections.py',
  'apps/api/tests/test_admin_sales_tickets.py',
  'apps/api/tests/test_dev_audit_snapshot.py',
  'apps/api/tests/test_phase_7a_cash_close.py',
  'apps/api/tests/test_phase_7b_cash_close.py',
  'apps/api/tests/test_returns_module.py',
  'apps/api/tests/test_tickets_module.py',
  '--junitxml=.tmp/validation/sale-idempotency-callers/callers.xml'
)
```

The earlier combined run passed the ten `test_phase_2a_pos_sales.py` cases and
the cold API startup case. It also exposed three adoption-test fixture issues:
an obsolete expected authorization status and concurrency fixtures that logged in
again and invalidated their earlier cookie. The final dedicated 26-case run uses
the corrected assertions and coordinated identities. That initial mixed result
is diagnostic evidence, not a passing combined run.

The acceptance suite verifies sequential snapshots and table counts, changed
intentions, malformed/missing keys, pre-admission errors, closed-session replay,
lost post-commit responses, rollback after real sale/outbox flushes, current
authorization, actor/workstation/cash-session mismatch, four same-cookie HTTP
requests and separate PostgreSQL command contention/independent-key progress.

The local TestClient plus Docker PostgreSQL measurement used five new-sale
requests and five replays. Median times were **239.855 ms** for new sales and
**60.583 ms** for replays on the shared Windows development environment. These
are observations for that sample, not an SLA or production capacity claim.

## Recovery and remaining boundaries

The POS persists only minimal recovery metadata. The request body remains in
memory; DEC-15's prohibition on a browser queue of pending economic mutations
still applies. A reload or transport failure cannot authorize a replacement
intention. Unknown outcomes remain blocked for backend recovery rather than
being displayed as a completed or safely failed sale.

Deployment of API and POS must be coordinated because the new header, explicit
cash-session field and response schema are required. No compatibility bypass for
old clients is introduced. Existing idempotency identities must survive recovery
with their corresponding business effects. Prefer roll-forward corrections;
do not remove records or restore only one side of the transaction history.

Sale-versus-close concurrency remains ZM-FIN-036; canonical inventory remains
049–050; the complete POS sale workflow remains 056. Worker execution, external
payment authorization, hardware effects and offline operation are outside 029.
This record does not declare Feature Complete or Production Ready.
