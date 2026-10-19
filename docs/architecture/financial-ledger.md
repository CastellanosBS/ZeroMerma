# Canonical financial ledger

Status: ZM-FIN-041 foundation implemented and locally validated. This ADR records
the design derived from approved decisions and its adoption boundary. Executed checks are recorded in
[financial-ledger-validation.md](../implementation/financial-ledger-validation.md).
The numerical examples below are derived acceptance cases from approved decisions;
they are not new business policies or claims of separate user approval.
Delivery acceptance requires the eight Foundation stages and required aggregate
for the immutable delivered commit; its SHA and workflow link accompany delivery.

## Decision and scope

The canonical representation has two tables:

- `financial_operations` records immutable admission, a causal economic purpose,
  the amount due or obligation, its currency, source and authorized context.
- `financial_entries` records the actual method legs. Confirmed entries are the
  ledger; a second posting table does not mirror them.

An operation is not itself another amount to add to its entries. Its identity and
obligation explain those entries. Pending allocation and completed economic effect
are different facts. Operation summaries are derived from the operation, its legs
and explicit compensations.

041 added this foundation without admitting operational writes to it. ZM-FIN-042
now adopts order payments and their cash-flow/close consumers as described below.
Other producers retain their current sources. The new tables start empty;
migration does not interpret existing rows,
backfill demo data or turn on a second stream of production postings. There is no
new POS/Backoffice workflow, provider adapter, general accounting system or bank
integration in this task.

The adoption map below assigns each producer and consumer to its later task. An
adopting flow must designate one source for each effect and move its consumers
deliberately. Adding new totals to the same legacy totals is never a transition
strategy. The inactive foundation does not prove that today's cash close already
includes every approved financial flow.

## Authority

The governing rules are DEC-05/06, DEC-09/10/11/13/14 and DEC-18/19 in
[the canonical decision record](../DECISIONES_ZERO_MERMA.md).

PostgreSQL is the transaction authority. Financial values use `Decimal`/`Numeric`,
monetary scale `0.01` and `ROUND_HALF_UP`; binary floating point is not money.
Every document and its entries share one currency. The initial physical schema
supports MXN, consistent with the current operational currency. This model
introduces neither FX conversion nor mixed-currency payments.

The backend determines the economic amount. A method, external authorization,
cash tender, commercial price, provider fee and recognized sale revenue are
distinct concepts. Client metadata and current catalogue values cannot rewrite
an admitted operation or its original pricing basis.

## Dictionary and identity

The physical models are `FinancialOperation` and `FinancialEntry` in
`apps/api/src/zeromerma_api/modules/financial_ledger/infrastructure/models.py`.
The cause/state catalogue is in the same module's `domain/constants.py`.

| Concept | Meaning and invariant |
|---|---|
| Operation identity | Stable UUID of one admitted economic cause; distinct from request, event and provider IDs. |
| Source identity | Explicit source document/type and causal effect; never inferred from matching timestamps, folios or amounts. |
| Operation kind | Receipt, refund, opening cash, opening obligation or another explicitly catalogued financial purpose. A business refund is not a technical reversal. |
| Amount due | Immutable amount the operation must resolve; never another ledger posting. |
| Currency | One currency shared by operation, entries and causal financial references. |
| Admission context | Authorized actor, branch, workstation/cash-session context and operation trace at admission, where applicable. |
| Entry identity and `leg_key` | Stable leg identity with uniqueness inside its operation and causal-effect protection. Repeating a command cannot create another copy. |
| Actual method | A real enabled method such as CASH or CARD; never MIXED. |
| Entry amount | Positive applied amount of one leg. Direction expresses its effect; negative input is not a shortcut around the cause catalogue. |
| Tendered/change | CASH retains tendered, applied and change; non-CASH change is zero. |
| Entry state | Distinguishes allocation, uncertainty, rejection and confirmed effect. Nonterminal amounts are not settled totals. |
| Entry cash session | The actual drawer/turn in which this leg takes effect; it may differ from the operation's original admission session. |
| Execution provenance | Accounting-only registration, integrated provider evidence or controlled manual fallback remain distinguishable. |
| Refund reference | Identifies the source return/payment document and economic subject; `REFUND_OF` may additionally identify a particular original receipt. A CASH refund may have a different method from that receipt. |
| Technical compensation reference | Explicit link to the corrected financial effect; the original remains queryable and unchanged. |
| Opening obligation kind | RECEIVABLE, PAYABLE or CUSTOMER_ADVANCE; establishes an opening position, not a drawer movement. |
| Evidence and trace | Reason/source evidence for opening or compensation, actor/scope, occurred/recorded times, idempotency and operation-context identities. No credentials or payment secrets. |

