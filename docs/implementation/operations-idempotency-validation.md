# ZM-FIN-033–035 operational command validation

Branch: `codex/zm-fin-033-035-idempotency`.
Accepted base: `65c1cb92c8553ffe4e1ed1b799e32939d9fe5bfd`.

This block adopts the existing idempotency executor in the 23 existing commands
assigned to the remaining ZM-FIN-033–035 epic by DEC-07. It does not certify the
entire product for opening. Administrative identity/role, reconciliation and
settings gaps assigned to 077, 080 and 085 remain in the functional matrix.
Integrated acceptance requires the eight Foundation stages and `Foundation required`
on the delivered immutable commit. The commit and verified run accompany delivery.

## Existing commands adopted

| Family                         | Commands                                               | Count |
| ------------------------------ | ------------------------------------------------------ | ----: |
| POS transfers                  | Dispatch, receive                                      |     2 |
| Backoffice transfers           | Create, update, dispatch, receive, cancel              |     5 |
| Purchases                      | Create, update, direct entry, confirm, receive, cancel |     6 |
| POS operational documents      | Counter transfer, waste, correction                    |     3 |
| Backoffice physical operations | Waste, inventory adjustment                            |     2 |
| Production                     | Create, update, start, complete, cancel                |     5 |

Every mutation requires UUIDv7 `Idempotency-Key`; request correlation remains a
separate identifier. POS intentions also identify the original cash session.
The shared executor owns domain changes, audit, outbox and the minimized terminal
acknowledgement in one transaction. Same-key retries preserve the body and context;
changed bodies, resource IDs, actors or context cannot reuse the identity.
PATCH fingerprints distinguish omitted fields from explicit null.

Snapshots retain stable document, receipt, movement and line identities and the
quantities/state relevant to that result. They exclude notes, operator names,
supplier/customer display data and dynamic action permissions. Existing detail
GETs provide richer information separately; this does not remove business text
from existing audit/domain records.

Nine recovery GETs cover the seven module families and both transfer surfaces.
They require current authentication, current capability and the original context;
they do not reserve a key or execute a command. Successful recovery returns HTTP
200, including when the original creation returned 201. A missing/uncommitted
result remains unknown. Historical POS recovery is allowed with a valid new login
after the original shift closed; a new write against the closed shift is rejected.

Cash references are checked after authorization and before reservation for existence
and historical actor/station/branch ownership. This avoids foreign-key failures for
invalid cash IDs without requiring a historical shift to remain open. The action
still acquires the cash lock and rechecks OPEN before any new write. Transfer
corrections preserve all original participating branches in durable context;
replay/recovery revalidate those grants without consulting a mutable destination.

Purchase creation with `confirm_now` requires both `purchases.manage` and
`purchases.confirm`. Replay rechecks these permissions; recovery derives the
confirmation requirement from the immutable original acknowledgement, not the
document's mutable current state.

## Physical behavior and bounded concurrency

Transfers now support multiple immutable partial receipts against one shipment.
Receiving 2 of 5 leaves 3 pending and the shipment in transit; receiving the last
3 completes it. Backoffice ledger movements remove only the quantity actually
received from transit. Duplicate line identifiers and receipts above the remaining
quantity are rejected. Shipment locking serializes competing receipt/update paths.
POS history includes the shipment ID for each individual receipt and pending totals
represent the remaining quantity.

Purchase receipts lock the document and relevant balances, including safe first-row
creation under the unique balance constraint. Each receipt line flushes its stock
and supplier-price changes inside the command transaction before another line can
refresh the same product balance. Distinct lines for one product therefore accumulate
correctly and create at most one supplier-product relation. Production completion locks its batch
and inventory balances in product order. Corrections lock the target document and
account for committed deltas; an original shipment with receipts cannot be corrected
as if it were still unreceived. These are the protections needed by these commands;
the broader concurrency review remains ZM-FIN-036–038.

Existing physical boundaries remain explicit: POS counter transfers, waste and
transfers do not gain a new unified inventory ledger in this block. Full physical
unification remains 051/052. A return already assigned `SEND_TO_WASTE` is not converted
into a second manual waste event. Production still checks shortages at start and
consumes planned inputs at completion; reservations/WIP, frozen recipes and expanded
production costing remain later work (054/069). No migration is introduced.

## Browser behavior

POS and backoffice use the shared intention coordinator. Durable browser metadata
contains only context identifiers, command code, key, state and a body digest.
Bodies remain in memory. An uncertain same-page attempt may resend the same frozen
body/key; after reload the operator can only consult the existing result. A second
tab cannot silently replace an uncertain intention.

Changing the authenticated session or authorization version discards volatile bodies.
The same cleanup covers earlier sale, order, return and cash adopters of the shared
coordinator. The coordinator also
checks an invalidation epoch across asynchronous lock/digest boundaries, preventing
an old intention from being sent under a new login. A late response from the old
session remains recoverable as unknown and is not delivered as a new-session result.

Transfer creation and dispatch are separate explicit actions. Production's optional
create-then-start flow uses two identities and checks current ownership between
steps. Losing either response never silently recreates the initial document.
Purchase forms retain editable fields after a known business rejection; confirmed
intentions close the form and refresh the separately queried document details.

