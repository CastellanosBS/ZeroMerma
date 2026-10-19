# POS local continuity and interaction validation

Scope: ZM-FIN-066 and ZM-FIN-067. This document distinguishes implemented browser behavior from physical device certification.

## Local authority and connection states

The browser uses the local API and canonical PostgreSQL database. `GET /health` reports process liveness. `GET /ready` separately checks that PostgreSQL responds and the configured connection is writable, rather than a recovery/read-only node. The probe uses a bounded connection pool and query timeout; a response does not authorize failover, certify schema migration, or certify backups.

The POS observes readiness on load, every 15 seconds, when focus/network hints change, and before every business POST. The probe deadline is five seconds; the business request deadline is fifteen seconds. A timeout after sending a command is an unknown result, never proof of rejection. Commands retain their original idempotency identity and the existing explicit recovery flow.

| UI condition | Meaning | Operator action |
| --- | --- | --- |
| Local server available | API and writable PostgreSQL answered the probe | Continue with the server-authorized operation |
| Database unavailable | API answered the readiness schema but PostgreSQL is unavailable or read-only | Stop new transactions and contact support |
| Local server unreachable | Browser cannot establish the local request; LAN, DNS, TLS, proxy and API cannot be distinguished from this evidence alone | Check local connectivity and server health |
| Browser reports a network cut | An advisory browser signal, not proof of Internet or LAN failure | Continue if the local readiness probe succeeds |
| External Internet unverified | No approved external connectivity probe is configured | Check the relevant external provider independently |

TanStack Query uses `networkMode: always` for this local architecture. This does not enable offline transactions: the transport checks the local authority and mutation retries remain disabled. There is no service worker mutation queue, local financial ledger, or automatic command resubmission on reconnect. Reconnection refreshes reads only. If a command was already sent, use its recovery control before repeating any payment. Reload retains only allowlisted recovery metadata, not the economic request body.

Do not call an unavailable local server an Internet outage. Cash operations can continue through a healthy LAN without Internet. External payment approval or digital delivery still requires its own provider to be available.

## Session and shared-terminal behavior

The approved inactivity interval remains thirty minutes. The server remains authoritative. Reload and passive reads do not extend activity. Locking preserves the cash shift; unlocking requires the current password. A backwards workstation clock cannot keep the existing UI timer above thirty minutes; focus/visibility restoration also reads server session state. Configure the workstation clock correctly before deployment.

Credentials remain in server-managed cookies and in-memory CSRF state. Business query caches, cart identity, sensitive notifications, and notification callbacks are cleared at their applicable session/actor boundaries. Pending command metadata is retained for reconciliation by the original operator; logout must not silently erase evidence of an uncertain payment.

## Keyboard, touch and reduced viewport behavior

POS dialogs have an accessible name and modal semantics, move initial focus inside, trap Tab/Shift+Tab, close with Escape only while idle, restore focus, and suppress underlying business shortcuts. Confirmation dialogs initially focus the first control; destructive confirmation must be deliberate. Keyboard help and the action palette use the same boundary. Modals scroll in reduced viewports. Coarse-pointer controls have a minimum 44-pixel target; visible focus and reduced-motion styles are provided.

The automated browser matrix covers 800×600, 1366×768, and 1920×1080 for keyboard-help focus containment, scrolling, and absence of horizontal document overflow. Additional controlled tests verify a healthy LAN with a negative browser connectivity hint and unavailable PostgreSQL before command admission, followed by reconnect/reload with no automatic POST. Unit coverage includes command response loss, preserved keys, bounded probe timeout, backwards clock, and sensitive notification cleanup.

These checks do not certify a purchased touchscreen, scanner, printer, drawer, browser/OS installation, or assistive-technology combination. Record the actual models, operating system, browser version, display scaling, resolution, and touch mode, then repeat checkout, opening/closing, recovery, modal keyboard navigation, 200% zoom, scanner focus, and one-handed interaction on the installed station. Record any unsupported device before pilot acceptance.

## Validation commands

Use the repository toolchain and isolated API runner. Current focused evidence:

- API: `.tmp/run-040-validation.ps1 -Targets @('apps/api/tests/test_local_readiness.py','--show-capture=no') -Label 'pos-local-readiness-final'` — 5 passed, including the real PostgreSQL probe; sanitized publication `0f1bbdee6d4549368ca5198c52b429a7`.
- Browser: `corepack pnpm --filter @zeromerma/pos-web exec playwright test --config playwright.config.ts e2e/connectivity-accessibility.spec.ts` — 5 passed.
- Final integrated unit, contract, build, and real API browser evidence belongs to the complete block validation report and its exact commit.