Both tables carry `branch_id`, optional `workstation_id`/`cash_session_id`,
`actor_id`, `currency_code`, `context_version`, `source_app`, `actor_type`,
`operation_id`, nullable `operation_code`, `correlation_id`, `causation_id`, `request_id`, `idempotency_key`,
`related_branch_ids`, `occurred_at` and database-generated `recorded_at`. The
financial row's `id` is distinct from the cross-cutting `operation_id`.
Evidence references are identifiers, not payment credentials or raw provider
payloads. PAN, CVV, authentication secrets and cardholder data are not fields of
these tables or their projection snapshots.

| Table | Additional physical fields |
|---|---|
| `financial_operations` | `id`, `kind`, `source_type`, `source_id`, `effect_code`, `subject_type`, `subject_id`, `amount_due`, `opening_obligation_kind`, `opening_reason_code`, `source_evidence_reference`, `cutover_at`, `related_operation_id`, `relation_kind` |
| `financial_entries` | `id`, `financial_operation_id`, `leg_key`, `payment_method_code`, `direction`, `amount`, `tendered_amount`, `change_amount`, `execution_mode`, `state`, `confirmed_at`, `resolution_kind`, `resolution_reference`, `reverses_entry_id` |

Amounts use `Numeric(12, 2)`. `amount_due` permits zero; an actual entry's amount
must be positive. Cause identity is unique on
`(source_type, source_id, effect_code)`, with `effect_code = kind`; entries are
unique on `(financial_operation_id, leg_key)`. One cash opening is admitted per
cash session. A nullable operation relation is not permission for a causeless
refund: its source and economic subject remain explicit and validated.

The cause catalogue preserves these directions and identities:

| Operation kind | Source type | Direction/effect |
|---|---|---|
| `CASH_OPENING` | `CASH_SESSION` or evidenced `OPENING_STATE` | CASH IN when positive; explicit zero has no entry. |
| `SALE_COLLECTION` | `SALE` | IN, actual customer collection. |
| `ORDER_ADVANCE`, `ORDER_SETTLEMENT` | `ORDER_PAYMENT` | IN, actual receipts against the ORDER subject. |
| `SALE_REFUND` | `SALE_RETURN` | OUT, against the SALE subject and refundable right. |
| `ORDER_REFUND` | `ORDER_PAYMENT` | OUT, against the ORDER subject and refundable right. |
| `OPERATIONAL_PAYMENT` | `OPERATIONAL_PAYMENT` | OUT. |
| `OPERATIONAL_CHARGE` | `OPERATIONAL_DISCOUNT` | IN; retains the existing internal collection semantics. |
| `CASH_DEPOSIT` | `CASH_DEPOSIT` | CASH IN in the operation's own cash session; catalogue support does not create an operational deposit workflow. |
| `CASH_WITHDRAWAL` | `CASH_WITHDRAWAL` | CASH OUT in the operation's own cash session; catalogue support does not create an operational withdrawal workflow. |
| `TECHNICAL_REVERSAL` | `FINANCIAL_ENTRY` | Opposite causal effect; original identity is preserved. |
| `OPENING_OBLIGATION` | `OPENING_STATE` | Opening RECEIVABLE/PAYABLE/CUSTOMER_ADVANCE position, with no drawer entry. |

