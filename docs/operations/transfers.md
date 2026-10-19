# Physical transfers

ZM-FIN-052 uses one backend physical workflow for POS and backoffice. This document describes the development implementation, not production acceptance.

## Quantities and custody

Dispatch removes available stock from the origin `BACKROOM` and records the same quantity in the destination `IN_TRANSIT`. A receipt removes only the quantity actually received from transit and adds it to destination `BACKROOM`. Partial receipt leaves the remainder in transit. Outstanding quantity is sent minus cumulative receipts, physical returns, and waste dispositions.

A draft can be cancelled without a stock effect. After dispatch, cancellation alone cannot erase transit stock. An explicit `RETURN_TO_ORIGIN` resolution requires actual arrival at origin and records its chosen `BACKROOM` or `QUARANTINE` destination. The UI defaults to quarantine. `SEND_TO_WASTE` requires actual custody at the destination and moves the damaged quantity into `WASTE`. Unlocated missing goods remain in transit; neither resolution claims a missing item has physically arrived.

Both branches must be authorized for `transfers.execute`, plus `transfers.cancel` for a return or `waste.manage` for waste. POS additionally uses the current workstation, open cash session, and actual physical branch. Backoffice does not fabricate a workstation.

## Lots and valuation

Dispatch selects eligible stock through the core FEFO allocator. Paired movements retain the original lot IDs, expiry dates, and quantities. When a partial receipt or resolution could refer to more than one remaining lot, the operator must identify the actual quantities per lot. Receiving the entire remainder or a quantity from the only remaining lot is unambiguous. Expired stock cannot be received into saleable storage; an actual return can use quarantine without inventing a new lot or expiry.

The origin's applied weighted average cost is frozen in the dispatch evidence. Receipts and resolutions preserve that value rather than reading the current product standard cost. Partial quantities allocate the original value proportionally at eight decimal places; the last quantity carries the exact remaining value. Unknown source value stays unavailable. A historical documentary shipment without canonical physical dispatch evidence cannot consume another shipment's pooled transit stock.

## Atomicity and recovery

Document progress, inventory effects, immutable resolution records, audit and outbox share the admitted command transaction. Shipment and ordered inventory locks serialize competing receipts and resolutions. Replay returns the stored acknowledgement without another physical effect.

Resolution command identities are `transfer.resolve_return` and `transfer.resolve_waste`. Their distinct identities preserve the required capability on recovery. Both UI surfaces keep the existing intention coordinator: an uncertain command retains its key and frozen request in memory; reload retains only recovery metadata. After reload, consult the saved confirmation with GET. Never submit a fresh resolution merely because the original response was lost.

## Acceptance checks

Validate full and partial receipt, return to both permitted origin locations, waste under destination custody, explicit multi-lot receipt, expired-lot quarantine, concurrent exhaustion, insufficient available stock, unchanged cost after a master-price update, exact final cost remainder, atomic audit/outbox failure, and lost-response recovery. POS and backoffice must report the same sent, received, returned, waste and outstanding quantities.
