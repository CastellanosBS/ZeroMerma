# ZM-FIN-056–067 POS implementation and validation

Branch: `codex/zm-fin-056-067-pos`.
Accepted base: `c562dcfe8a6f04d1c9e76d11706baa8d95629f20`.

Status: implementation and focused verification are in progress. This block is
not fully complete: digital delivery, a documented BBVA integration and physical
device acceptance have unresolved dependencies. No normal development database
has been migrated. PostgreSQL validation uses guarded disposable databases.
Acceptance of the delivered software requires the eight Foundation stages and
aggregate check for the exact delivered commit, clean checkout and verified
artifact hashes. Focused results do not replace that acceptance.

## Implemented scope and remaining boundaries

| Task | Current implementation | Remaining acceptance boundary |
|---|---|---|
|056|Sale confirmation requires the displayed unit price and currency; pricing rows remain locked through commit. Empty, duplicate, invalid, unavailable or insufficient-stock lines are rejected by the canonical backend. Price conflict allows explicit catalog refresh, removal of unavailable items and a new review without automatic resubmission.|Full regression and real browser evidence for the delivered commit.|
|057|Cash, separately charged card registration and mixed payments use exact amounts. Excess cash produces change; excess card cannot become change. Confirmation is bound to the reviewed cart; edits invalidate payment confirmation. Submission and uncertain results freeze edits until canonical recovery. Original command identity survives lost acknowledgements and reload uses read-only recovery.|Integrated provider states remain in 065; manual registration is not BBVA authorization. Changing the cart does not correct an already completed external charge.|
|058|Explicit versioned branch policy, backend quotations, minimum 50% deposit, immutable order revisions and production commitment, intermediate payments, bounded amendments and explicit cancellation responsibility. READY reserves stock through the existing FEFO boundary; delivery requires full settlement. POS and Backoffice expose the applicable controls.|The owner must choose the commitment lead time; there is no runtime default. Legacy orders without policy evidence remain explicitly unsupported for new lifecycle commands.|
|059|Immutable sale/payment/return receipts are written in the economic transaction. Reprint preserves the original document and never changes economics. Return settlement-at-issuance and current pending obligations are separate. Browser print records a request and cannot confirm physical output.|Real merchant identity/address configuration and printed samples on the selected equipment. Historic rows with no receipt snapshot are not fabricated from current data.|
|060|Unavailable controls remain truthful; no recipient is collected or message sent.|Approved transactional channel/provider and privacy boundary 128, plus worker delivery handlers 073–076. No provider or consent is invented.|
|061|Existing canonical opening, ledger movements and close are retained. Pending/processing/unknown financial entries already block close through the shared financial projection. Readiness and accessibility improvements apply to these screens.|Regression of same-turn and later-turn order effects, close races and physical counting.|
|062|Existing source-bound return quantities, explicit physical disposition and canonical cash-first refund obligations are retained. Receipt printing uses the frozen issuance document.|Regression of partial refund, insufficient cash, replay and recovery; external refunds remain provider-dependent.|
|063|Existing causal dispatch, partial receipt, return/waste resolution and command recovery are retained. Modal keyboard behavior and connectivity admission apply to operations.|Regression of split receipt/disposition and lost acknowledgements.|
|064|Verified device bindings, signed structured commands, causal job identities and an independent local durable spool are implemented. Cash drawer commands require a confirmed cash cause. No uncertified device is enabled by default.|Exact printer/drawer/OS/connection, a real adapter, installation and update packaging, pairing provisioning and physical acceptance. Kernel test adapters are not runtime integrations.|
|065|The existing financial/provider boundary remains separate from manual card registration; the checkout explains that the cashier must first confirm payment on the separate terminal.|BBVA terminal model, technical contract/sandbox, approved data flow and a pre-sale integrated payment intention wired to confirmation. Existing terminal APIs alone do not supply that missing checkout flow.|
|066|Bounded local API/PostgreSQL readiness, workstation-visible connection state, business-command admission, finite request timeout and read-only reconnection. Browser Internet hints do not block a healthy LAN; no browser offline financial queue.|Local-first installation, trusted LAN TLS and real network/restore drills remain operational prerequisites.|
|067|Modal focus containment/restoration, isolated keyboard shortcuts, responsive layouts, translated operational states and auth-boundary notice cleanup. Existing 30-minute inactivity policy is preserved.|Actual target touch/keyboard/printer devices and final user acceptance. Automated viewport checks do not certify physical equipment.|

