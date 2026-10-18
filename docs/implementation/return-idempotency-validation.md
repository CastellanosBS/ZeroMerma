# ZM-FIN-031 return command validation

Branch: `codex/zm-fin-031-return-idempotency`.

The accepted base is `e53ac6bd57865db0875a5d66bb1dd6e4da17fb7f`. Its Foundation
run validates the earlier order adoption, not this later return change. This
record captures the completed local implementation and validation. Integrated
delivery requires all eight Foundation stages and
`Foundation required` on the delivered commit; its immutable SHA and run link
accompany delivery without another source commit solely to insert the URL.

## Scope and preserved behavior

The adoption covers the existing POS command `POST /v1/returns/commit`, logical
operation `return.commit`. It creates one committed return, its lines, the
existing CASH refund movement, audit and outbox in the same transaction as its
durable idempotency result. Backoffice continues to query returns and related
financial documents; no new administrative refund command is introduced.

Every intention supplies a UUIDv7 `Idempotency-Key` and its return
`cash_session_id` explicitly. This is the cash session open when the return
intention starts; it can differ from the original sale's cash session.
Retries keep their key, payload, actor, surface,
workstation and cash context. `X-Request-ID` identifies a request attempt and
does not replace durable identity. Capability remains the canonical
`returns_corrections.manage` on POS; no capability alias or catalog migration is
introduced.

The command returns HTTP 201 with `ReturnCommitResultView`: return identity,
original sale and context identities, amounts, minimal lines and
`refund_cash_movement_id`. It omits operator personal information, notes and
dynamic audit/display data. Existing authenticated detail GETs remain the source
for those screen fields. The refund movement identity is carried explicitly in
the acknowledgement and audit/outbox evidence so equal partial refunds can be
linked without inferring identity from amount, sale or time.

Read-only recovery is
`GET /v1/returns/confirmations/{idempotency_key}?workstation_code=...&cash_session_id=...`.
It returns the saved acknowledgement only after current authorization and exact
actor/context checks. It neither reserves a key nor executes a return. A missing
or uncommitted result remains uncertain; it does not authorize another key.

The current behavior retained by this block includes confirmed original sales,
ordinary same-branch returns, a current authorized open cash session for a new
command, valid reasons, exact products for CLASS_CAPTURE lines, and existing
high-risk acknowledgement/review evidence. A replay must not create another
review event. Refund CASH remains permitted even when the original tender was
CARD or MIXED; the refund methods CARD/MIXED remain unsupported and rejected.

## Quantity, amount and transaction boundaries

Competing keys must not bypass entitlement. The original `Sale` row is locked
with `FOR UPDATE` after identity reservation. Committed quantities and amounts
across that sale's lines are recomputed under the sale-local lock.
The accumulated returned quantity cannot exceed the original sold quantity.
An excessive new intention conflicts with HTTP 409; invalid input remains
separate from a completed replay.

Refund allocation uses the original line's net amount and cumulative returned
quantity. The new delta accounts for amounts already refunded; the final partial
return absorbs the cent residual without exceeding the original net amount.
This fixes repeated per-request rounding for the existing snapshot. It does not
implement the complete future pricing/discount-allocation model of DEC-13 or
rewrite inconsistent historical refunds.

The executor owns commit/rollback. The return, refund movement, business audit,
outbox and terminal snapshot must survive or roll back together, including a
failure after their real flush. A completed fast path does not create documents,
recalculate the original refund or call an external provider. Historical cash
closure must not prevent authorized recovery of an already committed result.

The common authentication layer can serialize concurrent requests by one user or
session. Two HTTP clients sharing one authenticated session verify the visible
same-result behavior. Separate domain-level PostgreSQL tests exercise same-key
contention, competing distinct keys and the sale-row wait directly. Independence
is demonstrated for two sales in the same branch and cash session; this is not
a multi-branch or parallel HTTP throughput benchmark.

## Privacy and browser recovery

The browser retains only permitted recovery metadata. Request bodies remain in
memory; notes, returned-line payloads, customer/operator personal fields and
authentication material must not be persisted in the recovery record. After a
reload without a body, lookup is the available action; UNKNOWN never produces a
replacement intention automatically. A known initial rejection preserves the
editable draft, while confirmation clears it once.

