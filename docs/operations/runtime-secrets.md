# Runtime security and secret rotation

This is the implementation procedure for ZM-FIN-026–027. It describes development,
isolated validation and the deployment configuration boundary. It does not certify a
production installation, external encrypted storage, off-site backups or a pilot.
No live database, installed certificate trust or real secret is changed by this document.

## Deployment boundary

`ZEROMERMA_API_ENVIRONMENT` and `ZEROMERMA_WORKER_ENVIRONMENT` accept only `local`,
`test`, `staging` and `production`. Staging and production use the same strict
configuration checks. Runtime factories ignore repository `.env` files in those
two environments. Missing or sample database credentials prevent startup before
engine creation. The database must use `postgresql+psycopg`, an explicit host,
database and login, and a generated password of at least 24 characters. API and
worker should have distinct least-privilege database accounts; migration and
administration credentials must not be injected into either runtime process.

The API additionally requires explicit `CORS_ORIGINS`, `ALLOWED_HOSTS`,
`SESSION_POS_ORIGINS` and `SESSION_BACKOFFICE_ORIGINS`, using the
`ZEROMERMA_API_` prefix. Application origins are exact HTTPS origins without
paths, credentials, query strings, fragments or wildcards. The two audience lists
are disjoint and each is a subset of CORS origins. Loopback/development origins
are rejected in staging/production. Local tests supply their own isolated HTTPS
origins; they do not weaken this deployment policy.

Credentials use separate `__Host-` Secure, HttpOnly session cookies. Browser
requests send `X-ZeroMerma-Surface` and mutations send `X-CSRF-Token`; the session
service validates the selected audience's origin. CORS permits credentials only
for explicitly configured origins, with explicit methods and headers.
`SESSION_COOKIE_SAMESITE=lax` is the same-site default. Cross-site `none` requires
an explicitly selected HTTPS topology and retains the same CSRF/origin checks.

Staging/production reject training, development audit credentials/endpoints and
interactive API documentation. OpenAPI remains available to local/test contract
generation. No development routes are mounted in deployed applications.

## TLS, hosts and proxy trust

`infra/proxy/nginx.conf.template` is a reviewable LOCAL_FIRST template, not an
installed service. Render explicit API/POS/Backoffice hosts, certificate/key paths
and built frontend directories; replace only the named template placeholders,
preserving Nginx variables such as `$host`, `$uri` and `$remote_addr`.
DNS and certificate trust must resolve on the store LAN without Internet.
Use separately approved hostnames under the same site where practical.

Run Uvicorn on a restricted loopback interface with `--no-proxy-headers`.
`ZEROMERMA_API_TRUSTED_PROXY_IPS` is empty by default and accepts explicit IPs or
restricted CIDRs, never a universal network. Set it only to the actual proxy peer.
The proxy overwrites forwarded client/protocol values and strips other forwarding
headers. The application rejects untrusted forwarding metadata, unauthorized
Host values and non-HTTPS requests in staging/production. Do not expose the
upstream HTTP socket directly to the LAN.

The API uses no-store, nosniff, frame denial, no-referrer and a restrictive JSON
CSP. HTTPS responses add HSTS without implicitly including unrelated subdomains.
Frontend CSP allows local scripts and the explicit API origin; inline styles are
allowed for the React component styles, while inline scripts and eval are not.
Proxy access logs omit query strings, cookies and request bodies. Application
formatters redact credentials and URLs and emit exception types instead of raw
driver traceback text. Diagnostic work must preserve this boundary.

For isolated browser tests only, `New-ZeroMermaEphemeralTlsCertificate` in
`scripts/powershell/ZeroMerma.Tls.ps1` creates 24-hour localhost certificates with
a private key under `.tmp/validation`. It does not install system trust. The
isolated browser harness may ignore that temporary issuer; this option is not a
production certificate policy.

## Secret inventory and ownership

| Material | Owner | Runtime destination | Rotation/revocation |
|---|---|---|---|
| API database credential | Database/security operator | API environment or private DSN file | Rotate database login, switch runtime file, restart pools and verify |
| Worker database credential | Database/security operator | Worker environment or private DSN file | Same procedure, independent account |
| Migration/admin credential | Database operator | Explicit maintenance process only | Operator-controlled; never application frontend/runtime |
| Opaque session credential | Session service/user | Secure HttpOnly audience cookie; only verifier in DB | Session rotation/revocation; no shared signing secret |
| CSRF synchronizer material | Session service | Browser memory and server verifier | Bound to session credential lifecycle |
| Owner recovery material | Designated owner | Private host-bound recovery file | Existing one-use recovery CLI, durable successor and audit |
| Password-reset material | Identity administrator/user | One-use private delivery; verifier in DB | Expiry/consumption/revocation, no logging |
| TLS private key | Platform/security operator | Reverse proxy private runtime file | Certificate replacement and tested reload |
| Dev-audit token | Developer, non-production only | Explicit local environment | Disable endpoint and remove token |
| Future BBVA, notification, Telegram, backup credentials | Respective provider/operator | Future adapter/runtime secret injection | Provider-specific procedure required before enablement |

