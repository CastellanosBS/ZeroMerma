# Checkout and customer orders

This guide describes the implemented POS workflow. Physical printer acceptance, a bank
integration and a business-approved order lead time must be verified separately before opening.

## Before the first order

An authorized backoffice operator must configure the branch's **Order commitment policy**.
Enter the actual planning lead time in minutes and a meaningful reason. There is no production
default: quoting an order fails closed until a policy exists. The policy is versioned, audited
and recoverable after a lost response. Recovery returns the exact saved version even if a newer
policy has since been configured.

The disposable browser and API validation fixtures use explicitly synthetic policies. Their
values are test inputs, not recommendations for the bakery.

An authenticated cashier must use their bound workstation and an open cash session. Opening,
collection, delivery collections and refunds belong to the actual session that processes them.

## Checkout

Review the products, quantities and payment breakdown before confirming a sale. The POS submits
the expected price and currency of every line. If the catalog changed, update the cart prices,
review the resulting total and confirm again. A price refresh never automatically posts a sale.

In the separate-terminal workflow, **CARD is an accounting record of an external collection**.
Charge the terminal separately, verify its actual approval and then enter the applied amount.
Recording CARD in ZeroMerma does not by itself charge BBVA or prove a provider authorization.
Changing the cart invalidates the reviewed payment. Verify the amount actually charged before
confirming again; ZeroMerma cannot correct or cancel a charge made on the separate terminal.
This distinction also applies to order advances and intermediate collections. Cash fields record
the amount applied to the order; avoid entering cash tendered as though all of it were an advance.

If a confirmation result is uncertain, use the pending operation's recovery action. Do not create
a replacement operation or charge the customer again. A browser reload retains recovery metadata,
not the sensitive request body. Consult the recorded result when a same-body retry is unavailable.
The cart remains locked during submission and while the original result is unresolved.

## Creating an order

1. Capture the customer, exact products, quantities and collection date/time.
2. Enter an advance of at least 50% of the quoted total, rounded up to the smallest currency unit.
   CASH and CARD may be combined with an explicit amount for each method.
3. Select **Guardar pedido**, review the server quotation, minimum advance and production
   commitment time, then select **Confirmar pedido cotizado**.
4. Verify the confirmed folio, remaining balance and payment history. Each actual collection has
   its own immutable operational receipt; a status change does not create another collection.

The commitment decision uses PostgreSQL's wall clock after acquiring the order lock, so waiting
for another operation or a wrong workstation/server application clock does not extend the window.

The collection time is interpreted in the **branch's IANA timezone**, independently of the
computer's timezone. Ambiguous or nonexistent daylight-saving times are rejected. Commitment
is calculated by subtracting the configured elapsed minutes from the requested collection time.
Both the timezone evidence and the accepted commercial version are frozen.

A quotation must still match the current prices and policy when it is confirmed. If either
changed, obtain and review another quotation. The already confirmed order retains its historical
prices and policy; a later catalog or policy change does not silently reprice it.

## Advances and commercial changes

Select an order and open **Abonos y cambios**.

- **Confirmar abono** records the explicit CASH/CARD amounts against the remaining balance.
  It accepts only positive amounts and rejects an overpayment or a terminal order.
- **Modificar pedido** can change exact products, quantities and the requested collection time
  while the order is PENDING and before its frozen production commitment. Capture the reason,
  obtain a new quotation and select **Confirmar nueva versión**.
- If the new total requires more money to maintain the 50% minimum, include the additional
  payment in that same confirmation. A reduction below the amount already received is rejected.
  The new version, its additional payments and financial facts commit or roll back together.
- Another operator's change causes a version conflict. Reload and review the current version
  before making a new decision. Do not blindly repeat the amendment with a newer version number.

The prior commercial versions remain immutable. After the production commitment time, commercial
amendments are blocked. READY is a separate operational transition; it cannot be used to move
the commitment time or mark an order ready before that time. READY reserves the exact products;
delivery consumes those reservations once and requires the remaining amount to be settled.

## Cancellation and final outcomes

Cancellation requires a reason, an explicit responsible party and a terminal outcome
(CANCELED, EXPIRED or NO_SHOW). These are deliberate operator actions; the system does not
silently terminate an order because its collection time passed.

| Responsibility and timing | Financial outcome |
| --- | --- |
| Customer, before production commitment | Full refund of the accumulated advance |
| Customer, at or after production commitment | Retain the accumulated advance; no delivered-sale revenue |
| Merchant, before or after production commitment | Full refund of the accumulated advance |

The result distinguishes confirmed refunds from amounts that still require financial resolution.
Follow the recorded refund status and actual method; a cancellation acknowledgement is not proof
that an external provider refunded a card. A refund requiring cash must be handled through an open
cash session. Administrative cancellation cannot bypass that financial requirement.

Cancellation releases outstanding inventory reservations. DELIVERED recognizes the order's sale
amount; pending advances and retained amounts are shown separately. Historical orders without
verifiable policy/version evidence fail closed and require administrative review rather than an
invented cutoff.

## Before opening the branch

Run the isolated API/browser acceptance suites, then rehearse the complete physical workflow:
open with the intended fund, create an order, collect an intermediate payment, amend before
commitment, process a committed delivery, cancel under each responsibility rule, inspect receipts
and reconcile the cash cut against the actual payment methods. Test a lost response and reload
without repeating the collection. Verify that a closed session rejects further mutations.

Use the approved business lead time for this rehearsal. Record physical printer behavior,
separate-terminal procedures and the actual cash/card reconciliation as operational evidence;
passing simulated or browser tests alone does not certify those devices.
