# ZM-FIN-041 financial-ledger foundation validation

Status: implemented, with local validation passed. This record contains executed
evidence; immutable-commit delivery acceptance follows the rule below.
The [financial-ledger ADR and dictionary](../architecture/financial-ledger.md)
defines the scope and numerical cases derived from approved business decisions.

## Scope being accepted

Two canonical tables represent immutable operation admission/obligation and actual
method entries. Confirmed entries are the ledger; no duplicate posting table is
introduced. The foundation is inactive: no sales, orders, returns, cash commands,
reports or cash-close consumer is switched in 041. No backfill is executed.

The task does not claim the operational order-payment omission is resolved, real
provider capture is integrated, CASH_FIRST refunds are exposed end to end, or
legacy totals have been reconciled. Those are assigned to 042-047.

## Acceptance evidence

| Criterion | Required evidence | Result |
|---|---|---|
| Money and dictionary | Decimal/0.01/HALF_UP cases, non-finite/invalid amount rejection, same-currency enforcement and explicit sign/cause catalogue | Domain and PostgreSQL suites passed |
| Actual method composition | CASH change, multiple CASH legs, MIXED derived from real distinct methods; no MIXED persisted and no extra change posting | Domain and PostgreSQL suites passed |
| Obligation and state | Partial/unassigned refund remainder, pending/PROCESSING/UNKNOWN excluded from completed totals; derived state and explicit rejection | Domain and PostgreSQL suites passed |
| Immutable evidence | Admission identity and terminal-entry mutation rejected; entry deletion rejected; exact unique compensation preserves originals and does not masquerade as business refund | Domain and PostgreSQL suites passed |
| Causal bounds | Unique effect/leg identities, no allocation above due, refund tied to the economic subject with optional original-operation anchor and different actual method permitted | PostgreSQL allocation contention and causal checks passed |
| Session projection | Actual entry session may differ from original admission; totals use actual session and confirmed CASH; no original close rewrite | Domain and PostgreSQL projection checks passed; operational adoption remains outside 041 |
| Authorized reads | Internal query refreshes current authority and requires bound cash_finance.view and branch permission; one fact-graph statement snapshot, no flush/commit or legacy fallback; no endpoint enabled | Scope checks and external-revocation regression passed |
| Opening state | Zero cash opening without an entry; RECEIVABLE/PAYABLE/CUSTOMER_ADVANCE without drawer entries; explicit evidence and no demo backfill | Domain, PostgreSQL and migration checks passed |
| Isolation of 041 | New tables empty after upgrade/bootstrap; operational producers and existing consumers unchanged; no new endpoint or handwritten shared wire type | Migration preservation and contract checks passed |
| Migration | Empty-to-head, supported checkpoints, model/schema parity, 0043 transition preservation, downgrade guard and complete-database dump/restore | Full migration suite passed: 17 cases and 44 supported checkpoints |
| Static/contracts | Ruff, strict mypy, applicable model/domain tests, contract drift and inventory checks | Global Ruff, strict mypy 366 files and Foundation Contracts passed |

Counts below identify their actual executions. The final PostgreSQL coverage is
61 distinct cases across a 58-case run and three additional regressions; it is
not presented as one fictional 61-case execution.

## Executed checks

| Check | Result | Protected evidence |
|---|---|---|
| Domain rules and numerical projections: `apps/api/unit_tests/test_financial_ledger_domain.py` | 58 passed in 0.281 s; zero failures/errors/skips | `.tmp/validation-published/financial-ledger-domain/financial-ledger-domain.xml` |
| Final PostgreSQL storage plus complete migration suite | 75 passed: 58 storage/projection cases + 17 migration cases, in 286.96 s; zero failures/errors/skips | `.tmp/validation-published/operation-context/financial-ledger-final/23af56180f9b4260b690226ff750776a/operation-context.xml` |
| Final external revocation and transaction-isolation regressions | 3 passed in 10.134 s; zero failures/errors/skips | `.tmp/validation-published/operation-context/financial-ledger-isolation-revocation/422b6ff920b0451caf1176ba8bc31432/operation-context.xml` |
| Strengthened populated-ledger dump/restore | 1 passed in 6.17 s; zero failures/errors/skips; rerun of an existing migration case, not an additional distinct case | `.tmp/validation-published/operation-context/financial-ledger-restore-facts/d59b2846c5c145f682ae84840278c8f6/operation-context.xml` |
| Final repository static checks | Global Ruff passed; strict mypy passed for 366 API/worker source files; `git diff --check` passed | Coordinating validation on the frozen final runtime |
| Foundation Contracts | 101 passed in 114.164 s; zero failures/errors/skips; contract generation check and functional matrix passed | `.tmp/validation-published/foundation/815542c563d841358dc2bf23ee04fbc9` |

