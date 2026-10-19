# Inventory opening and reconstruction

This workflow implements technical controls for ZM-FIN-055. It does not certify a
production physical count, an owner's signature, restored backups, or a completed
cutover. The known `PG-ZM-CURRENT` and `PG-ZM-LEGACY` volumes remain development,
demo and test evidence. Their balances must not become production opening stock.

Inventory uses exact base quantities with three decimal places. Incoming
documents freeze their original unit, conversion factor and base quantity.
Weighted average valuation is independent for each branch/product/location.
Known inbound value changes the weighted basis; ordinary outgoing stock takes
that basis and freezes its applied cost. Missing cost propagates `UNAVAILABLE`,
not a fabricated zero. Empty stock resets its value to zero. Paired physical
transfers retain the source effect's quantity, total value and lot identity.

FEFO chooses physical lots by earliest expiry, then stable lot identity. Selling,
using or reserving excludes expired and unidentified lots. Reserved consumption
rechecks the original lots; expiration requires an explicit resolution. An
expired reserved production input can be reconciled as explicit waste from its
original lot; it cannot be consumed as usable input or silently replaced by a
fresh lot. An
unidentified return may enter quarantine without inventing an expiry or original
lot. It cannot be released into usable stock by changing its identity.

## Diagnose and review

Run the existing project toolchain with approved database credentials supplied
through the environment. Never put passwords or database URLs in the command
line or an evidence manifest. These commands use PostgreSQL read-only repeatable
read transactions:

```powershell
uv run --frozen python scripts/dev/inventory-reconciliation.py diagnose --branch-id BRANCH_UUID
uv run --frozen python scripts/dev/inventory-reconciliation.py dry-run --manifest reviewed-inventory.json
```

Diagnosis compares aggregate and lot projections to immutable movement and
reservation events. It reports negative stock, incompatible units, unclassified
historical causes, missing history, quantities, reserved quantities, availability,
valuation status and a ledger hash per physical key. It never creates missing
history. A balance without complete causal history requires manual reconciliation;
it is not sufficient evidence for a rebuild or an opening.

Prepare a versioned manifest containing:

- `manifest_id`, `branch_id`, `source_id`, `source_classification` and the source
  evidence SHA-256. Productive authority requires `REAL_OPERATIONAL`; known demo
  volume identifiers remain rejected even with that classification.
- `approval_reference`, `approval_evidence_sha256`, `controlled_window_reference`,
  timezone-aware `cutover_at`, `expected_row_count` and `rows`.
- Every row: unique `row_key`, stable UUIDv7 `idempotency_key`, `action`, product,
  location, base UOM, physical evidence reference/hash and an explicit reason.
- `OPENING`: exact decimal-string `quantity`, optional evidenced
  `inventory_value`, and lot entries (`lot_code`, `expires_at`, exact quantity)
  for controlled products. Each opening targets an empty key. Zero opening is
  recorded as evidence without creating a zero movement. A missing value stays
  unavailable. Lot sums must reconcile to the count; required expiry is explicit.
- `REBUILD`: `expected_ledger_sha256` from diagnosis. Omit quantity, value and lots;
  they are derived from unchanged canonical evidence. Rebuild corrects materialized
  aggregate and lot projections, preserving all original movement/event records.

Each key, row and idempotency key appears only once in a manifest. Review the
source and approval documents externally: a reference or hash is an operator
declaration, not proof of authenticity. Reports explicitly set
`approval_authenticity_verified=false` and `production_reconciliation_signed=false`.

## Apply in a controlled window

Take and test a recoverable backup, reconcile open operations, close cash sessions,
stop operational writers and confirm the physical count at cutover. Test the exact
manifest against a restored isolated copy first. Review the dry-run differences
and save its exact `manifest_sha256`.

```powershell
uv run --frozen python scripts/dev/inventory-reconciliation.py apply --manifest reviewed-inventory.json --expected-manifest-sha256 REVIEWED_SHA256 --controlled-window-confirmed
```

The CLI prompts for the owner email and uses a hidden password prompt. The service
refreshes authoritative Backoffice authorization and requires the designated
superadministrator with `inventory.adjust` and global scope. It rejects active
cash sessions and inactive branches. Keys are locked in canonical order and the
reviewed ledger hash is checked again under that lock. The operator's maintenance
window remains necessary to keep unrelated rows stable between resumable commands.

Each row is one admitted idempotent transaction containing its inventory effect
or rebuild, immutable manifest/progress evidence, before/after comparison, audit
and outbox. A failure rolls back the current row; completed rows remain durable.
Repeat the identical command or select `--row-key KEY` to resume. Preserve the
manifest and original UUIDv7 keys. An admitted manifest cannot be edited; a new
correction needs a separately reviewed manifest and explicit reason.

After application, run diagnosis again, compare quantity/value and lot/reservation
projections, retain the manifest, output, external signed count and approval, and
only then reopen operations. Partial compensation must reference the original
movement and original lots; cumulative compensation cannot exceed original
quantity or value. Original records are never rewritten or deleted.

## Roll-forward and restore

Migrations 0049 and 0050 refuse destructive downgrade when canonical stock,
reservation, lot or reconciliation evidence would be lost. Use a reviewed forward
correction or restore a separately validated backup during a controlled window.
Synthetic automated tests demonstrate mechanics only; an actual production
restore drill and signed reconciliation remain operational release evidence.
