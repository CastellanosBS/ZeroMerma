# Financial diagnosis and controlled imports

ZM-FIN-047 implements read-only diagnosis, dry runs and evidence-gated financial
transformations. DEC-19 classifies `PG-ZM-CURRENT` and `PG-ZM-LEGACY` as
`DEVELOPMENT_DEMO_TEST`; neither source may become productive financial history.
There is no presently approved external legacy source to import. Acceptance uses
synthetic evidence on disposable PostgreSQL, not a signed production reconciliation.

## Authority and supported transformations

The money authority is `closed_and_reconcilable_economic_evidence`. An operator must
retain the source evidence, classification, reviewed manifest, approval evidence,
controlled maintenance-window reference and a verified full-database backup.
Unknown or conflicting evidence requires manual reconciliation.

- `OPENING_ADJUSTMENT` creates an explicitly identified `OPENING_STATE` operation.
  `OPENING_OBLIGATION` represents a positive receivable, payable or customer advance
  without creating cash entries. `CASH_OPENING` must match an actual existing OPEN
  session's fund, workstation and opening time; that session must have no previous
  canonical opening. A zero fund has an operation and no zero entry.
- `BACKFILL` adopts an already persisted, causally verified source. Supported sources
  are confirmed sales and their payment legs, committed operating payments/charges,
  and actual order ADVANCE/SETTLEMENT receipts. IDs, amounts, methods, tender/change,
  timestamps, currency, branch, workstation and session must match exactly.
- `MANUAL_RECONCILIATION` and `ARCHIVE_READ_ONLY` are diagnostic dispositions. They
  cannot be automatically applied. Unsupported historical refund/provider sources
  require manual reconciliation; no generic historical transaction is fabricated.

All monetary values use exact Decimal cents in MXN. CARD backfill is an explicit
ACCOUNTING_ONLY external recording, never a claim of bank capture. Original sales,
receipts, sessions, legacy cash movements and approved closes are not rewritten.
Closed or CLOSING sessions reject new imported financial effects, including CARD.
Future sources require classification and review before staging or transformation.

## Manifest contract

The strict JSON schema is defined by
`apps/api/src/zeromerma_api/modules/financial_ledger/domain/reconciliation.py`.
Unknown fields, floating-point monetary JSON numbers, repeated row/command/cause
identities, inconsistent counts/totals and naive timestamps are rejected.

| Manifest fields | Meaning |
| --- | --- |
| `manifest_id`, `branch_id` | Stable UUIDs for this reviewed batch and its branch. |
| `source_id`, `source_classification` | Named source; classification is REAL_OPERATIONAL, DEVELOPMENT_DEMO_TEST or UNKNOWN. Only REAL_OPERATIONAL can apply. Known local demo identifiers remain prohibited even if relabelled. |
| `source_authority` | Exactly `closed_and_reconcilable_economic_evidence`. |
| `source_evidence_sha256` | Lowercase SHA-256 reference to retained original evidence. |
| `approval_reference`, `approval_evidence_sha256` | Reference and SHA-256 of separately retained approval evidence. |
| `controlled_window_reference`, `cutover_at` | Reviewed maintenance window and timezone-aware cutover timestamp. |
| `expected_row_count`, `expected_amount_due` | Exact row count and sum of row obligations; total is a decimal string. |
| `rows` | Between 1 and 1,000 immutable row descriptions. |

Each row requires `row_key`, a stable UUIDv7 `idempotency_key`, `treatment`, `kind`,
`source_type`, `source_id`, `subject_type`, `subject_id`, decimal-string `amount_due`,
timezone-aware `occurred_at`, `evidence_reference`, `evidence_sha256`, and `reason_code`.
`currency_code` is MXN. `workstation_id` and `cash_session_id` identify actual cash
scope and are absent for an opening obligation. Opening obligations additionally
require `opening_obligation_kind` RECEIVABLE, PAYABLE or CUSTOMER_ADVANCE.

Opening rows use `source_type=OPENING_STATE` and `source_id=evidence_reference`.
Their subject is CASH_SESSION for cash, ORDER for a known order obligation, or
OPENING_BALANCE for a separately identified receivable/payable. The same economic
subject cannot receive duplicate opening obligations of the same class.

