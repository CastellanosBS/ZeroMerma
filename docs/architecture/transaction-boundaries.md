# Explicit transaction ownership

Status: ZM-FIN-039 implemented and dedicated local acceptance verified. This convention
implements the existing DEC-07, DEC-08 and DEC-18 requirements; it does not introduce
a new business policy or a second persistence architecture.

The machine-readable inventory is
[TRANSACTION_BOUNDARY_MATRIX.json](TRANSACTION_BOUNDARY_MATRIX.json). Execution
evidence and remaining limits are recorded in
[transaction-boundary-validation.md](../implementation/transaction-boundary-validation.md).

## One owner for each root transaction

Every mutating use case identifies its root transaction owner. Participants use
the supplied SQLAlchemy session, may add or flush rows, and never commit or roll
back their caller's root transaction. A flush is not successful persistence. Only
an explicit successful commit makes the effects durable.

An owner may adopt the transaction already opened by its authorized reads. It
must not silently adopt unrelated business writes. The idempotency executor
enforces this distinction, including previously flushed writes. Its early
admission rejection leaves that pre-existing transaction with its original
caller; request cleanup must eventually discard unfinished work.

`db/transactions.py::rollback_on_failure` decorates explicit service owners and
uses `rollback_on_error` for cleanup. The decorator does not begin, commit, retry
or translate a transaction. Successful services retain their visible commit
sites. Any escaping `BaseException`, including cancellation, discards unfinished
work before the error returns to the caller. Function-based owners use the same
context manager where a method decorator is inappropriate.

Cleanup can revert only the current unfinished transaction. An error after a
successful commit cannot undo already durable changes. A subsequent read or
response-construction error may therefore return an error after the earlier
mutation committed; its cleanup discards only any new unfinished read transaction.
The command's durable identity, where available, is the authority for recovery.

The request session dependency also rolls back failures and unfinished work before
closing. It does not commit at the end of a successful request. An omitted commit
must remain an observable application defect; the dependency must not turn every
request into an implicit transaction owner. Read-only use cases close their read
transaction without producing domain effects.

## Idempotent commands and savepoints

`IdempotencyExecutor.execute` owns the adopted economic commands. The root
transaction contains the key reservation, domain changes, existing canonical
ledgers, audit, outbox and terminal safe acknowledgement. Domain actions must not
perform external work or call another root-owning executor.

Nested executor entry is rejected before the inner call assumes ownership. The
outer owner decides whether to propagate the error and roll back. A participant
that tries to commit or roll back during execution is rejected; it cannot turn
partial work into an accepted command.

The executor deliberately uses two types of savepoint:

- Reservation handles contention on the durable idempotency identity.
- Action execution allows a declared deterministic rejection to discard its
  business effects while retaining one terminal rejected acknowledgement.

An unexpected exception, failed audit/outbox write, unrelated integrity error or
transient database conflict rolls back the root transaction, including its key.
Retry uses the same intention. A committed response lost in transport is recovered
from the existing identity; it is not compensated or executed again.

`recover` has its own explicit owner for authorized result lookup and incidental
authentication activity. It runs no action and reserves no new identity.
`purge_expired_payloads` owns maintenance; its private helper participates without
an independent rollback. Maintenance retains the identity and immutable response
fingerprint and may clear only a safely reconstructible expired payload.

Inventory first-row creation uses a savepoint inside the caller's transaction.
Only the named natural-key uniqueness race is recovered there. Existing ordered
locks and complete write sets remain as specified in [concurrency.md](concurrency.md).
No owner or failure-cleanup wrapper releases those locks before the command ends.

## Administrative services and error translation

Administrative owners retain their existing commit points and acquire explicit
failure cleanup. Helpers for checklist replacement, permissions, contacts, lines,
balances and audit/outbox remain participants. Do not place a committing wrapper
around each helper or call an independently committing service from another
owner's unit of work.

`AdminPriceCatalogService.update_price` is a delegating entry point, not a second
owner. It selects either `AdminProductCatalogService.update_product` or
`AdminProductClassCatalogService.update_class`; that selected method owns the one
commit and failure cleanup. The following detail query does not commit again.