## Migration and contract changes

The single migration chain adds 0054 immutable receipt snapshots, 0055 versioned
order policy/revisions/commitments and 0056 hardware bindings/command intentions.
Downgrade guards preserve issued or executed facts. There is no fabricated
historical receipt or policy backfill. API and both web applications must be
deployed together because sales now require expected price/currency and orders
require a current quotation and explicit cancellation responsibility.

OpenAPI remains the source of the generated TypeScript contract. Receipt amounts
and order amounts are backend-derived. Hardware success, browser print requests
and payment provider approval are distinct outcomes.

## Focused verified evidence

Paths below are relative to `.tmp/validation-published`. These runs used a dirty
working tree at the accepted base commit; they are evidence for the focused
implementation, not final hosted acceptance.

| Verification | Observed result |
|---|---|
|Sale price/currency/input/mixed payment contract|9/9, `operation-context/pos-checkout-fixed/98cabcfbcacd4e97aaa6c438abf880e2/operation-context.xml`. Earlier diagnostic failed on test error-envelope expectations; corrected run is the evidence.|
|Checkout price-review UI|15/15 Vitest, including Escape, inactive product removal, explicit refreshed-price review and no automatic sale resubmission.|
|Checkout confirmation and draft locking|42/42 focused tests after review found a stale card-confirmation path. Quantity changes require renewed confirmation; an old handler cannot submit a new total; submission/UNKNOWN lock mutations and canonical recovery releases the lock. A separate zero-price refresh case also passed.|
|Order lifecycle and database clock|9/9, `operation-context/pos-order-db-clock/83205229f8e8481abe8e3324865f5050/operation-context.xml`, including exact policy acknowledgement recovery, immutable evidence, cutoff boundary, stale revision, changed catalog price and an incorrect application clock. Decision time comes from PostgreSQL after locking the order.|
|Existing order regression|The broad run passed 84/86; its two failures were outdated READY/cancellation expectations. Corrected cases and delivery-income evidence passed 3/3 in `operation-context/pos-order-final-assertions/764fdd755fbf40bdaf38e1560d1ad049`. The delivered-commit Backend stage remains the complete regression boundary.|
|Local readiness|5/5, run `0f1bbdee6d4549368ca5198c52b429a7`, including the real PostgreSQL probe.|
|Connectivity/accessibility browser scenarios|5/5: 800×600, 1366×768, 1920×1080, healthy LAN with browser offline hint, database loss and reconnection without repeated POST.|
|Administrative orders|4/4, `operation-context/pos-admin-orders/affd97ee559145eabceeaf07736294d4`; cancellation responsibility/reason and configured policy are explicit.|
|Administrative controls|9/9 cancellation tests and 4/4 policy intention tests.|
|Receipt/hardware API|15/15, `operation-context/pos-receipts-hardware-059-064-r3/4b4c6067b0c7430699b8b7aac5d310e5/operation-context.xml`; frozen receipts, source authorization and original-job recovery. This uses controlled test registrations, not physical certification.|
|Local device kernel|17/17 unit cases, including signed authority, binding, durable deduplication, FIFO and ambiguous physical outcomes.|
|Migration focus|9/9 across runs `3b2ef5f93e6b4a4b8005691c3a905a83` and `3d0f443cd9da40688dcfd0712113e0b0`: historical preservation, immutable/downgrade guards, one head, fresh schema parity and negative classifiers. Head 0056 has 56 revisions and 269 reviewed checks; no new parity exception hides a mismatch.|
|Web stage diagnostic|Full Web stage passed, run `3eaee6b17b4b48e1959a5c736475a6e4`: lint, typecheck, unit tests, both builds and 16 mocked browser scenarios. Later hardware recovery and final order timezone changes still require the delivered-commit run.|
|Real browser integration|19/19 (8 POS and 11 Backoffice), isolated database run `5ea40d3ac967460fb67f7518d1ed3399`, Foundation Browser run `1e87d0dfdf22413185f78478a8f1531d`. Includes mixed tender/change, lost acknowledgements, order amendment, partial refunds and administrative recovery. The earlier 7/8 diagnostic exposed two outdated return fixtures; the corrected run is the evidence.|
|Cash, order and refund regression|60/60, `operation-context/pos-orders-cash-boundary-fixed/09bf5f28bfe84081b684e3c5988e9634`. This run precedes the final PostgreSQL order-clock change; final Foundation acceptance also covers that change.|
|Receipt and hardware web controls|24/24 across seven Vitest files, including original-job recovery and browser print limitations.|
|Static Python typing|439 source files passed after the final hardware recovery and PostgreSQL order-clock changes; repository-wide Ruff also passed. Final Foundation result remains required.|
|Contracts and operation registry|Foundation Contracts passed, run `9c3f608495eb47229f237cb889951b76`: 112 tests; 287 generated API operations; zero unknown operations, unjustified raw API calls or handwritten contract types.|
|Validation evidence publication|15 existing Foundation/publication tests passed after adding an optional migration JUnit report. The earlier full migration diagnostic failed without individual published cases; focused corrections passed, but only the final full run can resolve that diagnostic.|

