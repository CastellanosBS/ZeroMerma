# ZM-FIN-043-047 financial adoption and validation

Branch: `codex/zm-fin-043-047-financial-block`.
Accepted base: `0901d7f1b12b9910c59cf5c414f9e1fa9c6cf2a5` (042),
[Foundation run39238593880](https://github.com/CastellanosBS/ZeroMerma/actions/runs/39238593880).
That base run is not evidence for the changes in this block.

## Scope and status

| Task | Implemented result | Acceptance boundary |
|---|---|---|
|043|Opening, sales and operating payments/receipts write canonical operations and positive actual-method entries in their business transaction. No mirrored CashMovement.|Causal IDs, actual context, applied cash/change, replay and audit/outbox rollback have focused PostgreSQL evidence.|
|044|Refund obligation is distinct from payment. CASH_FIRST pays available canonical cash; the remaining obligation resumes in an authorized current turn. POS recovery and Backoffice expose actual paid/pending money.|No invented provider refund. Remaining commercial order lifecycle belongs to its own task. No generic manual technical-reversal endpoint.|
|045|POS and Backoffice cash equations use confirmed entries. Operating receipts add money. MIXED derives from distinct positive sale methods. CASH/CARD expected/count/variance freeze at close; missing CARD count differs from zero.|Unresolved admitted legs block their actual turn. An unassigned refund debt can continue later. Existing historical counts are not rewritten.|
|046|Durable provider admission, terminal binding, separate external-call/evidence transactions, timeout/query recovery and authenticated evidence interface.|**PARTIAL.** Injected fake only; no actual BBVA adapter, integrated business producer/UI, hardware/PCI approval, VOID or bank-settlement reconciliation. FINAL_PILOT_START remains POSTPONED.|
|047|Read-only diagnosis/dry-run and evidence-gated, row-idempotent import for supported real sources/opening state, with immutable manifests and before/after amounts/hashes.|No demo/test promotion, real-source import, productive reconciliation signature or production restore is claimed. Ambiguous sources and closed historical turns remain manual.|

## Files and contracts

Financial recording, refunds, session queries, classification and reconciliation
live in `financial_ledger`. External provider ownership lives in `payment_terminal`.
Existing sales, cash, orders, returns, operating payments/charges, reports and
ticket readers adopt these sources. POS adds durable refund intention/recovery
and actual-method close display; Backoffice shows settled/pending refunds and
canonical cut references. Source documents retain their commercial receipt facts.

Alembic adds one chain:0045 refund obligations/order-entry link,0046 nullable count
and signed CARD expectation/count,0047 terminal intentions/evidence,0048 import evidence.
Migrations do not backfill or mutate operational history. Downgrade refuses to
erase admitted economic evidence or force missing/signed counts into old fields.
Complete verified restore or a reviewed roll-forward is required when applicable.

OpenAPI and TypeScript are generated from the backend:266 unique documented
operations,267 registered including one hidden framework route. Four refund routes
and five terminal routes are explicit in the access and functional matrices.
Existing immutable acknowledgement identities remain recoverable; new read DTOs
expose actual financial references. Transaction ownership includes provider TX1/TX2
and the existing idempotent executor for business posting/import rows.

## Focused acceptance evidence

All PostgreSQL runs use disposable loopback databases with unique run IDs and
protected output. No normal local/operational database was opened for mutation.
The following local results precede integrated acceptance; they do not substitute
for the exact delivered commit's Foundation checks.

| Cases | Result and protected evidence |
|---|---|
|043 producer replay, zero opening, CASH/CARD/MIXED, applied cash and rollback|24/24; `operation-context/043-producers/81c288df3dad46acb698350be51ab213/operation-context.xml`.|
|044 settlement, later turn, concurrent intentions, rollback, source methods, reserved UNKNOWN budget, missing opening, authority and BO metrics|10/10; `operation-context/refunds044-canonical/b95e34784b4f4b90bc63dd14eee87696/operation-context.xml`.|
|044 two operators/drawers contending on one obligation|1/1; run `57385ee723964c42850c924738c45aa5`; real `pg_blocking_pids` contention, one permitted settlement.|
|044 related-document aggregation by actual turn|2/2; `operation-context/refund-related-documents/8f217c186b3d4298b7694a63b7ac6384/operation-context.xml`. Multiple deliveries retain separate entry details and one document with the turn's total and last delivery time.|
|045 actual-method equations, CARD count null/zero/complete, mandatory CASH, three components/same-method/zero-applied-cash classification|7/7; `operation-context/canonical-close-seven/1d30ea1b0b3c472baa19b02d3f048e7a/operation-context.xml`.|
|045 canonical close plus complete phase7a/7b regression, including exact cent compensation|18/18; `operation-context/canonical-close-regression-final/8e6c48a8bd604b76b1be17c5277477f4/operation-context.xml`.|
|046 HTTP/provider boundary|23/23 first run `payment-terminal/d1afca508b3544fba0e62a4bebb477dc/acceptance.xml`; final changed-path group6/6 at `payment-terminal/4829a9c99b4b42a29bcd4fea4d8d10d6/acceptance.xml`, including fresh authority after provider contact.24 distinct PostgreSQL cases total,20 domain cases.|
|046 first-send approval revocation and recovery|7/7; `payment-terminal/0f2b1ebb13324bf09338607faae22d17/acceptance.xml`. Five additional cases reject deactivated/changed approvals before execute while preserving query-only recovery of an already sent identity;29 distinct PostgreSQL cases in the final module.|
|047 diagnosis/import/immutable evidence/rollback/replay/source scope/opening|15/15; `operation-context/047-reconciliation/e2d4fa9f61d64ca1a89a6a3846f8f043/operation-context.xml`; additional concurrent manifest case1/1 at `047-import-concurrency/6f17437809f24c078aecef609e5387e9`;16 pure manifest/Decimal cases.|
|045 signed CARD count and nonnegative CASH|5/5 PostgreSQL cases, run `d8823fc636024c76af2950275e383ffb`; POS model/components26/26, including negative cents and missing count versus zero.|
|POS refund components/intention/recovery|14/14, including global GET recovery after reload without an open drawer; Backoffice refund components7/7.|
|Cash concurrency|36/36; `concurrency/c4430fc77e7342ffadfbd9be5b4b1854`, preserving real database contention and rollback assertions.|
|Sale and cash idempotency|28/28; `operation-context/financial-idempotency-regressions/fa1d9929c97143449632ddf9fac78bb3/operation-context.xml`.|
|Order CASH/CARD/MIXED settlement and cancellation replay|3/3; `financial-unexplored-tests/103839d4cb33478598d35fda3d3d7063/result.xml`, including canonical ledger snapshots and exact CASH_FIRST receipt links.|
|Migration evidence preservation|9/9 final focused cases; `migration-review/39ed9d3d222544f28efffc620e002827`, including fresh metadata parity and eight guarded downgrade cases.|
|Backend unit suite|267/267 in the integrated source check; exact-commit Foundation acceptance remains required.|

Integrated local stages passed: Web (`a52829f1ffe945dc9eb8ef57dfcd66b3`),
Contracts (`97d3ba9345734d079f01868236c428d3`,101 cases), Migrations
(`12d18837bc8a4cfbbf225a06949b3dd9`,17 cases before the additional guards),
and Browser (`475c7a7301844d34b8d5a08b56518f13`,19 real Chromium cases).
The last browser run includes the signed-count and refund recovery changes;
earlier stage results are supplemented by the focused checks above. Generated
contracts cover266 operations with no orphan client operations. Ruff and mypy
pass for all387 backend/worker source files after final contract generation.

The first broad financial regression reported31/92 failures from previous storage,
counting and refund expectations. They are retained as diagnostic evidence and
updated to assert canonical identities and policy without removing concurrency,
rollback or business invariants. First migration validation also exposed old head
and schema-check fixtures. Failed attempts are not presented as acceptance.

## Reproduction and integrated acceptance

Use the pinned toolchain. Canonical repository entry points are:

```powershell
./scripts/dev/run-api-tests.ps1 -TestTarget @(
  'apps/api/tests/test_financial_producers.py',
  'apps/api/tests/test_refund_financial_ledger.py',
  'apps/api/tests/test_canonical_financial_close.py',
  'apps/api/tests/test_payment_terminal.py',
  'apps/api/tests/test_financial_reconciliation.py'
)
uv run --frozen ruff check .
uv run --frozen mypy apps/api/src apps/worker/src
uv run --frozen pytest apps/api/unit_tests
uv run --frozen python scripts/dev/api-contracts.py check
uv run --frozen python scripts/dev/check-functional-operation-matrix.py
./scripts/dev/check-foundation.ps1 -Stage Migrations
./scripts/dev/check-foundation.ps1 -Stage Web
./scripts/dev/check-foundation.ps1 -Stage Browser
```

The retained local `.tmp/run-040-validation.ps1` wrapper adds protected JUnit and
run metadata around the same isolated PostgreSQL harness. Evidence paths above
are relative to `.tmp/validation-published`. Final delivery requires all eight
Foundation stages plus the required aggregate for one immutable clean commit;
the delivered SHA, run link and artifact verification accompany the final report.

## Operational references and remaining risks

- [Canonical cash close](../operations/canonical-cash-close.md)
- [Refund settlement](../operations/refund-settlement.md)
- [Terminal boundary and remaining BBVA gate](../operations/payment-terminal-boundary.md)
- [Financial diagnosis/import/restore](../operations/financial-reconciliation.md)

No hardware, real provider sandbox or actual opening state was supplied for this
block. The terminal model/integration contract is still requested from the owner.
Database, browser and fake-provider success must not be described as BBVA
certification, production readiness or completion of the remaining project.