Translate an `IntegrityError` to a known business conflict only when PostgreSQL
reports SQLSTATE `23505` and the expected constraint name. An integrity error in
audit, outbox, a foreign key, a check constraint or an unrelated unique index is
not evidence that the requested domain entity already exists. Such failures
propagate through the owner's rollback and the canonical safe HTTP error mapping.

The exception boundary includes the first INSERT flush, not only the later commit.
Cleaning-log and sanitary-verification folios and equipment codes have direct
PostgreSQL regressions for this ordering. Their known uniqueness conflicts retain
the business error; the shared failure guard still owns the single rollback.

Reprint and report-export owners persist their existing audit records. Construct
the response while still within the transaction where practical, so a failed
projection does not masquerade as an uncommitted audit operation. This does not
make printer output or a network response transactional with PostgreSQL.

## Authentication and independent security evidence

Session lifecycle commands own their successful state transitions, user security
changes, audit and outbox. `last_login_at` must persist on successful login.
The plan's historical `AuthService.login` reference no longer identifies the
current implementation. `SessionService.login` already persisted `last_login_at`
in the accepted base; 039 adds direct persistence evidence rather than claiming
to repair a missing commit there. The reviewed routes revealed no omitted success
commit. The changes normalize failure cleanup, ownership, helper composition and
constraint-specific error translation.
Low-level rate-limit, session-creation, activity and revocation helpers participate
in a documented caller's transaction; a rate-limit helper must not secretly commit
another use case's pending writes.

Some security rejections deliberately commit security state before returning an
error: failed authentication counters, a resulting block or revocation, and the
associated evidence. Failure cleanup after that intentional commit cannot undo it.
The matrix identifies these paths separately from successful domain operations.

Authorization denial auditing first rolls back the failed business request and
uses a separate short-lived session for the denial record. That independent audit
does not confirm any business effects. Tests must distinguish the allowed denial
record from unexpected additional domain rows.

Privileged bootstrap and recovery services prepare changes without committing.
Their CLI owner coordinates protected recovery material and the explicit database
commit. Private-file publication is an external effect with its existing failure
and recovery rules; it is not a cross-resource ACID transaction. Development seed,
credential rotation and guarded test fixtures have separate declared owners.

## Audit, outbox and worker boundary

`AuditRecorder.record` and `OutboxWriter.append` only add rows to the supplied
session. DEC-18 requires business effects and the events describing them to commit
together. An outbox failure must not leave a successful sale, stock movement or
administrative change without its required trace.

The independent worker currently owns a read transaction through
`OutboxPoller.poll_once` and `Engine.begin`. Its `FOR UPDATE SKIP LOCKED` query
releases locks when that transaction ends. It neither claims events durably nor
marks them processed. Logging a selected event is not processing it. Handler,
retry, consumer identity and acknowledgement implementation remain later worker
tasks; this convention does not claim DEC-18 processing acceptance prematurely.

## Verification and boundaries

The AST inventory records database calls to `commit`, `rollback`, `flush`, `begin`
and `begin_nested`, with their containing symbol, receiver, role and owner. It
includes API/worker source, bootstrap, operations CLI and explicitly labelled
test-only helpers. File-stream `flush` and domain methods named `commit` are not
database transaction sites. Static coverage is complemented by PostgreSQL failure
tests; it does not prove arbitrary control-flow correctness on its own.

Acceptance distinguishes unexpected failure (no new domain, audit, outbox or
idempotency result) from a deterministic rejection (no domain effect, one permitted
terminal result) and an independently committed security observation. Session
reuse after rollback must remain safe. Successful commit followed by response loss
must retain all effects and allow result recovery.

ZM-FIN-039 does not add missing ledgers, change close totals, complete physical POS
effects or introduce a new worker processor. Order-payment ledger integration
remains 042. Request/event correlation remains 040, including the separately
recorded equipment-maintenance identifier issue. The 19 administrative idempotency
gaps in 077/080/085, reconciliation gaps and purchase PATCH UI gap remain open.
