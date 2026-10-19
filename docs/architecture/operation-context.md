# Operation context and causal traces

Status: ZM-FIN-040 implemented. This document records the canonical convention;
executed acceptance and the immutable-commit delivery rule are tracked separately in
[operation-context-validation.md](../implementation/operation-context-validation.md).
It implements DEC-16/17/18 without introducing another event architecture.

## Identities and authority

| Field | Meaning and authority |
|---|---|
| `request_id` | One HTTP attempt. Accept a strict UUID or generate a fresh UUID when the header is absent or invalid. Never echo an invalid header value. |
| `operation_id` | One logical operation. An authorized idempotent command or recovery uses the existing idempotency record's UUID. |
| `correlation_id` | Groups the operation's related traces. For adopted commands it equals the durable operation UUID. |
| `idempotency_key` | The caller's UUIDv7 intention key, independently validated by the command boundary. It is neither the HTTP request ID nor an event ID. |
| `causation_id` | The UUID of a known causing event. Root operations have no causing event; their value is null. |
| `event_id`, event type and schema version | Identify one persisted event and the version of its envelope/payload contract. |
| Entity type and ID | Identify the affected aggregate. Allocate/materialize its ID before recording a trace. |
| Actor ID/type | The authenticated user or an explicit system/worker/anonymous actor classification. Never infer authority from a client header. |
| `source_app` | `API` before verified authentication; `POS` or `BACKOFFICE` only from the verified session audience. Explicit non-HTTP execution uses `SYSTEM` or `WORKER`. Historical unknown origin remains `UNKNOWN`. |
| Branch, related branches, workstation and cash-session IDs | Server-resolved authorized operation context. A cross-branch operation retains its actual participating branches. |
| Occurred and recorded timestamps | The event's authoritative occurrence and persistence instants; new records obtain the recording time from PostgreSQL. These are not substitutes for causal IDs. |
| `context_version` | New canonical contexts use version 1. Existing/raw rows without proven context remain version 0. |

Client correlation, source and actor headers cannot assign trusted context. A valid
request UUID is a diagnostic identifier, not a capability or a unique business
constraint. The shared web transport generates a UUID for every attempt, including
retry and recovery, while preserving the command's original intention key.

The HTTP response exposes the accepted/generated request UUID consistently. Error
bodies retain the canonical `request_id` field. CORS must expose the response header
to both allowed web surfaces. Early security failures and exceptions must use the
same sanitized identity without copying invalid input into error text or logs.

## Propagation and lifetime

The context is a frozen snapshot. Middleware binds an attempt and clears it in
`finally`; authentication and authorized command admission replace snapshots
rather than mutating a shared object. Concurrent requests, threads and asynchronous
work cannot inherit another operation's actor, branch or IDs.

Application trace writers capture the current snapshot when constructing their
rows. The database session propagates the same values through transaction-local
PostgreSQL settings for the authentication triggers. Values are initialized for
each transaction and must not leak through a pooled connection. A trigger is a
trace producer subject to the same envelope and origin rules as an ORM writer.

The operation's selected transaction owner remains responsible for persistence.
`AuditRecorder` and `OutboxWriter` participate; adding context does not authorize a
hidden commit, rollback or independently committed domain event. The convention
in [transaction-boundaries.md](transaction-boundaries.md) applies unchanged.

Authorization denial is the deliberate exception already defined there: discard
the failed business transaction, then persist the security observation in its
separate audit transaction. Capture the safe original context before cleanup and
bind it explicitly to that short-lived transaction. A denial does not prove a
business mutation succeeded.

## Replay and uncertain results

An authorized replay or recovery retains the durable command operation/correlation
UUID and the current attempt's request UUID. It does not rewrite the original
audit/outbox rows, first-request identity, immutable acknowledgement or response
fingerprint. It produces no second business event merely because HTTP was retried.
The domain callback still does not run on replay.

An error before commit rolls back the traces together with the domain effects.
An error after commit cannot reverse the completed operation; result recovery
continues to use its original identity. Context binding must be restored after
both paths. Idempotency behavior and context comparisons remain defined in
[idempotency.md](idempotency.md).

