# Cash Close Contract Map

## Purpose

This document maps the current cash-close backend and frontend contract surface before a wizard-focused frontend refactor.

Scope:
- backend module: `apps/api/src/zeromerma_api/modules/cash_close`
- frontend module: `apps/pos-web/src/features/cash-close`
- tests:
  - `apps/api/tests/test_phase_7a_cash_close.py`
  - `apps/api/tests/test_phase_7b_cash_close.py`
  - `apps/pos-web/src/features/cash-close/model.test.ts`
  - `apps/pos-web/src/features/cash-close/submit.test.ts`

This is a contract review and implementation map. It is not a new cash-close UI design.

## Current endpoint map

Canonical router:
- `apps/api/src/zeromerma_api/modules/cash_close/presentation/router.py`

Endpoints:

| Endpoint | Method | Response | Current purpose |
| --- | --- | --- | --- |
| `/v1/cash-close/bootstrap` | `GET` | `CashCloseBootstrapResponse` | Resolve operator, branch, workstation, open session, blockers, warnings, payment-method catalog, baseline snapshot, pending class-capture summary. |
| `/v1/cash-close/summary` | `GET` | `CashCloseSummaryResponse` | Return financial totals, expected cash, movement breakdown, blockers, warnings, baseline snapshot, pending class capture, and reconciliation status. |
| `/v1/cash-close/reconciliation` | `GET` | `CashCloseReconciliationResponse` | Return product/class reconciliation context using current session state without committing anything. |
| `/v1/cash-close/preview` | `POST` | `CashClosePreviewResponse` | Validate counted amounts/products, compute variances, reconcile class capture, resolve discrepancy documents virtually, and return blockers/warnings. Read-only. |
| `/v1/cash-close/commit` | `POST` | `CashCloseDetailResponse` | Persist final close, payment-method counts, product counts, reconciliations, discrepancy resolutions, baseline snapshot, audit, and outbox. |
| `/v1/cash-close/{close_id}` | `GET` | `CashCloseDetailResponse` | Read a committed close report in detail. |

## Current schema support

Canonical schemas:
- `apps/api/src/zeromerma_api/modules/cash_close/application/schemas.py`

### Bootstrap

Supported now:
- user
- branch
- workstation
- local timestamp
- current open cash session
- blockers and warnings
- `can_start_close`
- payment method catalog
- baseline snapshot summary
- pending class-capture summary

Not present:
- wizard metadata
- denomination catalog
- cashier sign-off fields
- notification readiness flags

### Summary

Supported now:
- cash session
- opening amount
- cash-in / cash-out totals
- expected cash
- movement breakdown
- blockers / warnings
- baseline snapshot
- pending class capture summary
- reconciliation status

Not present:
- denomination-level expectations
- sign-off requirements
- printable summary token or export link

### Reconciliation

Supported now:
- relevant counted products
- class capture reconciliation rows
- reconciliation blockers / warnings
- `reconciliation_status`

Important constraint:
- `can_commit` is always `false` in the query response. Real commitability is determined after preview/submit-time validation.

### Preview request

Current request shape:
- `workstation_code`
- `counted_payment_methods[]`
  - `payment_method_code`
  - `counted_amount`
- `counted_product_lines[]`
  - `product_id`
  - `counted_quantity`
  - `notes`
- `manual_reconciliation_overrides[]`
  - `product_class_id`
  - `attribution_lines[]`
  - `notes`
- `discrepancy_resolutions[]`
  - `product_id`
  - `resolution_type`
  - `reason_code`
  - `quantity`
  - `notes`
- `notes`

Not present:
- denomination counts by bill/coin
- cashier password re-entry / explicit sign-off
- explicit acknowledgement flags for large differences
- notification preference or escalation payload

### Preview response

Supported now:
- expected / counted / variance cash totals
- payment method rows with expected and variance amounts
- movement breakdown
- blockers / warnings
- baseline snapshot
- pending class capture summary
- reconciliation status
- counted product lines
- class reconciliations
- discrepancy resolutions
- generated discrepancy documents
- notes

### Commit/detail

Commit persists and detail exposes:
- open/close session relationship
- branch / workstation context
- opened by / closed by users
- opened at / closed at timestamps
- payment method counted rows
- movement breakdown
- pending class capture summary
- reconciliation status
- counted product lines
- class reconciliations
- discrepancy resolutions
- generated discrepancy documents
- warnings
- notes

Not present:
- explicit cashier sign-off artifact beyond authenticated user identity
- report export URL
- printable close report endpoint
- dedicated backoffice notification state for high-impact differences

## Support matrix against the wizard target

| Capability | Status | Notes |
| --- | --- | --- |
| Bootstrap | Supported | `GET /bootstrap` is already sufficient for a wizard entry step. |
| Summary | Supported | `GET /summary` provides financial totals and warnings. |
| Reconciliation | Supported | `GET /reconciliation` returns class-capture and product reconciliation context. |
| Preview | Supported | `POST /preview` is read-only and already computes blockers, variances, and generated discrepancy documents. |
| Commit | Supported | `POST /commit` persists close and related audit/outbox traces. |
| Denomination counts | Not supported | Contract is only by payment method, not by bill/coin denomination. |
| Payment method counts | Supported | `counted_payment_methods[]` plus `payment_method_rows[]`. |
| Class capture reconciliation | Supported | Auto and manual resolution are both supported. |
| Difference reasons | Partially supported | Product discrepancy resolutions require `reason_code`; cash variance has warnings only, not a reason workflow. |
| Simple cashier validation/sign-off | Partially supported | Authenticated operator identity is persisted through `closed_by_user_id`, but there is no explicit sign-off payload or acknowledgment artifact. |
| Backoffice notification readiness for high-impact differences | Partially supported | Audit and general outbox exist, but there is no dedicated high-difference notification event or threshold policy. |
| Printable/exportable report | Not supported | No print/export endpoint or report artifact exists. |