`subject_type`/`subject_id` group the economic object independently from the
source document. For example, an order can receive several ORDER_PAYMENT causes
across turns while retaining one ORDER subject. `SETTLEMENT_OF`, `REFUND_OF` and
`REVERSAL_OF` express the allowed operation relationships, not inferred matches.
An ORDER refund may reference an evidenced opening CUSTOMER_ADVANCE obligation;
that opening position does not become a new receipt in the current drawer.
`SETTLEMENT_OF` accepts only an opening RECEIVABLE. An opening PAYABLE or
CUSTOMER_ADVANCE is not reclassified as an amount to collect from the customer.

The operation's admission identity and economic terms are immutable. Entries in
CONFIRMED, REJECTED or CANCELLED state are immutable; no entry may be deleted.
An unresolved entry can resolve only within its original identity, amount, method
and context. Corrections use an explicit new compensating effect. `REVERSED` is derived from
the original and its confirmed technical compensation; it is not an update that
erases the original posting. A refund does not automatically reverse the original
payment, restore return entitlement or restore inventory.

A technical reversal is a confirmed, full compensation of one confirmed original
entry, with the same amount, method and currency and the opposite direction. Its
source and reversal references identify that entry exactly; only one technical
reversal may reference it. This does not restrict a business refund to the method
or amount of one particular receipt: the economic SALE/ORDER subject groups its
relevant receipts and obligations.

The existing [operation-context](operation-context.md),
[idempotency](idempotency.md), [transaction ownership](transaction-boundaries.md)
and [concurrency](concurrency.md) conventions remain applicable. No request ID
becomes a financial uniqueness key, no participant gains a hidden commit, and
no financial effect is inferred from an audit payload.

## Allocation, completion and uncertainty

An allocation reserves part of the operation's due amount. The sum of legs other
than REJECTED/CANCELLED cannot exceed that amount. Equality is not mandatory while a refund is partially
settled or part of its obligation has no eligible method yet. Unassigned remainder
is explicit debt; inventing a CARD leg is not a way to satisfy equality.

The persisted entry states are `PENDING`, `PROCESSING`, `UNKNOWN`, `CONFIRMED`,
`REJECTED` and `CANCELLED`. Derived operation states also distinguish
`PARTIALLY_SETTLED`, `PARTIALLY_REVERSED`, `REVERSED` and `OPENING_RECORDED`.
An opening obligation's recorded state does not imply a settled payment.

`PENDING`, `PROCESSING` and `UNKNOWN` entries are excluded from completed financial
totals. `UNKNOWN` is neither failure nor permission to repeat the same effect with
a new key. A terminal rejection proves no confirmed effect for that entry; its
historical identity must not disappear to permit a duplicate uncertain charge.
An unresolved UNKNOWN leg remains visible even if another leg of the operation
already has a confirmed technical compensation; reversal does not conceal it.

Execution modes are `LOCAL` for CASH and `ACCOUNTING_ONLY`,
`PROVIDER_INTEGRATED` or `MANUAL_FALLBACK` for CARD. Resolution kinds distinguish
`LOCAL_CASH`, `EXTERNAL_RECORDING`, `PROVIDER_CAPTURE`, `PROVIDER_REFUND`,
`PROVIDER_REJECTION`, `PROVIDER_VOID` and `MANUAL_RECONCILIATION`. Recording an
evidence UUID is not a replacement for the future adapter's verification.

For integrated CARD, completion requires authoritative evidence equivalent to
`CAPTURED`. Authorization alone is insufficient. Bank `SETTLED` is a later
reconciliation dimension and is not the ordinary completion threshold. An
`ACCOUNTING_ONLY` entry records a payment performed outside ZeroMerma; it must not
pretend that ZeroMerma obtained provider authorization or capture. The actual
provider lifecycle belongs to 046.

