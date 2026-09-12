# Foundation validation

This is the executable validation map for ZM-FIN-009–014. It connects the contract, API,
worker, POS, Backoffice and CI baselines to reproducible commands. It does not certify
Development Complete, Feature Complete, Production Ready, or Pilot Ready.

## Canonical entry point

Use PowerShell 7, the repository Python/uv/Node/pnpm versions, frozen dependencies,
and Linux Docker. Install Chromium before browser stages:

```powershell
uv sync --all-packages --dev --frozen
corepack pnpm install --frozen-lockfile
corepack pnpm --filter @zeromerma/pos-web exec playwright install chromium
./scripts/dev/check-foundation.ps1 -Stage All
```

`All` executes eight stages in sequence and stops on failure. `-Stage <name>` runs one
stage, which is also the CI contract. All database work uses the protected disposable
PostgreSQL harness. There is no development-database validation mode or `-CiIsolated`
switch. Normal local application startup remains a separate workflow.

| Stage | Required checks | Principal evidence |
| --- | --- | --- |
| `Preflight` | Canonical versions, frozen Python and Node installations, Linux Docker | Transcript and stage result |
| `Backend` | API compilation, repository Ruff, strict API/worker mypy, API integration and unit suites | Transcript, backend JUnit |
| `Worker` | Compilation, discovered unit tests, PostgreSQL characterization, no-DB CLI startup | Worker unit and PostgreSQL JUnit, logs |
| `Migrations` | Full canonical Alembic validation through the guarded harness | Checkpoint/restore output and stage result |
| `Contracts` | Functional operation matrix, generated OpenAPI/client/inventory equality, contract/matrix tests | Metrics, zero-drift output, contract JUnit |
| `Web` | Workspace lint, typecheck, Vitest, builds, existing browser/component smoke | Transcript and component/browser results |
| `Browser` | Real POS and Backoffice suites against their dedicated API and disposable PostgreSQL | Sanitized per-surface results and API observations |
| `Negative` | Valid/invalid toolchain subprocesses, corrupt OpenAPI copy, unsafe seed rejection | Negative-gate JUnit and transcript |

The guarded Python runner can also discover the complete repository test configuration:

```powershell
./scripts/dev/run-api-tests.ps1
./scripts/dev/run-api-tests.ps1 -TestTarget apps/worker/integration_tests
./scripts/dev/run-migration-validation.ps1 -Mode Full
```

With no target, pytest discovers all paths in `pyproject.toml`: API integration, API unit,
API migrations, worker unit, worker integration, and development-script tests. The CI
stages divide those suites by responsibility; they do not silently replace discovery
with a worker boot-only check. Existing test-database guard tests are reused.

## Task acceptance map

| Task | Acceptance evidence and command | Scope boundary |
| --- | --- | --- |
| ZM-FIN-009 | `corepack pnpm contracts:check`; `Contracts` stage; policy and three derived artifacts | Backend owns contracts; checking never rewrites reviewed files |
| ZM-FIN-010 | `Backend` stage; executed API/DB suites, Ruff, strict mypy and compilation | Existing behavior is characterized; later business/security work remains open |
| ZM-FIN-011 | `Worker` stage; empty/outbox reads, unavailable DB, CLI lifecycle and signal tests | No business handlers, durable delivery, retry machine or processed-event writes |
| ZM-FIN-012 | `Web` and `Browser` stages for POS; real login/open/reload/API evidence | The smoke does not implement the complete sales/payment/inventory day |
| ZM-FIN-013 | `Web` and `Browser` stages for Backoffice; real navigation/read/reload | Hidden/disconnected modules and complete authorization remain later work |
| ZM-FIN-014 | All eight stages, negative gates, clean-checkout CI, immutable evidence and aggregate status | Pipeline configuration and local passes do not constitute a completed hosted CI run |

Detailed baselines:

- [API contract policy](../architecture/api-contracts.md)
- [Executed API foundation](api-foundation-baseline.md)
- [Executed worker foundation](worker-foundation-baseline.md)
- [POS and Backoffice foundation](web-foundation-baseline.md)
- [Migration validation](../operations/database-migrations.md)

## Hosted CI and merge status

`.github/workflows/foundation.yml` runs on pull requests, pushes to `main` and `codex/**`,
and manual dispatch. Its eight independent matrix jobs use fresh Ubuntu checkouts and
the same stage runner. Matrix fail-fast is disabled so one failure does not hide the
other stage results. Each job has a bounded timeout.

Each job installs the canonical toolchain and frozen Python/Node dependencies. The uv
action cache is explicitly disabled; the workflow configures no Node, dependency,
browser, result, or application cache restoration. Browser jobs install Chromium and
its Linux dependencies. CI receives no operational database credentials.

