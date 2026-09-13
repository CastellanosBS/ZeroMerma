# Authorization operating procedure and validation

Scope: ZM-FIN-015–022, implementing the approved DEC-03/04/19 policies. This document
records the repository implementation and isolated validation. Provisioning a
production account belongs to an explicitly configured deployment; no existing
operational volume is used by these tests.

## Initial owner provisioning

Upgrade the intended database to the canonical Alembic head. Configure the API
database through its normal protected environment configuration. Run from the
authorized control-plane host and an interactive private terminal:

```powershell
uv run --frozen --package zeromerma-api python scripts/bootstrap/manage-privileged-access.py bootstrap-owner --designation ZEROMERMA_OWNER --email owner@example.com --full-name "ZeroMerma Owner" --recovery-file C:\ZeroMermaPrivate\owner-recovery.json
```

Use the actual owner login address and an existing private recovery directory.
The CLI prompts twice for the password; it accepts no password or recovery secret
as a command-line argument. The recovery output must be a new file. Before any
secret is written, its permissions are restricted to the current OS account
(private Windows ACL or Unix mode 0600). The owner designation, explicit role and
global assignment are committed together with audit and outbox. The material is
never printed or persisted in audit/outbox.

Protect the recovery file separately from ordinary credentials and application
logs. Its hostname is bound to the actual control-plane FQDN at provisioning.
Do not commit this file, copy it into a build artifact, or use a demo login as the
initial owner. The CLI rejects an existing email and repeated initial provisioning.

## Recovery of a second Superadministrator

Create/select a different active Backoffice account through ordinary authorized
user administration. With exactly one active Superadministrator, use its UUID on
the same authorized host:

```powershell
uv run --frozen --package zeromerma-api python scripts/bootstrap/manage-privileged-access.py recover-second-superadmin --target-user-id 00000000-0000-0000-0000-000000000000 --recovery-file C:\ZeroMermaPrivate\owner-recovery.json
```

Replace the example UUID with the reviewed target. The CLI validates file access,
host binding, one-use material and account state. It cannot remove or deactivate
the last authority. The database records only a hash of the recovery material.

The successor material is written and flushed to a private sibling `.next-*`
file before the database transaction commits. After commit, the CLI atomically
publishes that file over the consumed material. If publishing fails after commit,
exit code 2 identifies the retained private file: preserve it because the previous
material has already been consumed. A crash in this interval is resolved from the
retained file and the durable recovery audit record, never by reusing consumed
material. If the commit raises an error, its outcome may be uncertain: the server
can have committed before the connection loses its acknowledgement. Exit code 2
therefore retains the private file after any commit attempt. Reconcile the recorded
owner, credential hash and audit before retrying or publishing the successor. Only
failures before a commit attempt clean up a newly reserved file.

With two active Superadministrators, subsequent privilege changes use the normal
durable proposal/approval procedure and two distinct current authorities.

## Durable two-person approval

The generated API exposes these operations under
`/v1/admin/roles/privileged-changes`:

1. The initiating Superadministrator submits `POST` with an operation, its exact
   user/role targets, the matching administrative command payload, a reason and
   an expiration of 1–60 minutes. The server validates and canonicalizes the
   payload and returns its SHA-256 digest.
2. A different current Superadministrator reads `GET /{change_id}`, reviews the
   targets and full payload, then submits `POST /{change_id}/approve` with
   `{"payload_sha256":"<reviewed digest>"}`.
3. The initiating administrator submits `POST /{change_id}/execute` with the same
   digest. The server rechecks both accounts, their required capability and the
   target state, then atomically applies and consumes the approved change.

Supported command types include user profile/status/locking, branch membership,
role assignment/removal and role modification/status. A proposal cannot be reused,
silently changed or executed after expiration or approver revocation. The last
active global Superadministrator and the explicit administration capabilities
remain protected. Ordinary user creation does not assign roles implicitly.

Use the generated contract for each command body and the normal authenticated API
client; do not put bearer credentials in URLs or saved examples. A dedicated
Backoffice approval-review screen is not implemented in this block and remains
tracked with the later user/role module completion work.

## Validation

The canonical shared harness provisions disposable PostgreSQL 16 databases. It
checks test-only role, host, database name, run ID and confirmation before access.
It never connects these tests to the application's normal database URL.

