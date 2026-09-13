# Executed web foundation baseline

Tasks: **ZM-FIN-012 and ZM-FIN-013**. This baseline preserves current business behavior and
release visibility. It establishes real transport/database/browser coverage; it does not
complete financial, inventory, authorization, hardware, or administrative features.

## Test layers

| Layer                      | Command                                                                                                | Evidence and limits                                                                                                                                           |
| -------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Unit/component             | `corepack pnpm --filter @zeromerma/pos-web --filter @zeromerma/backoffice-web test`                    | Vitest components, stores and API adapters use declared fixtures.                                                                                             |
| Existing browser/component | App `test:e2e`                                                                                         | Explicit `playwright.config.ts`, `e2e/` only. POS intercepts API requests; Backoffice covers its public shell. These are not integration evidence.            |
| Real browser integration   | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/dev/run-web-integration.ps1 -Surface All` | Fresh PostgreSQL, canonical migrations and disposable seed, API, worker readiness and separate web servers. Uses `playwright.real.config.ts` and `e2e-real/`. |

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
5. The test asserts that its only non-GET requests are login and zero-value opening.
6. An unauthenticated API request returns 401; an invalid stored token returns to login.

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
visible page headings and an authenticated reload. It asserts that login is its only
non-GET request. Sales and incident collections may be empty; successful empty reads
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
`ZM_E2E_WORKSTATION_CODE`. The runner supplies these; invoking Playwright directly without
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

## Remaining scope

The foundation smoke does not approve Development Complete or Feature Complete. Real
business journeys and broader cross-module authorization regression remain ZM-FIN-095
and ZM-FIN-100–102; the authorization block above supplies its specific negative tests.
Disconnected administration remains ZM-FIN-080/082/091. Integration tests intentionally
preserve current UX and do not fix those features. Existing router fast-refresh warnings
and large production bundle warnings are tracked as non-blocking foundation debt rather
than triggering a broad UI refactor here.