The amount applied/settled inside an operation must not be confused with bank
settlement. Gross confirmed inflows, gross confirmed outflows, outstanding
obligations and net effects are separate projections. Confirmed originals and
compensations both remain in the explanation of a net result.

## Cash, composition and equations

For a complete payment:

```text
sum(confirmed applied legs) = amount_due
CASH tendered = CASH applied + CASH change
non-CASH change = 0
```

Only CASH generates change. The drawer effect is the applied CASH amount once;
there is no additional change-out posting that subtracts it twice.

```text
methods = distinct actual methods with confirmed applied amount > 0
no methods -> no payment-method classification (None)
one method -> that method
two or more methods -> MIXED
```

Transaction classification and a multi-payment order's historical composition are
different analytical dimensions. Neither is an extra payment leg.

```text
expected_cash = opening_cash
              + confirmed CASH inflows
              - confirmed CASH outflows
cash_capacity = max(expected_cash, 0)
difference = counted_cash - expected_cash
```

Opening cash contributes once, whether a projection exposes it separately or
includes its classified entries in an internal sum. An explicit zero opening has
an operation and no zero-value entry. RECEIVABLE, PAYABLE and CUSTOMER_ADVANCE
opening obligations have no drawer entries: owing or being owed money is not
proof that cash was physically received at cutover.

A count of zero differs from missing count. A discrepancy requires its approved
reason; it never rewrites expected cash or creates a fictitious balancing entry.
These equations specify the target projection; integrating them into operational
cash close is 045.

Every admitted effect that can change a turn must participate in its CashSession
boundary. A pending or UNKNOWN admitted effect can block close even while it is
excluded from settled totals. A merely open order or physical transfer does not
automatically block financial close. CLOSED is terminal; a later financial effect
uses an authorized current session and preserves the historical close.

## Refund and order obligations

Refunds require a valid causal document and an available economic right. Their
ordinary policy is CASH_FIRST:

```text
cash_refund = min(refund_due, cash_capacity)
pending_after_cash = refund_due - cash_refund
```

The actual refund composition need not match the original payment composition.
After CASH capacity is exhausted, only eligible original non-cash operations may
fund the remainder. No minimum float or safety reserve is invented. An ordinary
refund cannot make authoritative expected cash negative. This specific refund
rule is not a new universal prohibition on every existing operational outflow.

The foundation's pure allocation function receives the verified remaining CARD
eligibility and current expected CASH as inputs. It does not discover provider
eligibility, authorize a business refund or reserve the economic subject itself.
Future command adoption must validate those inputs and serialize admission against
the source subject and actual cash session. The persisted per-operation allocation
bound is not a substitute for a cumulative return/refund-entitlement check.

A partial refund preserves the outstanding obligation and the identity of every
completed leg. Retrying its remainder must not execute the completed CASH leg
again. Receiving goods, consuming return entitlement and paying the refund are
different effects. Refund amount uses the original allocated net line value,
including its rounding residual, rather than current prices or promotions.

For orders, advances and settlement receipts are real financial effects in their
actual turns. Revenue is recognized at DELIVERED, exactly once, without a fake
Sale assigned to one of several payment turns. Minimum advance is
`Q(net_order_total * 0.50)`; overpayment is prohibited. Amendments must explicitly
and atomically resolve any new advance deficit or excess payment. Cancellation
uses responsibility and the approved PRODUCTION_COMMITTED boundary; retained
advances remain distinct from delivered-sale revenue. These policies constrain
the foundation and its future adopters; 041 does not implement those workflows.

## Internal projections and adoption responsibility

`FinancialLedgerQueryService.read_branch` requires an explicitly bound
authorization scope, refreshes current authority and requires `cash_finance.view`
with permission for the requested branch. After authorization, it reads the fact
graph's operation/entry pairs with one outer-joined SELECT, so PostgreSQL supplies
one fact snapshot rather than two independently changing lists. Authorization
may perform its own queries; this is not a claim of one SQL statement overall. It neither
flushes nor commits, returns frozen domain snapshots and has no fallback to
legacy CashMovement or order-payment tables.