```powershell
pwsh -NoProfile -File scripts/dev/run-api-tests.ps1 -TestTarget apps/api/tests/test_authorization_context.py
pwsh -NoProfile -File scripts/dev/run-api-tests.ps1 -TestTarget apps/api/tests/test_privileged_bootstrap.py
uv run --frozen pytest apps/api/unit_tests/test_privileged_cli.py
pwsh -NoProfile -File scripts/dev/run-api-tests.ps1 -TestTarget apps/api/migration_tests/test_migration_validation.py
corepack pnpm contracts:check
pwsh -NoProfile -File scripts/dev/check-foundation.ps1 -Stage All
```

Use the canonical Python, uv, Node and pnpm versions before invoking the harness.
Functional administrator tests provision a separate owner through the application
service using `testing/authorization.py`; they do not promote the runtime demo
administrator. Permission-denial and branch-isolation cases use explicitly limited
accounts. The real Backoffice browser fixture is a scoped reader for seven module
families and has no Superadministrator role.

## Executed evidence (2026-09-12)

All local runs use the canonical toolchain and disposable databases. Their working
tree contains the integrated block; the hosted Foundation run is the acceptance
record for the immutable committed checkout.

| Validation | Executed result | Local evidence |
|---|---|---|
| Migration chain, schema drift and transition from revision 0039 | 11 passed, including preserved pre-migration evidence and no implicit global assignment | `.tmp/validation/authorization/migrations.xml` |
| Effective authorization, initial provisioning, CLI ACL and recovery | 23 passed, including concurrent provisioning, one-use rotation and publish-failure recovery | `.tmp/validation/authorization/provisioning.xml` |
| Delayed worker observation after revocation | 1 passed; causal headers retained and new mutation denied | `.tmp/validation/authorization/worker-scope.xml` |
| Final CLI and bootstrap regression | 10 passed, including real PostgreSQL commits followed by simulated lost acknowledgements during both provisioning and recovery | `.tmp/validation/authorization/cli-final.xml` |
| Branch and cash regression | 15 passed, including concurrent cash-session opening versus branch deactivation and complete cash-cut/flow reads | `.tmp/validation/authorization/cash-focused.xml` |
| Operation scope and denial regression | 21 passed; mapped joins, all admin collections, SQL bypass rejection, rollback and revocation; 4 final lock/regression cases also passed | `.tmp/operation-authorization-tests-final4.log`, `.tmp/operation-authorization-lock-final.log` |
| Worker Foundation stage | 26 unit and 4 PostgreSQL tests passed; real `--once` command completed | `.tmp/validation/foundation/4edfbe30e51f4ed9a2a47a425a4aa7eb/` |
| Negative Foundation stage | 10 passed, including unsafe-database refusal before engine creation | `.tmp/validation/foundation/188970b38afa4a8d8dce2b925a795194/` |
| Real browser integration | 8 passed: 2 POS and 6 Backoffice; scope denial, missing grants and live revocation verified | `.tmp/validation/web/7227425c36864b02a666e9b91c6daccd/` |
| Web Foundation stage | 462 unit tests, 9 existing browser tests, lint, types and builds passed | `.tmp/validation/foundation/32879e6f573249c5bc8ff021a4f691e8/` |
| Contracts Foundation stage | 50 passed; 227 OpenAPI operations, no drift, no unexplained manual wire types | `.tmp/validation/foundation/4ce0b1188470434caf6dc4d814410dbf/` |

The branch creation regression was corrected by assigning the new UUID before
scope validation at flush. Mapped aliases used by cash-close and transfer queries
must preserve their own SQL identity when scope criteria are attached. Tests retain
negative cases for unclassified raw SQL/Core aliases and positive cases for mapped
aliases, joins, subqueries, counts and authorized lifecycle operations.

The final delivery identifies the successful hosted run and commit. It must include
all eight Foundation stages and the aggregate **Foundation required** check. Hosted
artifacts contain the full suite reports and generated-contract hashes. Provisioning
a production owner, executing outbox domain handlers, building the dedicated
approval-review UI and the remaining session, integrity and deployment work are
tracked separately in the master plan.