## Persistence and audit readiness

Canonical persistence:
- `cash_session_closes`
- `cash_session_close_payment_method_counts`
- `cash_session_close_product_counts`
- `cash_session_close_class_reconciliations`
- `cash_session_close_reconciliation_attributions`
- `cash_session_close_discrepancy_resolutions`
- `cash_session_close_issues`
- `branch_counter_snapshots`
- `branch_counter_snapshot_lines`

Commit side effects already implemented:
- closes the active cash session
- stores close report rows
- stores a new counter baseline snapshot
- reconciles pending class-capture sale lines
- writes audit trail for `cash_close.committed`
- appends outbox events:
  - `cash_session.closed.v1`
  - `class_capture.reconciled.v1`
  - `close_discrepancy.generated.v1` when discrepancy documents are created

What is missing for high-impact close monitoring:
- no dedicated alert threshold contract for large cash variance
- no dedicated alert outbox event for backoffice review
- no persisted acknowledgment state for “cashier reviewed this variance”

## Current frontend foundation

Current frontend files:
- `apps/pos-web/src/features/cash-close/cash-close-api.ts`
- `apps/pos-web/src/features/cash-close/queries.ts`
- `apps/pos-web/src/features/cash-close/model.ts`
- `apps/pos-web/src/features/cash-close/submit.ts`
- `apps/pos-web/src/features/cash-close/ui.tsx`
- `apps/pos-web/src/features/cash-close/ui-support.ts`
- `apps/pos-web/src/features/cash-close/cash-close-screen.tsx`

Current frontend already has a local multi-step shape:
- `CONTEXT`
- `FINANCIAL`
- `PHYSICAL`
- `RECONCILIATION`
- `REVIEW`

Current frontend already has:
- a local step strip
- submit helpers that preview first and commit only when preview is ready
- financial count input by payment method
- physical count flow based on class/product/quantity
- right-side close summary panel

Current frontend does not yet have:
- a standardized shared wizard layout built on the newer POS shared module primitives
- denomination UI
- explicit sign-off / acknowledgment step
- explicit high-impact difference escalation UX
- print/export/report action after commit

## Small safe fix applied during review

The handwritten frontend helper for close detail was sending an extra `workstation_code` query parameter to:
- `GET /v1/cash-close/{close_id}`

The backend contract does not accept or use that parameter.

Applied fix:
- `apps/pos-web/src/features/cash-close/cash-close-api.ts`
- `apps/pos-web/src/features/cash-close/queries.ts`

Result:
- the frontend detail call now matches the backend route contract exactly.

## Gaps before wizard implementation

### Gap 1: denomination workflow

There is no backend support for denomination-level counting.

If the wizard requires:
- bills / coins
- denomination subtotal validation
- denomination discrepancy review

then a backend-first extension is required. Do not simulate this purely in UI.

### Gap 2: explicit cashier sign-off

Current commit relies on the authenticated user only.

Missing pieces if product wants an explicit sign-off step:
- acknowledgment payload field on preview/commit
- persisted sign-off flag or sign-off metadata
- optional sign-off timestamp separate from commit timestamp

### Gap 3: high-impact difference escalation

Current contract supports warnings such as:
- `LARGE_CASH_VARIANCE`
- `LONG_SESSION_DURATION`

But it does not support:
- configurable escalation thresholds in settings
- dedicated acknowledgment requirement for high-impact close
- dedicated backoffice alert event

### Gap 4: report/print/export

Current detail response is rich enough to render a report client-side later, but there is no canonical:
- PDF endpoint
- print payload
- export artifact

## Exact scope for PROMPT 24

PROMPT 24 can safely implement a wizard-based frontend refactor **without backend changes** if it stays inside the current contract:

1. Context step
   - use `/bootstrap`
   - show blockers, warnings, baseline snapshot, pending class capture, open session identity

2. Financial count step
   - use payment method catalog and counted payment amounts
   - do not introduce denomination inputs

3. Physical count step
   - keep the current class/product/quantity counting model
   - do not change reconciliation semantics

4. Reconciliation step
   - use `/preview` results for:
     - class capture reconciliation
     - discrepancy resolutions
     - generated discrepancy documents

5. Review and close step
   - submit through preview-first then commit
   - reuse current commit gating logic

6. Success/detail step
   - use `/v1/cash-close/{close_id}`
   - show persisted report details

PROMPT 24 should **not** assume:
- denomination support
- explicit cashier sign-off contract
- high-difference notification contract
- printable/exportable report contract

If PROMPT 24 needs any of those, it should stop and request a backend-first contract extension.

## Recommended backend-first follow-up after PROMPT 24

If product later needs stricter controlled close behavior, add these in order:

1. configurable high-difference threshold + acknowledgment flag
2. dedicated outbox event for backoffice close-difference review
3. denomination count contract
4. printable/exportable close report contract