`get_cash_projection` passes that graph to the pure cash-session projection.
The pure rules validate causal identities, relation scope, method evidence,
allocation bounds and compensation before deriving totals. A missing or
incomplete opening is an invalid projection, not an implicit zero balance.
The explicit zero-opening operation is the valid exception with no entry.

This internal service has no HTTP endpoint in 041. Loading a complete branch
graph supports foundation validation; it is not a throughput claim or the final
query plan for live cash close. Adoption in 042-045 must provide efficient reads
with appropriate scope and a complete causal graph. It must also own commercial
debt/entitlement validation, provider-evidence verification, refund eligibility,
CashSession admission and the atomic domain/audit/outbox transaction. A pure
allocation or a successful read is not proof that money was paid.
Database context checks validate branch/workstation/session relationships; they
do not independently authorize a caller or enforce the operational OPEN-session
boundary. Those remain obligations of the adopting command, including ensuring
that a later posting never changes a historical closed turn.

Entry writes support the canonical READ COMMITTED transaction isolation. The
database guard rejects REPEATABLE READ and SERIALIZABLE entry writes explicitly:
a parent lock alone does not refresh a previously established transaction snapshot
for the allocation sum. This does not change database configuration or claim
validation of custom isolation settings; adopting another isolation level needs
its own proven admission protocol.

## Derived numerical acceptance cases

All amounts below use a single currency. Cases involving future workflows are
model/projection examples, not claims of operational integration.

| Case | Inputs | Required outcome |
|---|---|---|
| Opening and change | Opening 200; sale due 100; CASH tendered 120 | Applied 100, change 20; expected 300, with no second change posting. |
| Mixed payment | Due 100; CARD 60; CASH applied 40/tendered 50 | CASH +40, CARD +60; classification MIXED; total 100, not 200. |
| Same-method legs | CASH 40 and CASH 60 | CASH classification, not MIXED. |
| Uncertain CARD | Integrated CARD 100 in AUTHORIZED or UNKNOWN | No completed 100; UNKNOWN preserves unresolved identity. CAPTURED may complete before bank settlement. |
| Order rounding | Total 33.33 | Minimum advance 16.67; 16.66 is insufficient. |
| Multi-turn order | Total 1000; 500 in turn A, 500 in turn B | Each actual turn explains 500; revenue remains zero before delivery, then 1000 once without another receipt. |
| Cancellation | Net paid 500 | CUSTOMER before commitment: refund due 500; after: zero by default, retained 500 separate from delivered revenue; MERCHANT: refund due 500. |
| Amendment | Total 100/paid 50 becomes total 120 or 40 | Explicit additional 10 or explicit refund 10 respectively; no silent adjustment. |
| Different refund method | Original CASH 40/CARD 60; refund due 80; capacity 100 | CASH refund 80 permitted; original CARD 60 is not rewritten as refunded CARD. |
| Unassigned refund remainder | Original CASH only; refund due 100; capacity 40 | Confirmed CASH 40, pending 60; no invented CARD or negative drawer. |
| Partial-return residual | Original net 10 across quantity 3 | Successive eligible refunds preserve cumulative bounds; the final one receives the exact remaining cents, total 10. |
| Operational receipt/outflow | Opening 100; operational receipt 20; payment outflow 10 | Expected 110; neither operational amount silently changes a commercial sale's price. |
| Fee | Customer CARD payment 100; provider fee 3 | Customer amount/revenue remain 100; fee is separate, not a customer surcharge or CASH movement. |
| Compensation | Confirmed receipt 100; confirmed technical compensation 100 | Original and compensation remain; net effect zero and derived reversal, without deleting the receipt. |
| Count discrepancy | Expected 300; counted 290 | Difference -10 with reason; expected remains 300 and no synthetic receipt is created. |
| Opening position | Explicit cash opening 0; CUSTOMER_ADVANCE obligation 250 | No drawer entries for either; the obligation is not a new payment/revenue. |
| Clean start | Validated real opening cash 250; demo/test figures 999 | Only explicitly approved opening facts can participate in production; replay does not create another 250. |

