# Refund settlement

This describes the development implementation of ZM-FIN-044. It is not production acceptance or confirmation of a live banking integration.

## Obligation and actual money

A committed sale return admits one `SALE_REFUND` operation whose source is `SALE_RETURN`. An eligible order cancellation admits one `ORDER_REFUND` operation whose source is `ORDER_CANCELLATION`; the source and subject identify the original order. The operation's `amount_due` is the authorized refund obligation, not proof that the customer has received that amount.

Only confirmed financial entries represent money returned. Responses and detail screens expose `financial_refund` with `amount_due`, `amount_settled`, `amount_pending`, actual CASH/CARD totals, and the individual entries and their actual cash sessions. The original collection operation IDs provide causal references. A return's old `refund_cash_movement_id` is null for newly admitted refunds: no placeholder legacy movement is created. Historical stored acknowledgements remain deserializable; missing canonical evidence is not reconstructed as a successful refund.

Order refund payment history contains only amounts actually settled. Each new `CustomerOrderPayment` of type `REFUND` has an exact `financial_entry_id`; an unallocated obligation does not create a fictitious payment. Cash-flow and cash-cut reads follow those canonical entries and their reversal lineage.

## CASH_FIRST and capacity

The command locks the actual open cash session, then the original sale or order, and then the refund operation. Entitlement is checked against the original confirmed collections and previously admitted refund obligations under the source lock. Returning the physical product and settling the financial debt are distinct effects; the refund does not restore an already consumed return entitlement.

CASH_FIRST uses `max(expected_cash_amount, 0)` from confirmed canonical entries in the actual session. A validated canonical opening is mandatory. The historical `CashSession.opening_amount` alone cannot establish spendable cash. There is no extra cash reserve in this policy.

For example, a refund obligation of MXN 100 with MXN 40 available records one confirmed CASH OUT entry for MXN 40 and leaves MXN 60 pending. It does not invent a card refund or drive cash below zero. Original CARD or mixed collections may also be refunded in available cash under the approved policy. PENDING, PROCESSING and UNKNOWN refund legs continue to reserve their amounts; a cash retry cannot pay those same amounts again.

## Continuing a partial refund

The POS detail panel shows the authorized amount, confirmed delivery, pending amount and actual payment history. **Continue refund in cash** admits a new settlement command using the currently authenticated operator, workstation and open cash session. It pays only the remaining unallocated amount supported by current cash capacity. It does not replay already confirmed legs.

The obligation can originate in an earlier, closed session. New money belongs to the session that actually performs the later settlement. Unassigned remaining debt does not indefinitely block the original session's close; an admitted unresolved leg that can still affect that session does block closing.

The return receipt separates authorized, delivered and pending amounts. Backoffice displays the obligation and actual confirmed amounts without providing a financial mutation from its detail view. Aggregate refunded-money metrics use confirmed entries, including the sign of confirmed technical compensations; they do not sum all promised refunds as cash delivered.

## Commands and recovery

The continuation commands require `Idempotency-Key` and a body with `workstation_code` and `cash_session_id`:

| Source | Mutation | Recovery |
| --- | --- | --- |
| Sale return | `POST /v1/returns/{return_id}/refund-settlements` | `GET /v1/returns/refund-settlements/{idempotency_key}` |
| Order cancellation | `POST /v1/orders/{order_id}/refund-settlements` | `GET /v1/orders/refund-settlements/{idempotency_key}` |

Recovery query parameters are the command's **original** workstation code and cash-session ID. The authorized actor and original context must still match; replay does not require that historical session to remain open. POS capabilities are `returns_corrections.manage` and `orders.cancel`, respectively. Operation codes are `return.refund_settle` and `order.refund_settle`.

The browser persists only recovery metadata and the original command identity. While a result is unresolved, another settlement identity is blocked. If a response is lost, use the displayed recovery action: it sends GET for the same key and original context, without a second POST. An in-memory retry, when available, retains the exact key and frozen body. After reload, the body is not reconstructed or silently resubmitted. A global POS recovery panel keeps an unresolved settlement visible even when its original document is no longer selected or its old cash session has closed.

Recovering an acknowledgement verifies the recorded result; it is not a second instruction to hand over the same physical cash. Verify the confirmed deliveries before handing over money again. A new explicit continuation is appropriate only after the preceding command has a known result and a remaining obligation still exists.

Each continuation records `financial_refund.settlement_recorded` audit metadata and a transactional `financial_refund.settlement_recorded.v1` outbox event. Operation, actual entries, audit, outbox and acknowledgement share the command transaction. A failure rolls them back together.

## External payments and remaining acceptance

An operator-recorded CARD collection is accounting evidence, not proof of a provider capture or an available bank refund reference. This refund flow never automatically declares a successful CARD OUT. The real BBVA adapter, merchant contract, terminal compatibility and production reconciliation remain separate acceptance requirements. Until a valid integrated path is enabled, unavailable external remainder stays explicitly pending.

The provider boundary may work only with eligible original captures and amounts that are neither already refunded nor reserved by unresolved attempts. Test adapters and controlled pending-leg fixtures are development evidence only. Technical compensations remain append-only; this block does not expose a generic manual financial reversal endpoint or automatically reopen commercial return rights.

Before operational acceptance, exercise partial and full cash refunds, source entitlement contention, distinct settlement keys on the same obligation, lost responses and reload recovery, a continuation in a later session, insufficient and missing-opening cash capacity, unresolved external reservation, rollback after a flushed financial effect, and matching POS/backoffice/cash-cut amounts. Live terminal and physical cash-handling acceptance must be performed separately.
