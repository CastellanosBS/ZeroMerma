# Payment terminal boundary and activation gate

ZM-FIN-046 is partially implemented. No real BBVA adapter is registered and no
integrated payment button is enabled. Current CARD commands remain operator
accounting records for independently performed payments. They are neither BBVA
capture evidence nor bank settlement. This document does not certify hardware,
PCI compliance or production readiness. `FINAL_PILOT_START=POSTPONED` while the
approved BBVA gate remains unmet.

## Implemented technical protocol

An authorized source workflow must first admit a PENDING, PROVIDER_INTEGRATED
CARD entry with its immutable business entitlement, amount and actual open turn.
The current sales/order/refund UI does not yet implement that producer. The
terminal endpoint cannot invent the entry or accept a client success declaration.

`POST /v1/payment-terminal/operations` requires its own stable UUIDv7 idempotency key,
distinct from the source command's globally unique key, entry identity and approved
terminal binding. Its stored 202 acknowledgement is
admission only. The source-specific authority, branch, station, actor, provider
environment and evidence binding are validated. Replays return that same admission.
`GET /v1/payment-terminal/operations/{id}` reads current state separately.

The first dispatch revalidates that the bound terminal is still active and that
its immutable identity and approval evidence match the registered adapter. Recovery
of an already sent operation can query its original identity after binding
deactivation; it cannot send a replacement charge.

Dispatch commits a durable PROCESSING claim before contacting the adapter. There
are no held database transaction locks during the provider request. Concurrent or
later dispatch of PROCESSING/UNKNOWN queries the same provider identity; it never
issues a new capture. Provider timeout leaves uncertainty, not a rejection. A
separate authorized transaction applies authenticated, matching provider evidence
and writes audit/outbox atomically. Failure after provider success leaves the same
durable intention for reconciliation. Permission is refreshed after contact.

AUTHORIZED is not captured money. Only matching CAPTURED/REFUNDED evidence confirms
the actual entry. Duplicate authenticated events reuse their immutable evidence.
A new event with a contradictory terminal state records a discrepancy without
rewriting the first confirmed effect. Reusing an event identity with different
content or changing the bound provider operation identity returns409 without
appending new evidence. Capture does not prove subsequent bank settlement. UNKNOWN and
other admitted unresolved legs remain excluded from settled totals and block the
actual turn's close.

The callback interface is internal to a concrete authenticated adapter. There is
no unauthenticated public webhook or caller-supplied success endpoint. Raw payloads,
PAN, CVV and credentials are not accepted by HTTP DTOs or persisted as evidence.
Provider references are opaque; their financial scope, amount/currency and identity
must match the admitted operation. Refund admission serializes against its original
capture and reserves uncertain refunds within the remaining captured amount.

## Required before BBVA activation

1. Obtain the exact model/firmware, integration service and topology, official
   protocol/SDK, sandbox access, credential procedure and hardware/PCI evidence.
   Evidence UUIDs in local records are references, not a certification authority.
2. Implement the actual adapter and callback authentication/polling, bounded network
   timeouts, secret rotation and provider-specific reconciliation. Persist late
   provider evidence after a turn closes through an explicit reconciliation flow
   without rewriting its frozen financial snapshot; current continuations require
   an open actual turn. Add a close-resolution gate for contradictory provider
   evidence, whose discrepancy currently preserves the first confirmed entry.
3. Complete integrated source admission and recovery for sales, orders and refunds;
   provide POS/Backoffice states for waiting, uncertainty, resolution and terminal
   binding. Never issue a paid receipt before verified capture.
4. Implement supported VOID, fees, bank settlement and chargeback handling from the
   actual contract. No generic reversal or manual-fallback permission is invented.
   An uncertain integrated charge must not trigger a second manual charge.
5. Exercise sandbox and real hardware approval/rejection, offline recovery, lost
   result, simultaneous callback/poll, partial refund and close blockers. Record
   the deployment, firmware, identities and reconciled amounts before approval.

The injected fake in `test_payment_terminal.py` verifies the local boundary,
concurrency and recovery. It is never registered by production application code.
Passing those tests does not complete ZM-FIN-046 or unlock Pilot Ready.