Real-browser tests submit through the UI where available, allow the real API
transaction to finish, discard its successful response, then reload and recover
the exact acknowledgement. The fault helper permits only the enumerated local
operational command routes. It does not fabricate successful API responses.

## Validation record

All PostgreSQL validation uses the guarded disposable database runner; the normal
development database is not used. Published logs/JUnit pass the protected evidence
boundary to remove session credentials. Source and generated-contract hashes bind
the eventual Foundation evidence to the delivered commit.

Initial purchase acceptance exposed an authorization guard rejecting a Core INSERT
for first balance creation (18 passed, 13 failed). The implementation was corrected
to use authorized ORM writes with a savepoint and the existing unique constraint;
the next complete run passed all 31 cases. Further permission cases and integrated
results are recorded below after validation. The initial failed run is diagnostic
evidence and is not represented as a passing suite.

| Validation                                                                    | Executed result                                                                                                                |
| ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Purchases, complete PostgreSQL suite including repeated-product receipts      | 40 passed                                                                                                                      |
| Missing purchase branches and existing shared callers                         | 7 passed in a separate run                                                                                                     |
| Transfers, expanded PostgreSQL coverage across dedicated and existing callers | 54 passed across final scoped runs                                                                                             |
| Shared historical cash-context authorization                                  | 5 passed                                                                                                                       |
| Production, expanded PostgreSQL suite                                         | 48 passed; additional missing-branch case passed separately                                                                    |
| Physical commands, PostgreSQL                                                 | 49 passed; two corrected related-branch audit assertions passed separately                                                     |
| Purchases web tests including existing components                             | 18 passed                                                                                                                      |
| Production API/coordinator web tests                                          | 16 passed                                                                                                                      |
| Physical command web tests                                                    | 59 passed                                                                                                                      |
| Shared coordinator/API-client tests                                           | 27 passed                                                                                                                      |
| Local fault-injection helper tests                                            | 15 passed                                                                                                                      |
| Published API contract and functional-matrix tests                            | 100 passed; contract generation and matrix checks passed                                                                       |
| Integrated Web                                                                | Lint, typecheck, 719 unit tests, builds and 11 mocked-browser scenarios passed                                                 |
| Integrated real Browser                                                       | 19 passed: eight POS and eleven Backoffice scenarios                                                                           |
| Delivered Foundation CI                                                       | All eight stages and the required aggregate must pass on the delivered immutable commit; its verified run accompanies delivery |

The first integrated Web run passed lint/typecheck and the collected unit cases,
but one corrections screen suite could not collect because its old auth mock
lacked the new subscription API. The mock was corrected and its five screen cases
passed separately. The first Browser run timed out in the existing multi-step cash
scenario, leaving an open session that caused the next fixture assumption to fail;
another new scenario omitted the mandatory note for damaged waste and correctly
received 400. That fixture now supplies the required note. These diagnostic runs
are retained separately from subsequent complete acceptance.

The next Browser run passed all eight POS scenarios. Administrative acceptance
exposed four test selectors that matched wrapped select labels too narrowly and
an existing order fixture that exhausted the shared cashier's login budget.
The selectors now match the named combobox within its form; administrative order
setup has a separate disposable cashier and workstation. Production authentication
limits remain unchanged. Those failures are retained as diagnostic evidence.

A subsequent run passed production and purchases but exposed a real initial-value
problem when forms opened before their option queries completed: the browser
displayed a default option while React still held an empty value, so submission
stopped before sending a request. The affected forms now resolve still-empty
defaults when options arrive and preserve explicit selections. Focused regressions
cover delayed options and refreshes; real-browser acceptance is recorded above. Two existing POS component cases also
needed to await observable asynchronous completion before cleanup; the final full
Web run passed all 719 unit cases and all 11 mocked-browser scenarios.

Final independent review found a repeated-product purchase regression: with
autoflush disabled, refreshing the balance for a second receipt line discarded the
first line's pending increment. A missing supplier-product relation could also be
added twice. Four PostgreSQL regressions reproduced both failures for direct entry
and ordinary receipt before the fix. Flushing each completed line inside the same
command transaction corrected both cases; the complete 40-case purchase suite then
passed, including exact replay/recovery without additional effects.

The first hosted Web stage exposed the same premature asynchronous assertion in
the POS shipment component test. Shipment and receipt tests now await observable
success and completed mutations before cleanup. Their ten focused cases and the
repeated full Web stage passed (719 unit cases and 11 mocked-browser scenarios).
Hosted acceptance still requires the delivered immutable commit.

Reproducible entry points (with the pinned toolchain activated):

```powershell
corepack pnpm contracts:generate
corepack pnpm contracts:check
uv run --frozen python scripts/dev/check-functional-operation-matrix.py
pwsh -NoProfile -File scripts/dev/check-foundation.ps1 -Stage Contracts
pwsh -NoProfile -File scripts/dev/check-foundation.ps1 -Stage Web
pwsh -NoProfile -File scripts/dev/check-foundation.ps1 -Stage Browser
```

Run Python suites through `run-api-tests.ps1` and capture execution with
`Invoke-ZeroMermaProtectedValidationProcess`. Publish only the output of
`Protect-ZeroMermaValidationArtifacts`, not raw failure logs or runtime TLS files.
The next planned task after acceptance is ZM-FIN-036, the first broader concurrency
task; it is not another command-adoption block.