The final job is named **Foundation required**. It runs after the validation matrix,
including failures, and succeeds only when the matrix result is `success`. On 2026-09-12,
GitHub protection for `CastellanosBS/ZeroMerma` branch `main` was configured and read back
with that required check, strict status checks and administrator enforcement. Force
pushes and branch deletion remain disabled. A failed or missing aggregate check blocks
integration into the protected branch.

The implementation is published on `codex/zm-fin-009-014-foundation`. Its clean repository
history has no common ancestor with the historical remote `main`; publication does not
replace that branch or merge the historical application into the current architecture.
The reviewed CI commit and result are recorded in the execution evidence below.

After a stage succeeds, CI rejects tracked changes and untracked source files detected
by `git status --porcelain`. Generated artifact drift must be reviewed and fixed in the
source branch, never repaired by the check. Artifact upload runs even after failures.

## Isolation and evidence

The shared PostgreSQL harness creates a unique run/database/container identity, a
test-only role and credential, a loopback port, and tmpfs storage. Preconnect validation
rejects missing or operational URLs before creating an engine. A postconnect identity
check precedes migrations, fixture deletion, and seeding. The harness restores process
environment variables and removes its own disposable container; cleanup failure is
reported as failure rather than silently counted as success.

Real browser integration provisions its own servers and generated fixture users.
It never adopts a running development server. An authenticated API probe binds the
browser fixtures to the expected run before browser execution. POS and Backoffice use
separate real Playwright configurations; page/context interception and service workers
are disabled. Existing mocked browser/component tests remain useful in the `Web` stage,
but their successes are not counted as real API/database integration.

Logs and manifests are written under `.tmp/validation/foundation/<run-id>/`. Stage
manifests include the stage, pass/fail, UTC timestamps, commit SHA, working-tree
cleanliness and SHA-256 hashes of lockfiles and the three contract artifacts. Real browser
evidence is under `.tmp/validation/web/<run-id>/` and contains
minimal results plus sanitized method/path/status observations. Raw browser traces,
screenshots, videos and credential storage state are disabled for real integration.
Server artifacts are redacted before handoff. Generated passwords, tokens and database
URLs must not be included in committed documentation.

CI uploads `.tmp/validation/` plus configured Playwright result directories even on
failure, with a 14-day artifact retention period. These ignored local directories are
not release artifacts or operational backups.

## Execution evidence and acceptance

The local integrated validation ran on 2026-09-12 with the canonical toolchain and
disposable PostgreSQL 16. The following stage manifests record completed local runs:

| Stage | Observed result | Local evidence run |
| --- | --- | --- |
| Preflight | Canonical versions, frozen dependencies and Linux Docker pass | `706f3b1ee63d4b0eacc40141e31d1e42` |
| Worker | 26 unit tests, 4 PostgreSQL tests and no-DB CLI pass | `44b61025dd1040618d60cf3c3204c393` |
| Migrations | Full mode: 10 tests pass across the 39-revision chain | `366da7f65e604ae6bdb3776ef67e43aa` |
| Contracts | Zero artifact drift and 50 contract/matrix tests pass after the final policy review | `b39c37a41447497e814dc3d0b52dc88c` |
| Negative | 10 tests pass, including real subprocess nonzero exits for deliberate invalid inputs | `912b7e9beaa243208d7967ae8355d98f` |
| Real browser | POS 2 and Backoffice 3 pass against real API/DB; cleanup succeeds | `190bf6d0ebf74740841a0d141ef795a0` |

API and web baseline documents retain the initial failures, their corrections and
verified focused reruns. Local runs used the coordinated working tree; their manifests
do not claim a clean committed checkout. The hosted `Foundation` run is the authoritative
whole-commit acceptance record: all eight stages and **Foundation required** must pass,
and every job must finish with a clean source tree. Consult the
[implementation branch CI runs](https://github.com/CastellanosBS/ZeroMerma/actions?query=branch%3Acodex%2Fzm-fin-009-014-foundation).
Each run identifies its immutable commit and retains stage logs, JUnit/browser evidence
and artifact hashes. The task delivery records the exact successful run URL and commit.

An interrupted or partially executed stage, a collected test list, or a configured
workflow is not a passing result. Controlled failure evidence must show both the command
rejection and a failed aggregate required check; the disposable probe branch is never
merged into the implementation branch.

The [controlled failure run](https://github.com/CastellanosBS/ZeroMerma/actions/runs/34724965016)
executed commit `329e9c10dce530de02603554a81fc877f9f5c632`, changing only `.node-version`
from 22 to 24 relative to the first integrated candidate. All eight jobs rejected the
inconsistent toolchain policy with exit 1; **Foundation required** also failed. The
workflow definition itself was unchanged. The temporary branch/worktree was removed
after its logs and SHA-256 evidence were saved; the immutable run remains accessible.

Foundation evidence does not replace the later full authorization, idempotency,
concurrency, financial/inventory reconciliation, business E2E, hardware, load, security,
backup/restore, production platform, or pilot gates. Browser success validates the
specific exercised paths; worker success validates controlled metadata polling.