The existing domain/detail records and v1 outbox payloads can contain free-text
notes. Minimizing the new acknowledgement and browser metadata does not claim
that all existing persisted records are free of PII. DEC-15 remains ONLINE_ONLY;
no queue of economic mutations is added.

## Operator procedure

Confirm the return once. If the result is uncertain, do not hand out another
refund or start a replacement intention. Use **Consultar resultado de la
devolución** to retrieve the existing result. **Reintentar la misma devolución**
is available only while the unchanged original body remains in memory; it keeps
the same identity and return context.

After a reload, only lookup is available. If the result remains unknown, stop
and request operational review. This block does not implement a safe manual
reset or reconciliation procedure that resolves UNKNOWN. A later detail or
printing failure does not reverse a confirmed return or authorize another refund.

## Acceptance checklist

| Criterion | Required observation |
|---|---|
| Partial and total replay | Original return and refund movement IDs and snapshot; no additional document, cash movement, audit or outbox effect |
| Identity separation | Changed sale, quantity, product, reason, disposition, actor or context cannot reuse a key for another effect |
| Admission | Missing/malformed/duplicate keys, invalid inputs and unsupported refund methods do not commit an identity or business effect |
| Quantity race | Different keys competing for the last returnable quantity produce one success and one conflict after recalculation |
| Cents and accumulated value | Fractional quantities and repeated partial refunds preserve original net value and allocate the final residual exactly |
| Atomic rollback | Injected failure after actual effects flush leaves no return, refund, business traces or terminal identity; retry can succeed |
| Lost committed response | Same-key POST or authenticated GET recovers the original acknowledgement without another refund |
| Authorization | Current capability, actor, branch, workstation and original cash context remain mandatory, including after session rotation/closure |
| Financial linkage | Equal partial refunds resolve their explicit cash movement identities in Backoffice; no amount/time heuristic |
| UI recovery | Real POS committed-response loss, reload and lookup; generated contracts, minimal persistence and no automatic replacement key |
| Boundaries | Unsupported external refunds do not claim completion; current absence of stock movements is recorded honestly |

## Existing callers and reproducible commands

Seven existing suites contain 17 direct return POST call sites and 27 tests.
Each call supplies an explicit fresh intention key and reads an already-open
cash session with `testing.idempotency.current_cash_session_id`. The helper does
not open a session or patch TestClient. Other commands in those files remain
unchanged. Personal/display assertions continue through authenticated detail
reads.

```powershell
. .\.tmp\toolchain\activate.ps1
& .\scripts\dev\run-api-tests.ps1 -TestTarget @(
  'apps/api/tests/test_returns_module.py',
  'apps/api/tests/test_tickets_module.py',
  'apps/api/tests/test_admin_sales_tickets.py',
  'apps/api/tests/test_admin_returns_corrections.py',
  'apps/api/tests/test_admin_cash_flow.py',
  'apps/api/tests/test_admin_cash_cuts.py',
  'apps/api/tests/test_admin_reconciliation.py',
  '--junitxml=.tmp/validation/return-idempotency-callers/callers.xml'
)
& .\scripts\dev\run-api-tests.ps1 -TestTarget @(
  'apps/api/tests/test_return_idempotency.py',
  '--junitxml=.tmp/validation/return-idempotency/acceptance.xml'
)
uv run ruff check .
uv run mypy apps/api/src apps/worker/src
uv run python scripts/dev/check-functional-operation-matrix.py --json
& .\scripts\dev\check-foundation.ps1 -Stage Contracts
& .\scripts\dev\check-foundation.ps1 -Stage Web
& .\scripts\dev\check-foundation.ps1 -Stage Browser
```

Capture database and Foundation commands through
`Invoke-ZeroMermaProtectedValidationProcess` in
`scripts/powershell/ZeroMerma.ValidationArtifacts.ps1`. Preserve the original exit
status and publish only protected evidence. Database tests use the disposable
PostgreSQL harness, never the usual development database.

## Execution record

