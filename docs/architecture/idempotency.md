# Transactional idempotency foundation

ZM-FIN-028 implements the shared infrastructure governed by DEC-07. Adoption by
sale confirmation starts in ZM-FIN-029; the existence of this foundation does not
make existing business endpoints idempotent. POS and Backoffice remain separate,
and PostgreSQL remains the authority for both the command and its result.

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
`x-zeromerma-idempotency` convention without declaring adoption on existing routes.

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

ZM-FIN-029 adopts the foundation in sales; 030 covers orders and their payments;
031–035 cover returns/refunds, cash, transfers, corrections/waste and production.
The wider review of commit ownership belongs to 039 and unified causal context to
040. The misleading historical order `idempotency_key` currently used as request
correlation must be corrected during its command adoption, without fabricating
historical idempotency records.

Read-only endpoints do not require idempotency keys. The shared foundation is
tested through isolated transactional commands; no diagnostic business endpoint
is added to the deployed product merely to demonstrate the infrastructure.

Implementation details and executed acceptance evidence are recorded in
[the validation record](../implementation/idempotency-validation.md). Completion
requires the verified migration, model/constraint parity, concurrent PostgreSQL
tests, contracts, and immutable CI evidence; this document alone is not evidence
that a command is protected.
