# Transactional idempotency foundation

ZM-FIN-028 implements the shared infrastructure governed by DEC-07. ZM-FIN-029
adopts it for POS sale confirmation; ZM-FIN-030 adopts the existing order commands
on POS and Backoffice. Other business commands retain their own
pending adoption tasks; the existence of the foundation does not make them
idempotent. POS and Backoffice remain separate, and PostgreSQL remains the
authority for both the command and its result.

## Identity and request contract

Each new business intention uses a new UUIDv7 `Idempotency-Key`. Retries reuse that
same key. The database enforces global uniqueness of the key; actor, operation,
branch, workstation and cash session are contextual checks, not independent key
namespaces. Reusing a key with incompatible context or payload yields HTTP 409
with `IDEMPOTENCY_KEY_REUSED` and creates no new business effect.

`X-Request-ID` identifies an HTTP attempt and may change between retries. It is
not the durable command identity. An authentication session is also separate:
logging in again does not erase a completed intention. No historical request ID
is converted into an idempotency record without evidence.

The backend owns the header and response contract. OpenAPI and the TypeScript
client are generated from that contract. An endpoint must explicitly adopt the
foundation before claiming replay guarantees; merely accepting a request header
or disabling a submit button provides no such guarantee.

## Canonical fingerprint

The fingerprint includes a version, operation code, actor user ID, applicable
branch/workstation/cash-session IDs, and the canonical payload. It uses SHA-256
or an equivalent cryptographic hash. The canonicalization contract must account
for stable JSON object ordering, UUID and enum normalization, UTC timestamps,
contractual Decimal scales, defaults, and the distinction between absent values
and `null`. Version 1 uses typed canonical values and sorted JSON object keys.
Pydantic payloads include their validated defaults; an operation for which field
presence changes meaning must represent that distinction in its validated
payload. A mapping with an absent key differs from one with a `null` value.
Array order remains significant; related branch IDs are explicitly normalized
as a sorted set. Decimal fields use their declared scale without rounding, and
naive timestamps or non-finite numbers are rejected.

Cookies, passwords, CSRF credentials and other secrets, `X-Request-ID`, and the
idempotency key itself are excluded from the fingerprint payload. The
canonicalizer rejects known sensitive keys and secret-typed values rather than
silently removing them. This is a defense alongside explicit response schemas,
not a classifier that can discover every possible PII value. Persistence does
not require the original request body.

## Integration interface

`IdempotencyExecutor.execute` owns the root transaction and receives an explicit
operation code, validated payload, `CommandContext`, response policy, read-only
context/authorization callbacks and a business action. It must be entered before
business writes. The action may flush and use savepoints but must not commit,
roll back the root transaction or perform an external effect. Adopting a command
requires removing its existing internal commits; wrapping an unchanged service
that commits is invalid.

The caller's authorization callback checks the authenticated actor, surface,
capability and all participating branch/context boundaries. It runs on admission,
replay and before finalizing a new result. The context resolver receives the saved
context on replay, so it can identify a historical cash session without requiring
that session to be open. This does not authorize a new command in a closed session.

`CommandResult` provides a status and a Pydantic snapshot, with an optional stable
resource/reference. `ResponsePolicy` declares the snapshot schema, version,
optional rejection schema and immutable reconstruction callback. A
`DeterministicRejection` rolls back the action savepoint and stores the declared
safe rejection; authentication, authorization and rate-limit failures are excluded.

The HTTP adapter exposes `require_idempotency_key` and `idempotency_response`.
It rejects duplicate headers, returns `Idempotency-Replayed` and `Cache-Control:
no-store`, and reconstructs rejection envelopes with the current attempt's
request ID. OpenAPI publishes reusable components and the
`x-zeromerma-idempotency` convention. Adoption is declared on each protected
operation, rather than inferred from the presence of those shared components.

## POS sale confirmation and recovery

`POST /v1/sales/confirm` requires a UUIDv7 `Idempotency-Key` and an explicit
`cash_session_id` alongside the workstation, ordered lines and payment legs.
The cash session is part of the intention; reopening a workstation does not
silently redirect an old retry to the new session. A new intention requires the
authenticated operator's current open session and existing POS authorization.

The successful response is HTTP 201 with `SaleConfirmationView`. The snapshot
contains the sale, line, payment and cash-movement identities and amounts, but
excludes `operator_email` and `operator_full_name`. Authenticated sale-detail
queries retain those display fields. The ticket is a projection of the same sale
ID; confirmation does not create a separate ticket identity. An authorized replay
returns the original snapshot, without repricing or reconstructing it from mutable
operator, branch or catalog labels.