| Validation | Observed result | Evidence |
|---|---|---|
| Existing caller static checks | PASS: Ruff and diff check; 17 return calls carry explicit context; all other POST expressions unchanged | Local source/AST comparison |
| Existing callers, 27 regressions | PASS: 27 tests, zero failures/errors/skips; 288.53 s | Protected `.tmp/return-legacy-callers.log` and `.tmp/validation-published/return-idempotency-callers/callers.xml`; disposable PostgreSQL run `99186980ee4f4b5c821293b04edb603e` completed with exit 0 |
| Dedicated PostgreSQL/HTTP acceptance | PASS: 49 tests, zero failures/errors/skips; 323.16 s | `.tmp/validation-published/return-idempotency/acceptance.xml`; disposable PostgreSQL run `6f60552066654533b17eeb9d98ccdf53` completed |
| Static Python checks | PASS: repository Ruff and strict mypy across 334 source files | `uv run ruff check .`; `uv run mypy apps/api/src apps/worker/src` |
| Functional matrix validator | PASS: 319 entries, 244 OpenAPI operations; runtime/tracked contract comparison has no drift | `uv run python scripts/dev/check-functional-operation-matrix.py --json`; canonical fingerprint `e9b4d48872fb7ca8510668b23bf376476a44bccd3f1acc74f7b2c0611e796784` |
| Foundation Contracts | PASS: 63 tests in 151.83 s; 244 operations, no generated/runtime contract drift or source writes | `.tmp/validation-published/foundation/8a3310ca707a484d8125b02f479bcdc7` |
| Focused frontend tests | PASS: 30 return tests in four files; fault-support 9 and Backoffice adapter 3 passed in separate focused runs | Model 12, intention 6, hook 6, screen 6; no combined single-run total claimed |
| Foundation Web | PASS: 556 unit tests (POS 306, Backoffice 231, client 16, UI 3), 11 mocked E2E (POS 10, Backoffice 1); lint, types and builds passed | `.tmp/validation/foundation/46abba1ec49847feb1c822d88afa171b/Web.json` and `Web.log` |
| Real browser flows | PASS: 12/12 (POS 5, Backoffice 7); new return case 16,449 ms | `.tmp/validation/web/e81c027b6e674215943ba5a43e2aacac/{pos,backoffice}/results.json`; `pos/5-sanitized-network.json` records the lost real POST 201 and recovery GET 200 |
| Exact-commit CI | Required for integrated delivery | Immutable SHA and run link accompany the completion report |

The new real POS case preserves the committed acknowledgement after response
loss, reload and read-only lookup, blocks another tab from repeating the refund,
and invalidates its stale draft after confirmation. It observes one return and
checks the exact refund movement identity and amount through an authenticated
Backoffice API request from the browser. That last assertion is not a new
Backoffice mutation or a complete Backoffice return-screen test.

Five new partial CASH refunds and five same-key replays were timed with TestClient
and local disposable PostgreSQL. The observed median was 221.804 ms for a new
command and 62.804 ms for replay. These measurements describe the shared local
validation environment; they are not a production SLA.

The matrix closes GAP-0745 for the current return command and records the recovery
endpoint as verified. The wider return module remains PARTIAL. GAP-0779 retains
complete POS workflow coverage under 063; GAP-0852 retains Backoffice route-level
coverage under 079, distinguishing indirect adapter/API evidence from a full UI
test. Inspection resolves stale GAP-0926 because the CLASS_CAPTURE product query
is already wired to the POS screen; its separate direct API test gap GAP-0299
remains open.

## Remaining scope

This block does not implement the CashSession-versus-close concurrency boundary
of 037, canonical financial integration and partial/external settlement in
044–046, or physical attribution/disposition in 050–051. The current return
command stores three disposition codes without producing InventoryMovement;
zero additional stock effects on replay must not be described as a completed
physical return implementation. QUARANTINE, NO_STOCK, split allocations and
causal entitlement-restoring compensations remain part of the later DEC-09 flow.

Authoritative cash capacity, CASH_FIRST partial settlement and Refund/RefundLeg
states are approved targets, not completed by deduplicating the current cash
movement. No bank reversal, provider result, external pending workflow or negative
cash correction is invented here. Full POS/Backoffice flows remain 063/079.

Tasks 047/055 own financial/inventory diagnosis, rebuild and legitimate opening
state or backfill. Demo/test data are never promoted into productive history;
old request IDs do not become fabricated idempotency records. There is no schema
migration in this adoption. Deploy API and clients together; retain durable
identities and restore business effects and their idempotency results together.
This record does not declare the whole returns module or production readiness.
