# ZM-FIN-048–055 inventory implementation and validation

Branch: `codex/zm-fin-048-055-inventory`.
Accepted base: `c7d05140b096959f741b29e5524f7638c9ef5fdf`.
Status: implementation and the focused validations below are complete. Delivery
acceptance requires all eight Foundation stages plus the aggregate check to pass
for the exact delivered commit, with clean checkout and verified artifact hashes.
That run is identified in the delivery report; earlier Foundation acceptance is
not evidence for this implementation. No normal local database has been migrated.

## Implemented boundaries

| Task | Canonical implementation |
|---|---|
|048|Immutable causal stock movements, exact base quantities/conversion snapshots, aggregate and lot balances, reservations/events, sorted locking, weighted average value and FEFO selection. Unknown costs remain unavailable.|
|049|Direct confirmation debits COUNTER in the financial transaction. Lost acknowledgements/replay do not debit again. Catalog availability excludes reserved, expired and unidentified goods; backend locks arbitrate concurrent sales.|
|050|Class capture creates an obligation per sale line. Partial ticket attribution, return attribution and closing consume only its remaining quantity. Historical eligibility cannot use later receipts to explain an earlier sale. Physical close captures exact lot counts and immutable history. Backoffice lists tickets with pending attribution and reports each line's attributed quantity, remainder and actual product/movement history.|
|051|Economic return entitlement is separate from physical allocations. Split restock/quarantine/waste share one refund. Restock needs explicit inspection and eligible original lots. Physical compensation preserves refund facts and entitlement. Waste/counter movements and corrections use the same ledger.|
|052|Dispatch creates documentary transit; partial receipt and explicit return/waste resolution are bounded by that dispatch's remaining goods/lots/value. No generic transit adjustment or post-dispatch destination rewrite.|
|053|Purchase confirmation creates no stock. Actual receipts freeze unit/conversion/value/lot evidence; partial receipts and bounded compensations preserve causal history. Supplier/invoice identity is unique.|
|054|Release freezes recipe/input evidence and reserves FEFO stock. Completion consumes actual inputs and records output/waste; cancellation releases unused reservations. Unreconciled actual execution is preserved without fabricated WIP or stock movements.|
|055|Read-only diagnosis and dry-run; reviewed manifest-driven opening/rebuild commands with hashes, idempotency, immutable evidence and explicit real-source authority. Demo history cannot silently become production inventory.|

READY order reservations and delivery/cancellation effects adopt this same stock
boundary. Further commercial order states remain in their own later task.

## Contracts and migration

One chain follows 0048: 0049 inventory core, 0050 reconstruction evidence, 0051 class
attribution/normalized return allocations/close lot counts, 0052 transit resolution,
0053 purchase and production evidence. Downgrade guards reject loss of physical
facts. 0051 rejects ambiguous historic normalized returns or already-reconciled
class sales rather than fabricating per-sale allocations. Old active production
is explicitly pending reconciliation. Use clean approved adoption or validated
restore/roll-forward; these changes are not a production cutover.

Backend OpenAPI generates the TypeScript client. POS provides lot-aware returns,
physical counts, partial class attribution and transfer resolution. Backoffice
provides product policies, purchase receipts, production execution, physical
return correction and quarantine release. Command retries preserve the original
body/key; reload recovery uses GET and does not silently submit a new operation.

## Verified focused evidence

All PostgreSQL runs use guarded disposable databases. Evidence paths below are
relative to `.tmp/validation-published`; failed diagnostic runs are not acceptance.

