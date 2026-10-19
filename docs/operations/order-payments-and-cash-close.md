# Order payments and cash close

ZM-FIN-042 connects order collections and refunds to the actual cash session.
This manual describes the implemented scope, not a declaration of production readiness.

## Recording a payment

1. Sign into POS and open the cashier's session before creating a paid order,
   collecting its remaining balance or recording an applicable cancellation refund.
2. Record only the amount actually collected. The current order form accepts the
   applied amount; it does not calculate tendered cash or change. Return any change
   separately at the counter and enter only the amount retained for this payment.
3. For CARD, complete the charge on the external terminal first, then record its
   amount in ZeroMerma. This is an accounting declaration by the operator. It is
   not a BBVA authorization, capture confirmation or bank settlement integration.
4. A mixed payment contains its actual CASH and CARD amounts. Their sum must match
   the declared advance or remaining balance. Never record the same receipt twice.
5. If the response is interrupted, recover or retry the same intention. Preserve
   its idempotency key; do not enter a replacement payment merely because the
   response was lost.

The current order workflow records an advance on creation and the full remaining
balance on delivery. An already paid order can be delivered without another receipt.
There is no independent installment endpoint in this task. Backoffice can deliver
a fully paid order; it redirects monetary actions to POS and its open session.

Each actual payment has one immutable financial operation and one confirmed entry.
Payment detail exposes the actual session/workstation and financial identities.
Audit and outbox retain those identities in the same transaction. The operation's
amount and its entry must never be added together as two receipts.

## Reading the cut

The session receiving the money owns the collection, even if the order was created
in a previous session. A later refund belongs to the session that pays it out.
Closing an earlier session does not move its receipt into the later session.

```text
expected CASH = opening CASH
              + non-order CASH inflows - non-order CASH outflows
              + order CASH collections - order CASH refunds
              + signed order technical compensations
difference = counted CASH - expected CASH
```

The POS summary, preview and detail identify the order contributions. Backoffice
cash flow links each entry to its order and actual cut. The cut separates order
advances, settlements, refunds and technical compensations from ordinary sales.
CARD appears in the method breakdown but does not change drawer cash. POS calculates
the cash difference using only the CASH count, even when a CARD count is also entered.

Example: opening 500.00, sale receipts 21.00 and an order settlement 6.00 produce
expected cash 527.00. Counting 527.00 produces a difference of 0.00. An additional
CARD receipt belongs in the payment report, not in those 527.00 physical pesos.

Count the actual cash; never fabricate a balancing collection. A payment competing
with close either commits first and is included, or is rejected after the session
closes. A replay returns its prior acknowledgement without another financial entry.

## Recognition and retained boundaries

Collecting an advance is customer funding; it is not another ordinary sale. Delivery
is the approved revenue-recognition event, but this task does not implement new
revenue analytics or create a synthetic `Sale` when an order is delivered. Cash flow
records the time of collection/refund, independently of that recognition event.

The existing cancellation eligibility and original-method refund split remain in
place. They are not the complete approved cancellation/CASH_FIRST/partial-refund
workflow. ZM-FIN-044 and the order workflow task retain that work; ZM-FIN-046 retains
provider evidence, UNKNOWN resolution and integrated refunds. Confirm the external
refund before recording the current CARD cancellation workflow. A financial reversal
is distinct from a commercial cancellation; no new reversal command is exposed here.

Only CONFIRMED entries enter these totals. Pending, processing, unknown, rejected
and cancelled entries are not cash received or returned. General close blockers for
unresolved financial obligations belong to ZM-FIN-045.

Existing development payments are not backfilled or silently counted from another
table. Their missing financial references remain explicit. Do not use pre-adoption
test history as a productive opening balance. Productive cutover and historical
reconciliation remain ZM-FIN-047 under DEC-19.

The schema remains at revision 0044. There is no migration, provider configuration,
terminal integration or modification of an operational database in this task.
