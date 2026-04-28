# Final POS Consistency Audit

Generated on 2026-04-23.

Purpose:
- verify that the POS behaves as one coherent operational platform
- record the final hardening adjustments applied in this pass
- document residual consistency debt explicitly before production rollout

Scope reviewed:
- login and cash opening
- POS sale
- tickets
- returns
- waste
- adjustments
- counter transfer
- branch shipment
- branch receipt
- orders
- payments
- discounts
- cash close

## Completed improvements

### Cross-cutting foundations confirmed

- Shared POS foundation components are in place and broadly reused:
  - `PosButton`
  - `PosStatusBadge`
  - `PosPanel`
  - `PosCard`
  - `PosSectionTitle`
  - `PosFieldLabel`
- Shared feedback infrastructure is in place and reused:
  - `PosLoadingState`
  - `PosEmptyState`
  - `PosErrorState`
  - `PosConfirmationDialog`
  - `PosOperationResultToast`
  - `PosBlockerPanel`
- Shared operational layout and history infrastructure is present:
  - `PosModuleLayout`
  - `PosSummaryPanel`
  - `PosContextBanner`
  - `PosHistoryView`
  - `PosFilterBar`
  - `PosRecordList`
  - `PosRecordTable`
  - `OperationDocumentResult`
  - `OperationHistoryList`
  - `DocumentActionsMenu`
- Shell and keyboard foundations are centralized:
  - shared shell/sidebar registry
  - `KeyboardHelpOverlay`
  - shared record-list `Ctrl+F` search registration
  - shell-level sidebar tab protection and explicit sidebar focus shortcut

### Sensitive operation consistency confirmed

- Sensitive modules now converge on the same result/history grammar:
  - waste
  - adjustments
  - counter transfer
  - branch shipment
  - branch receipt
  - returns
  - payments
  - discounts
  - cash close
- Audit-safe detail visibility exists without exposing raw payloads.
- Browser print/copy actions are normalized through shared document action helpers.
- Backend remains the source of truth for sensitive document detail, history, audit summary, and controls.

### Final hardening changes applied in this prompt

`Pedidos` still had a few visible ad hoc surfaces compared with the rest of the platform. This pass normalized the most visible ones without rewriting the module:

- order detail loading now uses `PosLoadingState`
- order detail error now uses `PosErrorState`
- order detail empty selection now uses `PosEmptyState`
- top-level retry and create actions now use `PosButton` instead of raw shell buttons

Files changed in this hardening step:
- `apps/pos-web/src/features/orders/orders-screen.tsx`

## Module consistency snapshot

| Module | Layout consistency | Right panel consistency | Shared state consistency | Keyboard consistency | Notes |
| --- | --- | --- | --- | --- | --- |
| Login / cash opening | Good | N/A | Good | Good | Entry flow is coherent and keyboard-first. |
| POS sale | Good | Good | Good | Good | Core cashier flow is the strongest keyboard implementation. |
| Tickets | Good | Good | Good | Partial | Search/list keyboard is shared; full focus containment is still lighter than POS sale. |
| Returns | Good | Good | Good | Partial | Shared list/history/result flow is in place. |
| Waste | Good | Good | Good | Good | Shared confirmation/result/history is consistent. |
| Adjustments | Good | Good | Good | Partial | Audit/result/history are aligned; full focus-flow coverage is still uneven. |
| Counter transfer | Good | Good | Good | Good | Shared operational document grammar is in place. |
| Branch shipment | Good | Good | Good | Good | Shared operational document grammar is in place. |
| Branch receipt | Good | Good | Good | Partial | Shared history/detail exists; line-entry focus can still be tightened later. |
| Orders | Partial | Partial | Good | Partial | Functional and coherent, but still uses older composition patterns internally. |
| Payments | Good | Good | Good | Good | Shared query/result pattern is consistent. |
| Discounts | Good | Good | Good | Good | Shared query/result pattern is consistent. |
| Cash close | Good | Good | Good | Partial | Wizard is coherent; some unsupported backend steps remain explicit deferrals. |

## Remaining issues

These are the main residual consistency gaps after this final pass.

### 1. `Pedidos` still uses older internal composition

`apps/pos-web/src/features/orders/orders-screen.tsx` remains the largest module outlier:
- it still relies heavily on older `ContinuousWorkspaceSheet` / local orchestration patterns
- it still uses a custom decision panel instead of the newer `PosSummaryPanel` grammar
- it still contains more local button styling than the newer modules