The executor owns the transaction. The sale action can flush but cannot commit
independently. Sale, sale lines, sale payments, cash movements, `sale.confirmed`
audit, the sale outbox event and the terminal idempotency result succeed or roll
back together. Audit and outbox preserve the durable operation identity separately
from the HTTP attempt's request ID. This adoption does not implement the pending
canonical inventory ledger or the separate sale-versus-close locking task.

The existing authentication boundary locks the user and authentication session.
Concurrent HTTP requests for that same user can therefore serialize before sale
admission. Coordinated HTTP retry tests prove one result and one effect; separate
PostgreSQL command tests exercise same-key contention and independent-key progress
without that HTTP authentication lock. This is not a claim of parallel HTTP
throughput, and ZM-FIN-029 does not redesign authentication locking.

After a lost response or page reload, the POS can use
`GET /v1/sales/confirmations/{idempotency_key}` with `workstation_code` and
`cash_session_id`. The read revalidates the actor, POS capability and context; a
key is not a bearer credential. A completed result is returned from its safe
snapshot even if the historical session has since closed. A missing or unresolved
result is HTTP 409, not evidence that a new sale may safely be submitted with a new
key. Recovery reads do not execute sale effects or reserve new identities.

For one intention the POS keeps the same key through pending requests, temporary
contention and network failures. A terminal result ends that intention; a new sale
receives a new key. While its outcome is unknown, the operator must not bypass
recovery by creating a replacement intention. A deterministic business rejection
is distinct from transport failure and is displayed as a terminal rejection.

The browser persists only the key, payload digest, outcome status and opaque
user/branch/workstation/cash-session identifiers, plus the workstation code.
The economic request body remains in memory. No sale payload, response snapshot,
operator display details, cookie, CSRF token or credentials enter browser storage.
Reload and another tab recover through the backend; they do not reconstruct or
auto-submit a sale from browser storage. This is online recovery under DEC-15,
not offline sale capture or a promise of offline availability.

Executed adoption evidence and limitations are recorded in
[the sale validation record](../implementation/sale-idempotency-validation.md).

## Order commands and recovery

The seven existing order mutations share the executor: POS create, mark-ready,
deliver and cancel, plus Backoffice mark-ready, deliver and cancel. They do not
constitute independent payment endpoints. Initial advance legs belong to create,
final settlement legs to POS delivery, and applicable refund legs to POS
cancellation. Backoffice retains its prohibition on capturing pending settlement
or refund effects. Each command is a separate intention with its own key.

All four POS command payloads identify `cash_session_id` explicitly. The old
optional Backoffice body field named `idempotency_key` is removed; the UUIDv7
header is the sole idempotency input, and `X-Request-ID` remains attempt
correlation. The result is a minimized `OrderCommandResultView` with order and
payment identities, state and amounts. Customer/operator personal information,
free text and current UI actions belong to authenticated detail queries rather
than durable replay snapshots.

Order transitions lock their `CustomerOrder` row before validating current state
and balance, regardless of which surface initiated the command. Distinct keys
must not permit duplicate delivery/refund or incompatible transitions. The root
executor transaction covers order/items, existing payment legs, audit, outbox and
the terminal response. The action does not commit independently. Unrelated
orders are not serialized by an operation-wide lock.

Read-only recovery is exposed under
`/v1/orders/commands/{command_code}/{idempotency_key}` with workstation and cash
session, or `/v1/admin/orders/commands/{command_code}/{idempotency_key}` with
branch context. The command code selects an explicit supported operation. A
completed retry returns the original acknowledgement even if the order has since
advanced; it does not rebuild the old result from its mutable current detail.
Unknown or uncommitted outcomes remain uncertain and cannot authorize a new key.
Current authorization and original context apply to every lookup.

Browser recovery stores only minimal metadata, while the request body stays in
memory. It must not become a queue of economic operations or customer PII. The
accepted DEC-15 online-only boundary applies to orders as it does to sales.
Existing v1 order audit/outbox payloads retain their historical personal fields;
the privacy reduction here applies to the new replay snapshot and browser
recovery metadata, not every persisted domain or event record.

This adoption does not make `CustomerOrderPayment` part of the canonical cash
ledger: that integration is ZM-FIN-042. It also does not complete DEC-10's minimum
advance, production commitment, reservation, amendment or terminal-state rules.
The full POS and Backoffice order workflows remain later tasks 058 and 078.
Commands, validation status and those known differences are recorded in
[the order validation record](../implementation/order-idempotency-validation.md).

## Transaction and replay boundary

For an internal command, the reservation, business document, economic and physical
effects, audit, outbox and terminal result belong to one PostgreSQL transaction.
`COMPLETED` must never be committed after the business transaction in a separate
transaction. Existing domain uniqueness constraints remain additional defenses.

The canonical states are `PROCESSING`, `COMPLETED`, `REJECTED` and `UNKNOWN`.
An internal `PROCESSING` reservation is not independently committed. A crash
before commit rolls back the record and effects together; a crash after commit
but before delivering the response leaves a result available for replay.