No timestamp, folio, human name or current mutable entity state is sufficient to
invent a missing parent event. Causation remains null when no causing event is
known. Correlation alone does not establish causal ordering.

## Historical rows and migration

The additive `20261018_0043_operation_context` migration follows the existing 0042
idempotency revision.
Existing audit/outbox rows retain their IDs, payloads, timestamps and state.
They receive `context_version = 0` and `source_app = UNKNOWN`; unproven context
and recording instants remain null. Historical/raw outbox schema version is 0;
the migration does not infer a version from event-name text or label historical POS
activity as Backoffice, invent request/operation/causation IDs, or promote demo
rows into productive history. New canonical rows use context version 1 and the
outbox's schema version 1 envelope. A context-version-1 outbox row must have a
positive schema version. Existing `AuditLog.id/action/resource_type/resource_id`
and `OutboxEvent.id/event_name/aggregate_type/aggregate_id` provide the stable
event identity, type and affected entity; they are not duplicated into another
event table.

Existing event payload contracts and historical readers remain identifiable by
version. Adding envelope metadata is not permission to silently rewrite domain
payloads. A historical schema upgrade, an analytical backfill and a new business
event are distinct records under DEC-18/19.

Migration acceptance requires an empty database, the supported upgrade chain,
0042 historical fixtures, model/schema parity and guarded dump/restore evidence.
The guarded downgrade refuses to discard version-1 evidence. Use the isolated harness described in
[database-migrations.md](../operations/database-migrations.md). A rollback strategy
must preserve business data and trace identity; discarding the added metadata is
not an acceptable substitute for restore or a forward correction.

## Privacy and structured logs

Structured logs include only approved context IDs, event type/version, source,
result classification and safe operational metadata. They do not include raw
request bodies, complete headers, cookies, CSRF/reset/recovery credentials,
passwords, payment authentication data, arbitrary query strings or unrestricted
`extra` objects. Personal contact data and free-text notes are not context fields.

Technical logs and durable audit have different purposes; neither substitutes for
the other. Context enrichment does not broaden access to audit/export data or
relax branch/RBAC enforcement. Redaction is tested at actual logging and error
boundaries, including malformed request IDs, rather than inferred from a field's
name. Version 1 domain payloads already containing historical personal fields are
not claimed to be fully minimized merely because their envelope is safe.

The independent worker logs an explicit worker execution boundary and safe
selected-event context while retaining the event producer's origin. Reading and
logging an event does not claim or process it. The current poller still performs
no handler call, durable acknowledgement, retry scheduling or state transition.

## Retained scope

The new outbox producers use the existing operation's commit, with these payload
boundaries. They add no handler or external action:

| Event family | Payload boundary |
|---|---|
| `admin.input_supply.supplier_relation.updated.v1` | Product/supplier IDs and relation ID when already materialized |
| `admin.supplier.contact.created.v1`, `.updated.v1` | Supplier/contact IDs; no name or contact channel |
| `admin.supplier.product.linked.v1`, `.updated.v1` | Supplier/product/relation IDs and active state |
| `admin.supplier.branch.updated.v1` | Supplier/branch IDs and active state |
| `admin.setting.updated.v1`, `.reset.v1` | Setting key and scope; no old/new value or change note |
| `admin.report.exported.v1` | Report code, format and row count; no rows or filters |
| `ticket.reprinted.v1` | Ticket ID; no printable body or customer/operator personal fields |

The report event records the generated export operation, not receipt by another
party. The ticket event follows the existing audit action name and records an
accepted application reprint request; it does not certify successful physical
printing. Transport or printer failures after commit cannot undo these records.

- 087 implements durable outbox processing, leases, retries and dead letters.
- 093 builds the full event catalog and deterministic analytical projections.
- 109 implements production metrics, tracing, probes, dashboards and alerts.
- Availability, ledgers, reconciliation, administrative idempotency and other
  unfinished product functions retain their own tasks and matrix gaps.

040 establishes correct trace context for existing behavior. It does not declare
the worker functional, event delivery exactly-once, complete data minimization of
all historical payloads, a new retention policy, or production readiness.