## Current sources and adoption map

The source references below describe the inspected implementation before adoption,
not an assertion that its current behavior already implements every decision.

| Flow/source today | Remaining adoption and limit |
|---|---|
| `sales/infrastructure/models.py`: SalePayment and CashMovement; sale service writes a CASH movement | 043 maps actual sale legs and causal effects; 045 moves consumers/classification. Do not sum legacy and new representations. |
| `orders/infrastructure/models.py`: CustomerOrderPayment; order service writes ADVANCE/SETTLEMENT/REFUND separately | 042 admits one financial operation/confirmed entry per actual payment in the same transaction. Order consumers read these entries, without a mirrored CashMovement or a historical payment fallback. |
| `payments/application/services.py`: OPERATIONAL_PAYMENT creates a CASH OUT movement | 043 preserves its outflow cause and actual method. This is not a sale discount. |
| `discounts/application/services.py`: OPERATIONAL_DISCOUNT creates a CASH IN movement | 043 preserves the inspected internal collection semantics. CommercialDiscount remains a pricing rule; the hidden operational-discount UI is not enabled here. |
| `returns/application/services.py`: cash refund and linked CashMovement | 044 implements the unified obligation/legs, partial settlement and causal compensation; provider refunds remain 046. |
| `cash_close/application/services.py` and `admin_services.py`: non-order totals read CashMovement; cash-flow uses existing non-order module sources | 042 adds only canonical confirmed order entries and their causal compensations, with actual session attribution and separate order fields. The sources are disjoint. 045 retains full consumer adoption, method reconciliation and unresolved-effect blockers. |
| Existing CARD rows | 046 implements provider evidence, UNKNOWN resolution, callbacks, terminal binding and reconciliation. Current CARD registration is not verified BBVA capture. |
| Existing demo/test history and future legitimate cutover evidence | 047 supplies diagnosis, dry run, selective transformation and reconciliation. No historical financial backfill is part of 041. |

043-047 remain separate work even though this foundation can represent their
required states and examples. Pricing/admission, physical ledgers, order workflow,
provider capabilities, analytics and the production cutover retain their assigned
tasks. No source gap is closed solely by adding these two tables.

For the adopted order workflow, see the
[order payments and cash-close manual](../operations/order-payments-and-cash-close.md)
and [042 validation record](../implementation/order-cash-flow-validation.md).
An order collection is funding at collection time, distinct from revenue at delivery.
CARD is explicitly ACCOUNTING_ONLY with the operator's payment record as evidence;
it is not provider capture. Existing command acknowledgement snapshots remain
unchanged; financial references are exposed on authenticated detail GETs.

## Migration and productive-data boundary

The migration is `20261019_0044_financial_ledger`, following
`20261018_0043_operation_context`. It creates empty structures and preserves
existing financial tables, operational rows, audit and outbox. A downgrade may
remove the new schema only while both tables are empty; economic evidence must
not be erased to make a downgrade possible. Use a reviewed forward correction or
a verified complete-database restore when evidence exists.

DEC-19 classifies the known local volumes as DEVELOPMENT_DEMO_TEST and identifies
no current external legacy source. That does not authorize touching those volumes
or promoting their rows. Productive opening facts need dated, scoped, validated
evidence and their own causal identity. Ambiguous real sources require manual
reconciliation; fictitious historical sales and payments are prohibited.

See [database-migrations.md](../operations/database-migrations.md) for the guarded
harness, supported history and restore procedure. Local acceptance uses disposable
PostgreSQL, never the operational database. A passing foundation does not declare
financial integration, Data Integrity Ready or production readiness.
