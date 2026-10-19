# PostgreSQL command concurrency

ZM-FIN-036–038 implements the shared transaction boundaries for existing cash
commands and inventory writers. DEC-06 governs cash admission and closure;
DEC-08 governs stock identity and ordering; DEC-07 preserves command identity;
DEC-18 requires business changes, audit, outbox and the terminal acknowledgement
to commit together. PostgreSQL is the authority. Browser coordination and HTTP
authentication do not replace database locks.

Validation and remaining boundaries are recorded in
[concurrency-validation.md](../implementation/concurrency-validation.md).

## Transaction ownership and lock order

The idempotency executor owns the root transaction. It reserves the UUIDv7 key,
runs the action, rechecks authorization and commits the safe result with its
effects. Actions may flush and use savepoints; they must not commit independently
or perform external work while holding locks.

For a new cash command, the implemented order is:

1. The existing HTTP identity, user and authentication-session boundary, when
   the command arrives through HTTP.
2. The idempotency reservation and authorized historical context.
3. The exact `CashSession` row.
4. Dependent business rows, such as the original `Sale` for a return or the
   `CustomerOrder` for a POS order transition.
5. Any applicable inventory balance write set in deterministic order.
6. Domain effects, audit, outbox and terminal result, followed by one commit.

This is the cash-specific ordering clarified in DEC-08: acquiring a dependent
business row and then waiting for its cash session would invert the boundary.
Physical commands without a cash session lock their business document and then
their complete balance write set. Commands sharing a boundary must use the same
order.

Current HTTP authentication can serialize requests from the same user before
they reach these locks. Concurrent HTTP submissions are useful end-to-end tests,
but they cannot by themselves prove the domain protocol. Database tests use
independent transactions and observe the actual blocking relationship.

## Cash admission and closing

`modules/cash/application/command_context.py::lock_cash_session` selects the
explicit cash-session ID using PostgreSQL `FOR NO KEY UPDATE`, refreshes the ORM
row with `populate_existing=True`, and validates actor, branch, workstation and
`OPEN` after acquiring the lock. The lock lasts until the executor commits or
rolls back. No process-local mutex or global cash lock is involved.

`NO KEY UPDATE` is intentional. Idempotency reservation foreign keys can already
hold `KEY SHARE` on the cash-session row. Their compatibility prevents two distinct
reserved keys from deadlocking while they each try to acquire an unnecessarily
strong `FOR UPDATE` lock. The session's key is not changed; concurrent financial
actions still serialize on its row.

The boundary covers sales, POS order actions, return refunds, operational payments,
operational discounts and close. Opening retains its separate user/workstation
uniqueness boundary. An order read-only context resolver does not acquire the cash
action lock; the new-write action does. Return refund entitlement is checked
under the original sale's lock after acquiring the cash session.

There are two valid race outcomes:

- An operation obtains the boundary first, validates `OPEN` and commits. Close
  subsequently obtains fresh state and recalculates the existing close projection.
- Close obtains the boundary first and commits. A waiting new operation then sees
  `CLOSED` and is rejected without a business effect.

If the first transaction rolls back, the waiter proceeds against the rolled-back
state. A preview does not reserve admission; close recalculates under its lock.
`CLOSING` remains a transactional interval, not a persisted state or an intermediate
commit. Successful close also revokes the bound POS authentication sessions in
the same transaction. `CLOSED` remains terminal.

Replay is different from admitting a new write. The executor reauthorizes the
original context and returns its immutable terminal result without running the
action or requiring the original shift to remain open. A valid new login can
therefore recover a completed close or operation from a historical shift.

### ZM-FIN-037 and the order ledger boundary

The shared lock guarantees the temporal admission of order advances, settlements
and refunds relative to close. Existing `CustomerOrderPayment` records still do
not all create the canonical `CashMovement` entries consumed by the close formula.
That integration is ZM-FIN-042. This block does not change totals, reconstruct a
missing order ledger or claim that those payments are already included in the
financial close equation.

The current financial writer catalog is:

| Command | Existing financial effect | Cash boundary |
| --- | --- | --- |
| Sale confirmation | `CashMovement` for the cash collection leg | Before the sale and its effects |
| Operational payment | `CashMovement` for a CASH outflow; CARD retains its existing non-cash behavior | Before either payment method is admitted |
| Operational discount | `CashMovement` for a CASH inflow; CARD retains its existing non-cash behavior | Before either payment method is admitted |
| Return commit | CASH refund `CashMovement` | Before locking the original sale and validating remaining entitlement |
| POS order creation/delivery/cancellation | Existing advance, settlement or refund `CustomerOrderPayment` when applicable | Before the order action; ledger integration remains 042 |
| Cash close | Existing projection over `CashMovement` and the close record | Recalculated while the session is locked |

