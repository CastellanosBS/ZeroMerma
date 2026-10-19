# Canonical financial cash close

Opening a turn records one explicit CASH_OPENING operation, including a valid
zero opening. A positive fund has one confirmed CASH entry. Missing opening
evidence blocks close instead of silently assuming zero.

New sales, operating payments/receipts and order payments have causal financial
operations and actual-method entries within the same business, audit, outbox and
idempotency transaction. Only CONFIRMED entries enter money totals. CashMovement
is not a second source or fallback for these flows. Existing test history is not
promoted or backfilled by schema migration.

```text
applied sale CASH = cash tendered - cash change
expected CASH = confirmed CASH IN (including opening) - confirmed CASH OUT
expected CARD = confirmed CARD IN - confirmed CARD OUT
method variance = captured method count - expected method amount
```

Change is already excluded from applied CASH; there is no second change outflow.
An operational charge/receipt adds cash and an operational payment subtracts it.
Refund obligations alone do not move money; actual settled refund legs do.
Technical compensation keeps the original entry and adds the opposite effect.
The framework can read such a compensation but does not expose a generic manual
"fix money" endpoint.

MIXED means more than one distinct positive method in a sale's confirmed entries.
CASH 40 plus CASH 60 is CASH; CARD 60 plus CASH 40 is MIXED. A cash tender returned
entirely as change does not create a zero financial entry or make a CARD sale mixed.
Repeated method components remain separate entries. Reports count mixed sales;
they do not add a fictitious MIXED monetary total to CASH and CARD.

The cashier must count CASH. CARD reconciliation can be blank, explicit zero or
a captured amount; these are different states. CARD never changes drawer variance.
The CARD count is a signed net amount: an operating CARD outflow without a receipt
can produce expected CARD-10, counted CARD-10 and zero variance. CASH remains a
nonnegative physical count. A negative CARD net is not negative physical cash.
Preview displays expected/count/variance by actual method. Commit freezes both
method expectations under the turn boundary. A blank CARD count freezes null count
and null variance. A later refund uses its actual current turn and cannot rewrite
the earlier close. Older snapshots lacking CARD expectation remain unknown.

PENDING, PROCESSING and UNKNOWN admitted entries block closing their actual turn.
A refund remainder without an admitted money leg remains a debt and can be paid
in an authorized later turn; it does not permanently trap the original turn.
See [refund settlement](refund-settlement.md) for safe resumption and recovery.

The cash-cut refund detail keeps each confirmed delivery as a separate entry.
Related documents list each return once: its amount is the sum of confirmed
deliveries in the displayed turn, and its date is the latest of those deliveries.
Deliveries in another turn are excluded from both that amount and that date.

Example: opening100, CARD sale16, CASH applied20 (tender30/change10), operating
receipt10 and payment5 gives expected CASH125 and CARD16. Cash count125 has zero
variance. Missing CARD count has no variance; explicit CARD0 has variance-16.
POS and Backoffice use the same canonical amounts. CARD accounting is not bank
settlement evidence; see the [terminal gate](payment-terminal-boundary.md).
