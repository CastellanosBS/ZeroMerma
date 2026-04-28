# Customer Communication Readiness

## Scope
- `Pedidos`
- `Tickets`
- `Devoluciones`
- shared frontend communication readiness states

## Current backend and worker state

### What exists
- transactional outbox persistence
- generic worker polling for `outbox_events`
- order, ticket, and return domain events already persisted for audit/outbox purposes

### What does not exist
- no canonical email provider integration
- no canonical SMS provider integration
- no notification delivery module in the API
- no worker consumer that dispatches customer notifications
- no notification status projection for customer-facing sends
- no frontend/backend contract for `send order ready`, `send ticket`, or `send return receipt`

## Module readiness map

| Module | Customer contact in current contract | Provider/send contract | Current state |
| --- | --- | --- | --- |
| `Pedidos` | `customer_phone` only | missing | scaffolded disabled state |
| `Tickets` | none | missing | scaffolded disabled state |
| `Devoluciones` | none | missing | scaffolded disabled state |

## Frontend behavior implemented now
- `Pedidos` exposes `Notificar pedido listo` only when the order is already `READY`.
- `Tickets` exposes disabled actions:
  - `Enviar ticket por correo`
  - `Enviar ticket por SMS`
- `Devoluciones` exposes disabled actions:
  - `Enviar comprobante de devolucion por correo`
  - `Enviar comprobante de devolucion por SMS`
- every disabled action explains the real blocker:
  - missing customer contact in the current contract
  - missing provider and delivery worker

## Canonical backend gaps for real implementation

### Orders
- dedicated command or domain action to request `order ready` notification
- optional customer email if email delivery should be supported
- delivery status model:
  - requested
  - sent
  - failed
- auditable notification records linked to the order

### Tickets
- explicit customer contact source for sale tickets
- canonical ticket-delivery command
- safe receipt payload for customer delivery
- notification history linked to the ticket

### Returns
- explicit customer contact source for return receipts
- canonical return-receipt delivery command
- notification history linked to the return document

### Worker / delivery
- outbox consumer for customer communication events
- provider adapters:
  - email
  - SMS
- retry policy
- failure logging
- provider response correlation ids

## Required production configuration
- provider selection per channel:
  - email provider
  - SMS provider
- credentials and sender identity for each provider
- delivery worker enablement
- branch-safe sender settings if branding differs by branch
- rate limiting / retry policy
- customer consent and policy rules if messaging leaves the POS domain

## Recommended next backend-first prompt
1. define canonical notification command endpoints and schemas
2. define outbox event names and worker consumption rules
3. add notification delivery status storage
4. add customer contact sourcing rules for tickets and returns
5. only then enable real send actions in POS