Backoffice order delivery only permits zero remaining balance; cancellation that
would require a refund is rejected there. Those paths do not add cash effects or
become an alternative to the POS financial boundary.

For effects already materialized in the cash ledger, the concurrent tests must
verify both the effect and the close equation. For order payments they must verify
the admission ordering and absence of a new payment after close, while retaining
the explicit ledger gap. Financial normalization remains ZM-FIN-041–045.

## Inventory write sets and first-row races

`modules/inventory/application/mutations.py` provides `InventoryBalanceKey`,
`lock_inventory_balances` and the transaction-local `LockedInventoryBalances`.
The natural key is `(product_id, branch_id, location_code)`, enforced by the
existing `uq_inventory_balances_product_branch_location` constraint. Lock ordering
uses `(branch_id, product_id, location_code)` regardless of a transfer's direction
or a recipe's input/output ordering.

Each writer declares its complete write set before applying stock effects. The
helper deduplicates and sorts the keys, locks existing rows and loads fresh values.
For a missing row it attempts an ORM insert inside a savepoint, preserving the
authorization guard. Only a violation of the known balance uniqueness constraint
is recovered by loading the concurrently created row under lock. Other integrity
errors escape and roll back the command; they are not interpreted as a successful
stock update.

The locked collection retains the same ORM objects for the transaction. Applying
several lines to the same balance accumulates their deltas without refreshing away
pending changes under `autoflush=False`. The collection cannot be reused after the
root transaction ends. An inventory movement and its balance change are created
together; an exception after either flush rolls them both back with the command.

Inventory adjustments, administrative waste, purchases, administrative transfers
and production use this shared writer. A finite nonzero Decimal delta and the
existing unit of measure remain required. Ordinary outbound effects cannot consume
unavailable stock. Existing inventory adjustments explicitly retain their negative
balance behavior. Administrative receipt also preserves the `IN_TRANSIT` exception
for shipments created by the still-documentary POS path; this block does not invent
the missing POS dispatch stock movement. These exceptions remain visible at the
caller, without a new negative-stock, reservation or conversion policy.

Independent products and branches have no shared inventory lock. Two commands for
the same natural key serialize; concurrent first entries produce one balance with
both committed movements. A failed command leaves neither a partial balance update
nor an orphan movement.

## Transient conflicts and retry

The executor bounds domain lock waits with a transaction-local `lock_timeout`
(5,000 ms by default). Idempotency-key contention retains its separate 1,000 ms
default and existing key-in-progress behavior. Successful execution restores the
previous timeout before commit; rollback discards transaction-local settings.
These are lock-wait bounds, not whole-command latency guarantees.

This timeout and error translation apply only inside the shared executor and its
adopted commands. Earlier HTTP authentication locks are outside that boundary, as
are the 19 administrative idempotency gaps still assigned to 077/080/085. This
block does not give those paths an identical timeout or retry contract. The five
existing inventory writers do use the shared balance mutation protocol described
above.

PostgreSQL lock timeout/unavailability (`55P03`), deadlock (`40P01`) and serialization
failure (`40001`) roll back the root command. They produce HTTP 409 with code
`CONCURRENCY_RETRY`, `details.retryable=true`, `Retry-After: 1` and `Cache-Control:
no-store`. They do not persist a terminal business rejection or a partially
completed intention. Unrelated database errors retain their normal failure path.

The browser preserves the same key and frozen body for a retryable response. It
does not replace the intention or treat the response as a known business rejection.
There is no automatic retry loop. After a reload the body is absent by design:
only result lookup is possible, and a still-unknown result requires the existing
operational review path. Authentication changes discard volatile bodies while
retaining recovery metadata. A fresh command must never be inferred merely from
an uncertain response.

## Scope and evidence limits

The existing schema is sufficient; no migration or alternate balance store is
introduced. POS document-only operations do not acquire a new physical ledger.
Unified transfer/return effects, reservations, production WIP and costing remain
their assigned tasks, including 051/052/054/069. Administrative idempotency gaps
in 077/080/085, the purchase PATCH UI gap and reconciliation gaps remain open.

Tests run against guarded disposable PostgreSQL. Evidence records transaction IDs,
backend process IDs, observed wait relationships and final reconciled effects;
it must not expose SQL bind values, credentials or raw session material. Local
timings describe that test environment, not a production SLA. This protocol alone
does not certify deployment, load capacity, backup recovery or product readiness.
