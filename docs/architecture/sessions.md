# Browser sessions and account security

ZM-FIN-023–027 implements DEC-05 in the existing identity module. PostgreSQL is
the session authority. POS and Backoffice authenticate separately; opening the
Backoffice from POS passes no credential and grants no additional authority.

## Credentials and browser boundary

The API issues random opaque credentials through `__Host-zm-pos-session` and
`__Host-zm-backoffice-session`. Cookies are Secure, HttpOnly, Path=/, without a
Domain attribute. Only credential and CSRF verifiers are stored in the database.
The response contains user authorization, non-secret session metadata and a CSRF
token kept in browser memory. Reload restores this envelope through
`GET /v1/auth/session` without extending inactivity. There is no refresh token.

Every request identifies its audience using `X-ZeroMerma-Surface`. A cookie for
one audience cannot authenticate the other. Each audience has a separate,
disjoint Origin allowlist, which is a subset of credentialed CORS origins. This
also prevents a compromised POS origin from restoring a Backoffice CSRF token
when the browser happens to carry both cookies. Mutations require a matching
Origin and `X-CSRF-Token`; public login and recovery validate Origin and apply
rate limits. For safe requests with no Origin, a strict Referer origin is used,
then the request URL origin for same-origin deployments. These must still match
the selected audience allowlist. A separate API origin is not automatically
trusted as an application origin.

Bearer authorization and credential query parameters are rejected. Frontends
remove the previous authentication storage keys and credential URL parameters;
there is no migration or compatibility exchange for old bearer tokens. API
contracts and TypeScript types are generated from backend schemas.

## Lifecycle and transactions

| Rule | POS | Backoffice |
|---|---|---|
| Idle timeout | 30 minutes, then LOCKED | 30 minutes, then EXPIRED |
| Absolute lifetime | 12 hours | 8 hours |
| Concurrent sessions | One ACTIVE/LOCKED per user and workstation | Multiple |
| Workstation | Required and validated | Absent |
| Cash session | Linked when an owned cash session opens | Absent |
| Reauthentication | Same session ID, rotated cookie/CSRF, unchanged absolute deadline | Full login after expiry |

The 30-minute policy applies when login, accepted activity or reauthentication
sets an idle deadline. Existing persisted deadlines are not extended in bulk;
restoring or polling a session preserves its current deadline. Absolute limits
remain unchanged.

Polling and reload do not count as activity. Real keyboard, pointer and touch
events use a throttled activity endpoint; authorized business mutations also
renew idle time within the fixed absolute deadline. Locking does not close cash.
Closing cash revokes only POS sessions linked to that cash session, in the same
transaction. The client returns to authentication after the close result.

POS commands use the authenticated workstation. Receiving a branch transfer
creates its receipt at the destination and preserves the shipment's original
workstation. The `transfers.execute` policy permits only the shipment's
`IN_TRANSIT` to `RECEIVED` or `RECEIVED_WITH_VARIANCE` transition when a validated
receipt was inserted in the same transaction, with matching shipment, branches,
recipient and destination workstation. That causal link must remain valid through
commit. Historical or rolled-back receipts cannot authorize a transition, and
this exception does not permit reassigning a document's workstation.

The identity boundary lock precedes user, workstation and session locks.
PostgreSQL enforces active POS slot uniqueness. Triggers revoke affected
sessions when user security, role/permission status, assignments, surfaces or
branch scopes change, including SQL changes outside the HTTP service. A rollback
also rolls back revocation. Requests resolve current grants and scopes rather
than trusting cached claims. Revocation committed before a subsequent request
invalidates that request. Sale/payment/close race handling remains part of the
later financial consistency block.

Session creation and state transitions write audit and outbox records without
credential values. Actor, audience, session, workstation, cash and request context
are preserved where applicable. Frequent activity updates do not create an
unbounded stream of audit/outbox events.

## Passwords and recovery

New administrative accounts require a password change before business activity.
Changing a password revokes every session and outstanding reset credential.
Administrative recovery requires `users.manage`, target-user scope and a reason.
Protected privileged accounts additionally require the existing two-person
approval mechanism bound to the exact operation, target and payload hash.

Reset credentials are independent random secrets, stored as hashes, expire after
30 minutes by default and can be consumed once. Issuing and consuming recovery
both revoke sessions. The code is returned once to the authorized operator;
delivery is manual, with no implied email/SMS provider. The UI keeps it only in
memory and never places it in a URL or persistent storage. Failed authentication
uses generic responses and persistent account/IP rate limits across API workers.
Login success persists `last_login_at`.

The Backoffice shows own sessions with individual and other-session revocation.
User administration exposes scoped session management and recovery actions based
on backend-provided permissions. Self-service password change and manual reset
completion are available on both surfaces.

## Deployment and cutover

Migration `20261018_0041_auth_sessions` follows
`20260912_0040_authorization`; it adds session, login-limit and reset-credential
state plus transactional triggers. Existing business records are retained. The
old stateless bearer cannot create a new cookie session. Users log in again.

Apply the migration once to an explicitly selected environment, deploy API and
both web builds together, and restart API/worker after secret changes. Local
development and browser integration use HTTPS; test certificates are scoped to
disposable validation and never installed as globally trusted certificates.
See [runtime secret operations](../operations/runtime-secrets.md) for production
fail-closed settings, private files, rotation and proxy configuration.

An actual production installation still requires chosen LAN hostnames,
certificates trusted by the POS computer, protected service access, backups and
recovery drills. This implementation does not certify those later deployment
and operational gates.