The domain suite covers strict money/currency, explicit HALF_UP rounding, CASH
change, derived MIXED, unresolved CARD, refund allocation/remainder, opening
obligations, exact compensation, actual-session order receipts and operation
directions. It also verifies Decimal results under a reduced ambient precision.
That case exposed a context-sensitive absolute-value check; the final money
implementation uses an exact magnitude check and a local calculation context.
Four final admission cases also reject a technical reversal with a missing,
foreign-parent, unconfirmed or amount-mismatched original before a compensating
leg exists. They passed against the corrected implementation; this record does
not claim a prior failing execution of those four cases. Four summary cases reject
incompatible compensation pairs; another preserves UNKNOWN as the visible state
while a different entry is partially reversed.

These checks validate pure rules and representations. They do not implement the
ADR's future cancellation/amendment, provider-fee or operational cutover examples.

Migration acceptance verifies the fresh 44-revision chain, 225 exact check
fingerprints, upgrade from 0043 with all prior table data preserved, empty-table
downgrade, rejection of downgrade with financial evidence and complete-database
dump/restore. Entry-write tests verify READ COMMITTED allocation serialization;
REPEATABLE READ and SERIALIZABLE are rejected rather than silently accepting an
unverified budget snapshot. No operational database or persistent volume was used.

The final restore rerun strengthens `test_dump_restore_sanity` with one admitted
operation and one CONFIRMED entry. It compares their complete row JSON after
restore and proves the restored immutability triggers reject UPDATE. The migration
count remains 17 distinct cases; this final rerun is recorded separately from the
earlier combined execution. The 0043-to-0044 transition preserves hashes for all
81 pre-existing tables.

## Validation workflow

Use the pinned toolchain documented in README. Database validation uses the
canonical isolated-database harness exposed by `scripts/dev/run-api-tests.ps1`
and `scripts/dev/run-migration-validation.ps1`. Console output and JUnit publication
use the protected validation helpers. Do not target the normal Compose database,
staging, production or a persistent operational volume.

Focused domain and database checks use these targets:

```powershell
uv run pytest apps/api/unit_tests/test_financial_ledger_domain.py -q
.\scripts\dev\run-api-tests.ps1 -TestTarget @('apps/api/tests/test_financial_ledger.py')
```

General gates are:

```powershell
uv run ruff check .
uv run mypy apps/api/src apps/worker/src
.\scripts\dev\run-migration-validation.ps1 -Mode Full
corepack pnpm contracts:check
uv run python scripts/dev/check-functional-operation-matrix.py
.\scripts\dev\check-foundation.ps1 -Stage All
```

Migration-only checks do not prove operational adoption. Model-level numerical
examples do not prove a POS or Backoffice integration. Existing economic tables
are preserved; this task neither classifies their development rows as production
nor recalculates their historical closes.

## Delivery rule and retained work

Acceptance is established by the eight Foundation stages and the required
aggregate for the immutable delivered commit. Its exact SHA and workflow link
accompany delivery. Local edited-tree evidence proves only the commands actually
executed and does not substitute for that immutable-commit result.

The ADR's adoption map remains authoritative for 042-047. General accounting,
unapproved tips/FX/surcharges, provider hardware/compliance, pricing workflow,
physical-ledger integration, analytical projections and productive opening-data
approval are outside 041. No arbitrary monetary floor, cancellation percentage,
provider capability or operational readiness claim is introduced.