Migration `20261018_0042_idempotency` adds `idempotency_records`, a global unique
key, UUIDv7 validation, nine CHECK constraints and a partial response-expiry index.
The identity has restrictive references to its actor, branch, workstation and
cash session. A deferred PostgreSQL constraint trigger rejects a durable
`PROCESSING` row at commit, including an accidental low-level connection commit.
It reads the row's final state so reservation and completion within one transaction
remain valid. Durable external processing would require a later explicit schema
and workflow change; it is not silently enabled by this foundation.

A second trigger refuses deletion and changes to the key, operation, fingerprint,
actor/context, initial request correlation and creation timestamp. Terminal results
are immutable except for the guarded payload purge described below. `UNKNOWN`
cannot transition back to `PROCESSING`; reconciliation to a terminal state remains
possible for a later approved provider workflow.

Schema/key errors, authentication failures and authorization denials before
admission do not consume the key. A deterministic business rejection after
admission may be persisted as `REJECTED`. Unexpected failures, deadlocks,
serialization failures and pre-commit timeouts roll back and permit a retry with
the original key.

A replay authenticates the current request and revalidates current capability
and scope before returning the saved result. Knowledge of a key grants no access.
The completed fast path must not rerun domain commands, pricing, inventory
calculations, external adapters, worker handlers or outbox consumers. A historical
cash session need not remain open to retrieve an already committed, authorized
result; a new intention resolves its current context again.

## Concurrency and external outcomes

Requests compete only for the same key using the unique index. The executor uses
a transaction-local lock timeout for reservation, restores the previous timeout,
and translates contention to `409 IDEMPOTENCY_IN_PROGRESS` with `Retry-After: 1`.
Its default wait is one second; this is a technical bound, not a declared business
SLA. Different keys, unrelated
commands and independent branches must progress concurrently. There is no global
queue, lock by operation code, human approval or external dependency on the
synchronous internal-command path.

`UNKNOWN` is an uncertain external outcome, not failure or permission to repeat
an external effect. Provider workflows, leases and reconciliation remain later
work under DEC-14 and the integration tasks. A future lease expiration may permit
reconciliation, not blind re-execution.

## Retention and privacy

The durable identity preserves enough information to reject future incompatible
reuse and identify the committed result. Response expiry must not delete this
identity or turn an old key into a new intention.

A response payload may be removed only when a compact snapshot or stable result
reference remains sufficient for an authorized replay. No original request body
is required once its canonical fingerprint and metadata suffice. Sensitive
response material must not be persisted merely to simplify replay.

`purge_expired_payloads` selects a bounded batch with `FOR UPDATE SKIP LOCKED`,
reconstructs each result through the declared reference and verifies equality
with the saved snapshot before clearing it. PostgreSQL separately requires a
non-null reference and actual expiry according to its clock. Only the payload
and update timestamp may change; JSON null cannot substitute for SQL NULL. There
is no scheduled purge worker in this block.

Every terminal result retains a SHA-256 response fingerprint. Both its original
snapshot and every later reconstruction must match that immutable digest, so a
reference whose underlying data changes cannot return a different result after
purge. Response payloads and references are JSON objects or SQL NULL; JSON literal
null, arrays and scalars cannot satisfy the result/reference contract. A reference
still needs an operation-specific immutable resolver; a digest detects drift but
does not recover a lost historical snapshot.

Downgrade to 0041 is allowed only while the store is empty. Once identities exist,
use a corrective migration or restore a consistent database backup containing
both the business effects and the idempotency records. Restoring or deleting one
side alone can recreate a duplicate-effect risk.

DEC-16 requires category-based retention, PII minimization and preservation of
economic history; there is no universal legal TTL for every record. Audit has its
own retention policy and cannot substitute for the idempotency identity. This
foundation does not introduce a blanket deletion job, indefinite PII retention,
or a claim of legal compliance.

## Adoption boundaries

ZM-FIN-029 adopts the foundation in sales; 030 covers the seven existing order
commands and their embedded payment effects;
031–035 cover returns/refunds, cash, transfers, corrections/waste and production.
The wider review of commit ownership belongs to 039 and unified causal context to
040. Historical order request correlation is not converted into fabricated
idempotency records during adoption.

Read-only endpoints do not require idempotency keys. The shared foundation is
tested through isolated transactional commands; no diagnostic business endpoint
is added to the deployed product merely to demonstrate the infrastructure.

Implementation details and executed acceptance evidence are recorded in
[the validation record](../implementation/idempotency-validation.md). Completion
requires the verified migration, model/constraint parity, concurrent PostgreSQL
tests, contracts, and immutable CI evidence; this document alone is not evidence
that a command is protected.