`legs` contains actual positive entries with `leg_key`, `payment_method` CASH/CARD,
`direction` IN/OUT and decimal-string `amount`. Optional fields are
`tendered_amount`, `change_amount` (default 0.00), and
`external_recording_reference`. A confirmed CARD leg requires the actual external
record UUID. CASH IN requires tendered = applied + change; OUT has no change.
Opening obligations have no legs; other supported rows reconcile all legs to
`amount_due`. Zero-applied sale payment receipts have no corresponding entry.

The software validates manifest and row hashes, causal values, counts and monetary
reconciliation. The supplied source/approval evidence hashes are operator declarations:
it does not verify external documents, legal authority or digital signatures.
Reports and audit explicitly retain `approval_authenticity_verified=false`.
An arbitrary approval UUID/reference alone is not proof of business approval.

## Operator sequence

1. Inventory and classify the source without modifying it. Preserve original evidence.
   Investigate open operations; do not force-close them to make an import possible.
2. Select the intended database using the normal API configuration. Prefer the
   configured private `ZEROMERMA_API_DATABASE_URL_FILE`; never put credentials in
   command arguments, the manifest or captured output.
3. Run diagnosis and dry-run first, then rehearse against an authorized restored copy.
   Confirm branch scope, original source identity, evidence references, counts,
   totals, differences and the exact returned `manifest_sha256`.
4. Obtain and retain the actual external approval, verified backup/restore evidence
   and controlled window. Apply only the reviewed immutable manifest.
5. Run dry-run again and reconcile `applied_row_count`/`applied_amount_due` against the
   manifest, inspect the canonical ledger and retain before/after hashes and audit.
   Business go-live approval remains a separate operational gate.

From the repository root with the pinned toolchain activated:

```powershell
uv run --frozen python scripts/dev/financial-reconciliation.py diagnose --branch-id <branch-uuid>
uv run --frozen python scripts/dev/financial-reconciliation.py dry-run --manifest <reviewed-manifest.json>
uv run --frozen python scripts/dev/financial-reconciliation.py apply --manifest <reviewed-manifest.json> --expected-manifest-sha256 <dry-run-hash> --controlled-window-confirmed
```

Diagnosis/dry-run use PostgreSQL REPEATABLE READ, READ ONLY transactions. They do
not log in, seed, flush, reconcile, commit business changes or mutate closes.
They report aggregate counts, monetary totals, differences and evidence identifiers.

Apply prompts interactively for email and a hidden password using the existing
login/rate-limit mechanism. Every row revalidates the persisted BACKOFFICE session
and current grants. Only an explicit superadministrator with GLOBAL
`cash_finance.manage` can apply; a POS login or a named seed administrator is
insufficient. The temporary CLI login is logged out at the end. Secrets are never
accepted through argv or stored in the manifest.

## Interruption, replay and recovery

Each row has one admitted idempotent command and one atomic transaction covering
the operation/entries, immutable progress, audit and outbox. Branch and actual cash
session locks serialize admission during the controlled window. A failure rolls
back that row; earlier committed rows remain durable.

Re-run the identical `apply` command to resume. `--row-key <key>` can select one
reviewed row. Already completed keys replay the original acknowledgement without
duplicating effects. Changed manifest content under the same identity, duplicate
causes and different evidence for an applied row are rejected.

Migration `20261019_0048_financial_import`, after
`20261019_0047_payment_terminal`, creates `financial_import_manifests` and
`financial_import_rows`. Database triggers reject UPDATE/DELETE of evidence and
progress. Downgrade refuses when either table contains evidence. Do not delete
rows or edit amounts to square totals: preserve evidence and use a reviewed forward
correction, or restore a verified full-database backup within the approved recovery
window. Rehearse restoration separately before productive use; synthetic transaction
rollback tests do not certify a production backup or signed reconciliation.

Automated acceptance is in `apps/api/unit_tests/test_financial_import_manifest.py`
and `apps/api/tests/test_financial_reconciliation.py`; database tests require the
guarded disposable PostgreSQL harness. No normal local volume is a test target.