This is operationally acceptable now, but it should be the first cleanup target if a post-release UI convergence pass is planned.

### 2. Full focus containment is still uneven

The shell now prevents accidental sidebar tab entry before explicit navigation, which resolves the worst cross-module interruption.

What remains uneven is per-module focus containment:
- some modules still do not fully use `useFocusFlow`
- list/detail and right-panel transitions are consistent visually, but not every routed module traps task focus as tightly as the POS sale flow

Residual modules to review first if keyboard hardening continues:
- `tickets`
- `returns`
- `orders`
- `corrections`
- `cash-close`

### 3. Not every routed module uses the same top-level wrapper

The platform now looks coherent because the shell, state surfaces, history surfaces, and action grammar are shared.

However, some modules still achieve that through older local wrappers instead of `PosModuleLayout`. That is a composition consistency gap, not a user-facing contract gap.

### 4. Backend DB-backed test execution is still environment-blocked here

Broad backend `pytest` suites continue to time out in this environment when PostgreSQL-backed tests are executed. Static checks and frontend regressions are green, but production-readiness still requires rerunning the DB-backed suites on a responsive local database.

## Production readiness checklist

### Frontend

- [x] Shared shell/sidebar navigation is unified
- [x] Shared buttons, badges, panels, and result states exist
- [x] Shared query/list/history pattern exists
- [x] Shared document action framework exists
- [x] Critical cashier flow is keyboard-first
- [x] Sensitive module actions use shared confirmation/result patterns
- [x] Training mode and scanner readiness are explicit
- [ ] `Pedidos` internal composition is fully migrated to the newest shared layout grammar
- [ ] Full task-level focus containment is uniform across every routed module

### Backend and contracts

- [x] Backend remains the source of truth for frontend contracts
- [x] Sensitive operations keep audit/outbox traces
- [x] History and audit visibility endpoints exist for the sensitive modules already migrated
- [x] Dev audit snapshot exists for persisted-state inspection
- [ ] Broad DB-backed backend regression suites rerun successfully on responsive PostgreSQL

### Reporting and delivery

- [x] Copy/print action framework exists
- [x] Real browser print exists for tickets and return receipts
- [ ] PDF/export contracts still do not exist for most operational documents
- [ ] Cash close printable/exportable report is still deferred by backend contract

## Manual QA checklist

### Entry and shell

- [ ] Login starts on email and advances with Enter
- [ ] Cash opening shows workstation, branch, cashier, and status clearly
- [ ] Sidebar cannot be entered accidentally by `Tab`
- [ ] Sidebar can be reached explicitly with the keyboard shortcut
- [ ] `F1` / `Ctrl+/` opens keyboard help

### POS sale

- [ ] Class capture works with arrows and Enter
- [ ] Product direct works with arrows and Enter
- [ ] Quantity capture accepts Enter / NumpadEnter
- [ ] `F2` or `Ctrl+Enter` jumps to payment
- [ ] Exact payment and change payment both succeed
- [ ] Sale success exposes folio and ticket actions

### Consultation and returns

- [ ] Ticket search by folio works from the list and scanner field
- [ ] Ticket reprint opens the browser print flow
- [ ] Return preload from Tickets works
- [ ] Return reason and refund method are mandatory
- [ ] Ticket return status updates after a committed return

### Sensitive operations

- [ ] Waste requires origin, reason, and lines before commit
- [ ] Counter transfer confirms before commit and shows folio after success
- [ ] Shipment requires destination before commit
- [ ] Receipt exact and difference paths both work
- [ ] Adjustment requires reason and shows net effect before commit

### Operational modules

- [ ] Order create/list/detail/deliver/cancel flows are coherent
- [ ] Payment create flow validates required fields and confirms cash-affecting operations
- [ ] Discount create flow validates required fields and high-value acknowledgement where required

### Cash close

- [ ] Wizard blocks when there is no open cash session
- [ ] Summary, reconciliation, preview, and final commit work end to end
- [ ] High-impact differences require acknowledgement before final commit

## Recommended follow-up order after this audit

1. rerun the DB-backed backend regression suites on responsive PostgreSQL
2. clean up `Pedidos` onto the newer shared layout/right-panel grammar
3. finish full module-level focus containment for the remaining routed modules
4. only then consider further cosmetic cleanup