Hosted run `39331588486` for commit `f2923a3` passed the full migration suite
(34/34), Contracts, Worker, Preflight, Negative and the 19 real browser scenarios.
This resolves the earlier incomplete migration diagnostic. Web exposed three stale
authentication mocks in the return-screen tests; the mock now follows the actual
optional-selector/getState API, with 17 related tests passing. That run is diagnostic,
not final acceptance: the corrected commit must pass the complete Foundation workflow.
The corrected full local Web stage passed in run `c65704e8d8cb4bc0912db7e70aede658`,
including lint, TypeScript, all unit tests, both builds and 16 mocked browser scenarios.

Hosted run `39332464705` passed Web and the full migration suite, but exposed a race
in the browser fault-injection harness: its committed-result promise settled before
the simulated connection abort completed. Five deferred-abort cases reproduced the
race and passed after the helper fix (23/23 total). Administrative recovery also
waits for UNKNOWN and an enabled recovery action before reload. These changes affect
the validation harness only and retain all economic-effect and duplicate checks.
The corrected full Browser stage passed 19/19 in isolated run
`27ee28facc924ff2b353088b3c4f4f06`, Foundation run `fd98120ac20d451c98662571fc818535`.

## Operational information still needed

1. Choose the branch production commitment lead time. The Backoffice form accepts
   an explicit duration and reason; test-only 1440-minute fixtures are not a business
   decision or a production default.
2. Provide the BBVA terminal model and availability of its technical documentation
   and sandbox. Do not put credentials in chat. Manual separate-terminal charging
   remains the previously authorized fallback.
3. Identify the purchased computer OS, printer and drawer models and connections.
   Physical printing/opening cannot be validated against an unspecified device.
4. Choose transactional digital delivery channel/provider and the applicable
   privacy notice, or explicitly postpone digital tickets. The software currently
   sends no digital tickets.

This record does not declare Feature Complete, Pilot Ready or Production Ready.

Operational procedures are in [checkout and orders](../operations/pos-checkout-and-orders.md),
[connectivity and accessibility](../operations/pos-continuity-and-accessibility.md)
and [local hardware](../operations/local-hardware.md). The loopback transport omits
API cookies and accepts only backend-signed commands using generated Python-owned
models. The contract guard rejects another origin, credential mode, extra fetch
or a manually substituted result model; it does not permit feature-level API fetch.