| Verification | Actual result |
|---|---|
|Purchases/production five-module regression|99/99; `operation-context/purchase-production-053-054-final/2be4e25e12aa47ec995fe9340775c54d/operation-context.xml`.|
|Migration module|30/30; run `a78c671c2ced40a7a22757f09a07a420`, including 53 checkpoints, fresh metadata parity, five new guards, rollback and dump/restore.|
|Ticket temporal attribution with/without lots|2/2; run `c6f24a9a42494474a54794dd5b64a1f1`: later receipts excluded, partial attribution/replay conserved, excess rejected.|
|Administrative pending attribution report|4/4 PostgreSQL cases in `operation-context/inventory-admin-attribution-report-final/508cdcb91a9a42abbd2991e1541f9e23/operation-context.xml`: lot/nonlot pending, partial and completed reports, plus both POS temporal-projection regressions after extracting the shared progress reader. The 10 focused UI tests, Backoffice typecheck and build pass.|
|Sales, returns and close physical regression|16/16; `operation-context/inventory-final-physical/43e1618d7df447fa8fb33013329f5c11/operation-context.xml`, including historical lot counts, explicit waste-lot selection and compensation, partial return value, post-sale receipt exclusion and rejected effects.|
|Temporal closing and cross-lot rounding|The three new cases pass in `physical-temporal/697dc8bda0df4ae6b536e38622654ae8`: closing skips later receipts with earlier expiry, pending unflushed effects reduce historical capacity, and three fractional lot returns conserve the original value exactly. Two unrelated legacy scope expectations from that diagnostic run were corrected and passed in `physical-scope-final/6548930b730b45b5b2c0ef5e799fcba9`.|
|Returns and refund regression|71/71 across four modules; run `aad170987162470da02bc88e53a15eb3`. A purchase reversal also passed; a separate catalog expectation in that diagnostic run was corrected from 400 to 409. The final catalog assertion and dependent-module batch were still running at this evidence checkpoint; the delivered-commit Backend stage includes them.|
|Expired reserved production stock|2/2; run `80ba0873e08c432999cc399004b833c6`: usable consumption rejects expired stock, explicit production waste consumes the same reserved lot once, and the UOM history guard remains enforced.|
|Opening and reconstruction (055)|11 selected reconciliation cases pass in `inventory-core/83576029c9b5469a8950358a01eacf5c/result.xml`: read-only diagnosis, opening, reconstruction, interrupted execution/resumption, and rejected demo/unauthorized evidence. The lot reconstruction/stale-hash case also passes in `inventory-core/6cf005066efb43669692d45a9d5ab151/result.xml`. These are selected successful cases from mixed diagnostic runs, not acceptance of either entire run.|
|Real POS browser workflows|8/8; run `bc7f8ca7cac1428c8e661049ad95e284`, including partial class attribution and split return/quarantine disposal with lost acknowledgements and GET recovery. Backoffice in this diagnostic run was 9/11; two stale quantity/movement assertions were corrected and await the full delivered-commit run.|
|POS close model/components|27/27, including exact fractional lot counts retained through synchronization and request serialization.|
|Transfer completion scope|Final destination waste and partial-waste/final-receipt scenarios pass 2/2 in `inventory-transfer-destination-completion-final/23d8b448631947b0aa9269d1156427b0`. Wrong-workstation attempts retain their security audit without business effects; completion retains the original shipment identity and requires current transaction evidence.|
|Web unit tests and builds|775 unit tests pass (POS 425, Backoffice 312, API client 35, UI 3), and both application builds pass. The corrected mock operational regression passes 3/3. Hosted acceptance remains separate.|
|Generated contracts|274 operations, 274 generated client entries, no orphan operations, unjustified raw HTTP calls or handwritten domain contracts; `corepack pnpm contracts:check` passes without source writes.|
|Python static analysis|Ruff passes; mypy passes 416 API/worker source files at this checkpoint.|

The focused evidence above is a source-freeze checkpoint, not a replacement for
the complete Backend and Browser suites. The block is accepted only when the
delivery report identifies the successful exact-commit Foundation run and its
verified artifacts. An unsuccessful or incomplete run leaves acceptance pending.

The Backend CI stage has a 90-minute limit; all other stages retain 60 minutes.
The accepted baseline already required approximately 54 minutes for Backend.
The additional physical, lot, reservation and valuation cases run in the same
mandatory suite; no check is skipped to meet the former timeout.

## Operational policy

Enable lot tracking/required expiry only for the reviewed product catalog. Record
actual source lot and expiry on incoming goods; production output has its own lot.
No shelf life is inferred. The application records lot selection, but staff must
label and physically pick the corresponding goods; it cannot verify shelf layout.

At close, count each retained lot. A class sale may consume only an eligible lot
deficit; it cannot consume a lot that the operator counted as still present.
Mixed increases/decreases between lots require an explicit reviewed adjustment
before closing. Expiry does not automatically erase stock or generate waste.
Record the actual discarded lot and reason. Quarantine is physical inventory
excluded from usable availability; release requires inspection and eligible identity.

The owner has not yet supplied the product enrollment or shelf-life catalog.
The software supports explicit per-lot evidence without assuming either.
Deployment, opening counts, labels, staff training, backups and business acceptance
remain separate from synthetic validation. See
[opening/reconstruction](../operations/inventory-reconciliation.md) and
[transfers](../operations/transfers.md).
