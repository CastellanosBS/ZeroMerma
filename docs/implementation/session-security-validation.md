# ZM-FIN-023–027 validation

Branch: `codex/zm-fin-023-027-session-security`.
Migration head: `20261018_0041_auth_sessions`.

The owner confirmed that current data is development/test data only. Validation
uses generated, disposable PostgreSQL instances; no normal local database is
migrated, seeded or reset by this block's tests.

## Reproducible checks

Use the pinned toolchain from `.python-version`, `.node-version`, `uv.lock` and
`package.json`. On a host with another Node version, activate the existing local
toolchain for the shell before invoking commands.

```powershell
./scripts/dev/check-foundation.ps1 -Stage All
```

The eight required stages are Preflight, Backend, Worker, Migrations, Contracts,
Web, Browser and Negative. The harness creates isolated PostgreSQL databases,
uses HTTPS for both real browser surfaces, and removes generated TLS private
keys before publishing artifacts. It records commits, timestamps and artifact
hashes under `.tmp/validation/`. CI captures and sanitizes stage console output
while preserving its exit code, and uploads only sanitized text evidence from
`.tmp/validation-published/`. The same stages run in Foundation CI.

Targeted security checks are included in the complete backend suite:

```powershell
./scripts/dev/run-api-tests.ps1 -TestTarget @(
  "apps/api/tests/test_auth_session_lifecycle.py",
  "apps/api/tests/test_cookie_boundary.py",
  "apps/api/tests/test_runtime_secret_rotation.py"
)
```

Coverage includes audience/Origin/CSRF isolation with simultaneous cookies;
legacy bearer rejection; idle and absolute expiry; cookie rotation; concurrent
POS replacement; logout and session revocation; authorization-trigger rollback;
cash linkage and closing; temporary-password restrictions; privileged recovery
approval; single-use/expired recovery; generic login errors and rate limiting;
and real PostgreSQL credential rotation preserving stored data.

Browser tests exercise restoration, lock/unlock, logout, absence of persisted
credentials, authorization revocation and existing POS/administrative flows.
Settings, proxy, logging and secret CLI tests cover explicit production policy,
spoofed forwarding headers, hidden development endpoints, CORS, private-file
handling and redaction. Migration checks include all historical checkpoints,
schema drift rejection, interruption rollback and dump/restore.

## Acceptance and remaining operational work

The following local evidence was obtained on 2026-10-18:

| Check | Result | Evidence |
|---|---|---|
| Pinned dependency installation | Passed, frozen lockfiles | Foundation `edf8a0c827b74aa4bf48109759dfd4b1` |
| Worker | 26 unit and 4 PostgreSQL tests passed | Foundation `466d6cc86f5b42a6bfdaefdb13b58523` |
| Negative gates and evidence publication | 15 passed through the CI console wrapper; failing subprocess exit code and JUnit failure preserved, credentials removed | Foundation `a7c36889775c46de901e8cac1d8cfcc4` |
| Web | 478 unit and 11 mocked browser tests passed; lint, types and builds passed | Foundation `c63cc7f0b725441eabf4dc4a2a7b22f8` |
| Real HTTPS browsers | 2 POS and 6 Backoffice tests passed | Browser run `460a7d8fc26c4cccb8289e2af2e8ad03` |
| Full migrations | 13 tests passed; 41 historical checkpoints, zero unknown drift, preservation and dump/restore passed | `.tmp/session-migrations-final.log` |
| Contracts | 50 tests passed; 240 operations and 59 bounded collections, zero generated drift | Foundation `bb2ed8c016684671b370a2fa0c742cf1` |
| Runtime security and secret tools | 60 tests and real PostgreSQL rotation passed | `.tmp/runtime-security-final.log`, `.tmp/runtime-secret-rotation.log` |
| Session security | Lifecycle, concurrency, scope denial, privileged recovery, temporary-password lock/unlock and positive session administration passed | `.tmp/auth-session-lifecycle-final.xml`, `.tmp/auth-session-boundaries.log`, `.tmp/session-migration-boundaries.log`, `.tmp/session-admin-positive-final.log` |
| Final runtime configuration review | 54 focused tests passed, including rejection of deployment mode selected only by checkout `.env` | `.tmp/runtime-security-review.log` |
| Final browser session review | 23 focused unit tests (8 new regressions), 7 affected mocked browser tests and 2 real POS tests passed; cross-tab recovery does not extend activity | Browser run `c40b2a6a779242919142e03586137c4d` |
| Privileged access regression | 5 affected tests passed; authority changes revoke sessions and preserve business audit/outbox assertions | `.tmp/session-privileged-regressions.log` |
| Transfer workstation binding | 21 tests passed: 7 existing HTTP flows and 14 causal-link, workstation and rollback cases | `.tmp/session-transfer-binding-current.xml` |
| Training bootstrap regression | 3 unit tests passed with explicit POS authorization context | `.tmp/session-training-regressions.log` |

The integrated API regression is additionally required; its final status is
supplied by Foundation for the delivered commit. The
initial migration gate rejected the four new check expressions and partial-index
reflection until exact reviewed fingerprints and negative mutation tests were
added. No general drift exception was introduced. Contract inventory regeneration
follows functional consumer inventory updates, so UI references remain canonical.

The developer launcher was parsed and reviewed; it was not run against the
persistent development database. The real HTTPS browser harness exercised
the equivalent API/Vite path with disposable data. Source and explicit log scans
are bounded checks, not proof about unknown production secrets or image layers.

Implementation evidence is distinguished from deployment evidence. Test results
and CI references are recorded with the delivered change; the existence of this
document alone is not a passing validation result. Foundation must pass for the
immutable delivered commit before merge.

The next functional dependency is ZM-FIN-028 (idempotency and financial
consistency). The later Security Ready and Production Ready gates still require
their dedicated validation, actual hostnames/TLS/service configuration,
credential provisioning, retention, backup/restore and real operation rehearsals.
No terminal integration, hardware certification or production deployment is
claimed by this block.
