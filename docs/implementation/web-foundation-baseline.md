# Executed web foundation baseline

Tasks: **ZM-FIN-012 and ZM-FIN-013**. This baseline preserves current business behavior and
release visibility. It establishes real transport/database/browser coverage; it does not
complete financial, inventory, authorization, hardware, or administrative features.

## Test layers

| Layer                      | Command                                                                                                | Evidence and limits                                                                                                                                           |
| -------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Unit/component             | `corepack pnpm --filter @zeromerma/pos-web --filter @zeromerma/backoffice-web test`                    | Vitest components, stores and API adapters use declared fixtures.                                                                                             |
| Existing browser/component | App `test:e2e`                                                                                         | Explicit `playwright.config.ts`, `e2e/` only. POS intercepts API requests; Backoffice covers its public shell. These are not integration evidence.            |
| Real browser integration   | `pwsh -NoProfile -File scripts/dev/run-web-integration.ps1 -Surface All` | Fresh PostgreSQL, canonical migrations and disposable seed, API, worker readiness and separate web servers. Uses `playwright.real.config.ts` and `e2e-real/`. |

The isolated harness also accepts `-Surface POS` or `-Surface Backoffice`. Run it with
the canonical Node.js 22, pnpm 10.33.0, Python 3.12 and uv 0.11.4 toolchain and an
available Linux Docker engine. Install browser binaries with
`corepack pnpm --filter @zeromerma/pos-web exec playwright install chromium` when needed.
Install repository dependencies with `corepack pnpm install --frozen-lockfile`.

Both apps typecheck real E2E/config files in addition to application sources. Node.js
types are explicit development dependencies. No database schema or domain contract is
added by these two tasks.

The existing mocked browser suites now start dedicated servers with `--strictPort`,
refuse server reuse, use at most two workers, and point unmatched API requests at an
unserved sentinel origin. Their fixtures include the current login surface, and their
selectors follow the existing table, cash-opening redirect and cash-close review UI.
The screenshot suite writes through `test.info().outputPath("screenshots")` under ignored
`test-results`; it no longer overwrites tracked screenshot references. Order drafts use
a future pickup date with explicit hour/minute fields.

## Real POS coverage

1. Direct access without a session returns to cashier login.
2. Real login reaches the mandatory opening form for the seeded workstation.
3. Opening with `0.00` creates a disposable cash session through the API.
4. Reload reads the persisted `OPEN` session and loads the real POS catalog.
5. Human activity may call the session heartbeat; other business writes remain limited
   to zero-value opening. The session checks also lock, reauthenticate and log out.
6. Cookies are HttpOnly/Secure/SameSite=Lax; reload restores without browser-stored
   credentials. A locked reload stays locked; reauthentication rotates CSRF while
   preserving the session ID and absolute deadline. Logout is confirmed by the API.
7. An unauthenticated API request returns 401; obsolete stored auth keys are removed
   and cannot authenticate.

No sale, order payment, refund, transfer, inventory operation or cash close is created.
The zero-value session exists only inside the uniquely identified disposable database.
The harness cleanup removes that database and the servers after success or failure.

## Real Backoffice family coverage

| Navigation family      | Route                | Actual GET endpoint       |
| ---------------------- | -------------------- | ------------------------- |
| Catalog and costs      | `/admin/productos`   | `/v1/admin/products`      |
| Sales and orders       | `/admin/ventas`      | `/v1/admin/sales/tickets` |
| Multibranch operations | `/admin/sucursales`  | `/v1/admin/branches`      |
| Purchases and supply   | `/admin/proveedores` | `/v1/admin/suppliers`     |
| Cash and finance       | `/admin/cortes-caja` | `/v1/admin/cash-cuts`     |
| Quality and hygiene    | `/admin/incidencias` | `/v1/admin/incidents`     |
| Control                | `/admin/auditoria`   | `/v1/admin/audit`         |

The smoke performs real administrative login, direct navigation, successful API reads,
visible page headings and an authenticated reload. In addition to login, human activity
may send session heartbeats; the family reads do not create business mutations. It
also opens the paginated own-session panel and verifies that a Backoffice cookie
cannot authenticate a POS request. Sales and incident collections may be empty; successful empty reads
count as integration, not as proof that a create workflow is complete.

The original foundation reader characterized surface access without an administrative
role. ZM-FIN-015–022 now replaces that fixture with seven explicit view capabilities,
each scoped to the same single active branch. It remains a non-superadministrator.
The added authorization suite checks accounts without grants, foreign branch reads,
independent management/export and revocation in an open browser session. See
[administrative authorization presentation](web-authorization.md) for the current
contract and validation evidence. The original five-test foundation results below
remain historical evidence for ZM-FIN-012/013.