There is no replacement for the removed `AUTH_TOKEN_SECRET` or
`AUTH_TOKEN_TTL_MINUTES`: opaque sessions do not require a long-lived signing key.
External provider and backup integrations remain later tasks; unused credential
fields are not introduced merely to resemble a completed secret manager.

## Private runtime files

Use exactly one of `ZEROMERMA_API_DATABASE_URL` or
`ZEROMERMA_API_DATABASE_URL_FILE`, and likewise for the worker. In deployed
services, prefer private files outside the checkout and build context. Files must
be owned/readable only by the process account (Windows ACL or POSIX mode 0600),
regular files rather than symlinks, bounded in size and contain one value.
The file loader and CLI do not echo values. Settings representation and serialization
omit secret values and private-file paths.

Create the protected parent directory under the intended service account, then:

```powershell
uv run --frozen --package zeromerma-api python scripts/operations/manage-runtime-secrets.py store --output C:\ZeroMermaPrivate\api-database-url
```

Enter the value at the private prompt. Never pass a secret in CLI arguments, source
code, frontend environment, release manifest, log, screenshot or CI artifact.
The command reserves a new file and protects it before writing; it refuses overwrite.
Environment injection is supported for a supervisor/secret store, but process
environment access must be restricted to the service/operator account.

## Database credential rotation

Schedule the maintenance window and identify every process using the selected
login. Create a new private output path; do not overwrite the current credential.
The same runtime login rotates only its own PostgreSQL password.

```powershell
uv run --frozen --package zeromerma-api python scripts/operations/manage-runtime-secrets.py rotate-database --environment staging --current-file C:\ZeroMermaPrivate\api-database-url --next-file C:\ZeroMermaPrivate\api-database-url.next
```

The command durably writes the successor before changing the password, commits
the rotation, and verifies a new connection with the successor. On success,
point the service's `DATABASE_URL_FILE` at the successor and restart connection
pools. Verify readiness, authenticated session continuity and an authorized
operation in the isolated environment; then retire the old credential file using
the organization's secure file lifecycle. Rotation does not delete session rows
or change opaque-session verifiers, and requires no image rebuild.

Exit 2 means the commit outcome or successor probe is uncertain. Both files remain
private. Reconcile which credential connects and the database state before
changing configuration or retrying. A failure before any commit attempt removes
the uncommitted successor. Do not blindly restore an old password after an
ambiguous network outcome. Restore/readiness and service rollout are explicit
operator actions; this CLI does not claim a zero-downtime production rollout.

## Validation and limits

Run a bounded scan before publishing source or validation artifacts:

```powershell
uv run --frozen --package zeromerma-api python scripts/operations/manage-runtime-secrets.py scan --repository . --artifact .tmp/runtime-secret-rotation.log --artifact .tmp/runtime-security-final.log
```

`--artifact` accepts repeated explicit unpacked files. Add repeated `--secret-file`
arguments pointing to private inventory files to check known runtime material
(including the password component of a DSN). Values must never be supplied as CLI
arguments. The scanner checks both the Git index and tracked working files, private
PEM keys, actual session-cookie shapes, and any supplied secret values. Reports
contain only file identifiers and counts, never matching content. It fails when a
match is found or an input cannot be scanned. Unit tests prove detection even when
the index contains a secret but the working file is already clean.

This is a bounded source/artifact check, not proof about unseen Git history,
compressed archives, container layers, external provider consoles or arbitrary
unknown secret formats. Extract and explicitly inspect release artifacts before
the later deployment gate. The current development run has no supplied production
secret inventory and does not claim access to production secrets or images.

Unit tests cover explicit configuration allow/deny cases, audience origin
separation, hosts, trusted proxy metadata, HTTPS, safe error headers, credential
redaction, private-file input, no overwrite and ambiguous-commit recovery.
`apps/api/tests/test_runtime_secret_rotation.py` runs only through the canonical
guarded PostgreSQL harness. It creates a separate temporary login, rotates it,
checks preserved data and verifies that the old credential no longer connects.
The harness owns the ephemeral database and cleanup; it never selects the local
operational database. The local run passed 60 settings/security/CLI/worker-settings
tests and the PostgreSQL rotation test (11.33 seconds, disposable run
`18dc529eeae54978b8c57951ffda0317`). Nginx validated the rendered proxy template
using `nginx:1.28-alpine`, with no network, published ports or operational mounts.
These checks do not imply that a live reverse proxy was installed.

This evidence does not certify encrypted external storage, production database
roles, actual store DNS/certificates, production backup, provider credentials or
operational deployment. Those require the later platform and integration gates.