## Placeholders and unreleased surfaces

The Principal navigation family contains dashboard and alerts and has no released real
page. It is excluded from real-family coverage. Dashboard, alerts and operational
payments use generic disconnected page infrastructure; the separate redirect test
confirms they route to Products and never counts them as API integration.

`releaseVisibility.ts` hides nine modules: dashboard, alerts, recipes/costs, commercial
discounts, operational payments, cleaning logs, sanitary verifications, roles/permissions
and settings. The last six have varying implementation underneath their release gates;
being hidden does not mean that their whole implementation is absent. These tasks
neither unhide nor complete them.

## Isolation and safe evidence

- The runner uses the canonical preconnection and postconnection destructive-test guards,
  unique run/database/container identities and dynamically allocated loopback ports.
- Real Playwright configuration requires the isolated-run marker, run ID, explicit API
  and app origins, generated fixture credentials and artifact directory. No operational
  URL, reused development server or credential default is accepted.
- Page/context route interception and HAR/WebSocket routing are forbidden by the fixture;
  service workers are disabled. Real suites do not import mock helpers.
- Real suites use one browser worker per disposable database and no retries. Repeated or
  concurrent runner invocations use different databases and ports.
- Credentials are generated for each run and never written as storage state. Raw browser
  traces, video and screenshots are disabled because they can capture login payloads.
- The custom reporter redacts generated passwords/emails, bearer tokens and JWTs. It saves
  minimal `results.json` files; sanitized network attachments retain only HTTP method,
  endpoint path and status. Query strings, headers and bodies are excluded.
- The reporter removes Playwright's automatic `error-context.md` page snapshot after
  checking that its path remains inside the isolated test output directory.
- Artifacts live under `.tmp/validation/web/<run-id>/` and are ignored by Git. Keep these
  sanitized files in CI; do not enable raw traces or export browser profiles for diagnosis.

Environment contract: `ZM_WEB_INTEGRATION_ISOLATED`, `ZM_E2E_RUN_ID`, `ZM_E2E_API_URL`,
`ZM_E2E_POS_URL`, `ZM_E2E_BACKOFFICE_URL`, `ZM_E2E_POS_EMAIL`,
`ZM_E2E_BACKOFFICE_EMAIL`, `ZM_E2E_PASSWORD`, `ZM_E2E_ARTIFACT_DIR` and
`ZM_E2E_WORKSTATION_CODE`, `ZM_E2E_TLS_CERT_FILE` and `ZM_E2E_TLS_KEY_FILE`. The runner supplies these; invoking Playwright directly without
them intentionally fails before a browser starts.

## Validation evidence

Executed locally on 2026-09-12 using Node.js 22.23.2 and the canonical toolchain:

| Command                                                                                                | Observed result                                                                                                                  |
| ------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------- |
| `corepack pnpm --filter @zeromerma/pos-web --filter @zeromerma/backoffice-web lint`                    | Both pass, zero errors; two existing router fast-refresh warnings per app.                                                       |
| `corepack pnpm --filter @zeromerma/pos-web --filter @zeromerma/backoffice-web typecheck`               | Both application and real-browser/config programs pass.                                                                          |
| `corepack pnpm --filter @zeromerma/pos-web --filter @zeromerma/backoffice-web test`                    | POS 47 files / 234 tests; Backoffice 56 files / 209 tests pass.                                                                  |
| `corepack pnpm --filter @zeromerma/pos-web exec vitest run src/lib/web-integration-support.test.ts`    | Additional 2 safety tests pass: direct/remote invocation rejection and interception/evidence protection.                         |
| `corepack pnpm --filter @zeromerma/pos-web --filter @zeromerma/backoffice-web build`                   | Both production builds pass. Large-bundle warnings remain: approximately 951 kB POS and 1,615 kB Backoffice minified JavaScript. |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/dev/run-web-integration.ps1 -Surface All` | **5/5 real browser tests pass**: POS 2, Backoffice 3; 39 migrations, real API/worker readiness and cleanup succeed.              |

Successful real run: `190bf6d0ebf74740841a0d141ef795a0`. Its ignored evidence directory is
`.tmp/validation/web/190bf6d0ebf74740841a0d141ef795a0/`. Each surface contains
`results.json` and numbered `sanitized-network.json` files; Backoffice also contains
`1-route-coverage.json`. Every documented family endpoint returned 200. The only browser
mutations in the main smoke were login and POS zero-value opening.

Early executions revealed harness startup/ESM-loading issues and stale UI selectors;
these were corrected before the successful real run. No application feature was changed
to make the smoke pass. Test discovery by itself is not completion evidence.

## Session lifecycle update (ZM-FIN-023–027)

Validated locally on 2026-10-18 with the canonical toolchain. Both applications now
restore independent server sessions through Secure, HttpOnly cookies, send the explicit
surface header and keep CSRF tokens only in memory. No browser bearer credential or
persisted authentication state remains; startup deletes the obsolete storage keys.
Human keyboard, pointer and touch events drive throttled activity requests. Session
reads, page reloads and background requests do not extend inactivity deadlines.

The POS gates protected routes while locked or while a password change is required.
Unlocking a locked temporary-password session still requires the password change.
The client clears protected query data on lock, logout, revocation and actor changes,
and ignores stale restoration responses after lock or logout. Backoffice includes
paginated own-session management and capability-gated administrative session revocation
and one-use password-reset issuance. Reset credentials are shown only in the active
dialog; the UI does not claim to send email or SMS. Superadministrator reset approval
continues to use the dedicated backend approval workflow.

| Validation | Observed result |
| ---------- | --------------- |
| `pwsh -NoProfile -File scripts/dev/check-foundation.ps1 -Stage Web` | Pass: lint, typecheck, production builds, **478 unit tests** (POS 245, Backoffice 222, API client 8, shared UI 3), and **11 mocked browser tests** (POS 10, Backoffice 1). |
| `pwsh -NoProfile -File scripts/dev/run-web-integration.ps1 -Surface All` | **8/8 real browser tests pass** (POS 2, Backoffice 6), with HTTPS, the real API, migration through 0041, worker readiness and disposable database cleanup. |
| PowerShell parser check for `scripts/dev/start-local.ps1` | Pass. The persistent development database startup was not executed as part of this validation. |

Foundation evidence is under
`.tmp/validation/foundation/c63cc7f0b725441eabf4dc4a2a7b22f8/`.
Real-browser evidence is under
`.tmp/validation/web/460a7d8fc26c4cccb8289e2af2e8ad03/`; both surface `results.json`
files record success. This run verifies POS lock/reload/unlock/logout, cookie properties,
surface isolation, Backoffice own-session display, seven released read families and
revocation of an already open session. Password-change, incorrect-unlock and stale
response behavior also have focused mocked-browser or unit coverage. This does not
claim full end-to-end coverage of every administration workflow.

The local startup script now launches HTTPS loopback services with a disposable
certificate, checks both API and worker database targets before migration, refuses busy
ports and records owned process IDs and logs. It does not install OS certificate trust.
The isolated browser runner validated the HTTPS Vite configuration; execution against
the persistent development database remains a separate local operational check.

The final review added eight focused session-boundary regressions. Expired content
is now hidden and its query cache cleared before the status read; a failed network
request leaves a visible verification retry. Locked tabs restore on focus, and a
CSRF rejection restores the current cookie envelope without replaying the rejected
mutation. Recovery itself uses only session reads and does not renew inactivity.
The follow-up validation passed lint/typecheck, 23 focused unit tests (POS 15,
Backoffice 8) and seven affected mocked browser tests (POS 6, Backoffice 1).
The preceding 478-test entry records the earlier full Web run; it is not a claim
that the full suite was repeated after these eight additions.

Real POS integration was repeated successfully with two tabs sharing the actual
cookie: **2/2 tests pass** in
`.tmp/validation/web/c40b2a6a779242919142e03586137c4d/`. After one tab unlocks and
rotates cookie/CSRF, the other restores its envelope and keeps the same activity
timestamp and idle deadline. Headless Chromium's focus notification is delivered
explicitly because activating its page does not consistently emit a window-focus
event; API calls and cookies remain real and unintercepted. Focused command logs
are `.tmp/session-boundary-pos-tests.log`, `.tmp/session-boundary-bo-tests.log`,
`.tmp/session-boundary-mocked.log`, `.tmp/session-boundary-bo-mocked.log` and
`.tmp/session-boundary-real-pos.log`.

## Remaining scope

The foundation smoke does not approve Development Complete or Feature Complete. Real
business journeys and broader cross-module authorization regression remain ZM-FIN-095
and ZM-FIN-100–102; the authorization block above supplies its specific negative tests.
Disconnected administration remains ZM-FIN-080/082/091. Integration tests intentionally
preserve current UX and do not fix those features. Existing router fast-refresh warnings
and large production bundle warnings are tracked as non-blocking foundation debt rather
than triggering a broad UI refactor here.
