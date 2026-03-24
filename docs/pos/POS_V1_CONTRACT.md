# ZeroMerma POS v1 Contract

## 1. Purpose

This document freezes the functional and technical perimeter of the ZeroMerma POS v1 backend.

Its goals are:

- define the official POS v1 behavior;
- identify authoritative routes and exceptional routes;
- stabilize the vocabulary used by frontend, backend, and tests;
- reduce future drift between services, routers, schemas, and operations.

This document is normative for POS v1.

---

## 2. Core domain boundary

POS v1 includes these subdomains:

- cash session
- sale
- payment
- receipt/reprint
- customer order
- order delivery through checkout
- finished-goods stock registration from POS
- cash reconciliation
- sale void
- full sale refund
- POS audit trail

Out of scope for POS v1:

- split tender
- partial refunds
- partial returns by item
- discounts/promotions engine
- exchange flows
- reopen sale
- full deprecation/removal of manual order delivery
- advanced BI/reporting beyond audit event persistence

---

## 3. Authoritative principles

### 3.1 Backend-authoritative pricing

The backend is the source of truth for effective selling price in checkout flows.

### 3.2 Snapshot-first receipts

Printable receipts and reprints prioritize persisted snapshots.

### 3.3 Order is not sale

A customer order is a commercial commitment.
A sale is the final monetized and inventory-affecting transaction.

### 3.4 Inventory moves through canonical services

Routers must not mutate inventory directly.
Inventory effects must happen through canonical service-layer flows.

### 3.5 Persistent operational audit trail

Critical POS operations must emit persisted audit events.

---

## 4. Official payment methods

POS v1 officially supports:

- `CASH`
- `CARD`
- `TRANSFER`
- `OTHER`

Rules:

- `amount_tendered` applies only to `CASH`
- non-cash methods produce `change_due = 0.00`
- canonical payment-method vocabulary must be shared across model, schema, service, and tests

---

## 5. Aggregate lifecycle rules

## 5.1 Cash session

States:

- `OPEN`
- `CLOSED`
- `CANCELED`

Rules:

- at most one `OPEN` session per branch
- opening amount must be non-negative
- closing amount represents counted real cash in drawer
- expected cash is computed as:
    - `opening_amount + session CASH payments`
- close persists reconciliation evidence

### Open authorization

Allowed roles:

- `ADMIN`
- `CASHIER`

### Close authorization

Allowed roles:

- `ADMIN`
- `CASHIER`

Additional rule:

- `CASHIER` may close only the session they opened
- `ADMIN` may close any accessible session

---

## 5.2 Sale

States:

- `OPEN`
- `PAID`
- `VOIDED`
- `REFUNDED`
- `PARTIALLY_REFUNDED`

POS v1 actively uses:

- `OPEN`
- `PAID`
- `VOIDED`
- `REFUNDED`

### Official sale creation paths

- direct sale creation: `/pos/sales`
- atomic checkout: `/pos/checkout`
- order delivery via checkout: `/pos/orders/{order_id}/deliver-checkout`

### Void

`POST /pos/sales/{sale_id}/void`

Rules:

- only for `OPEN`
- sale must have no payments
- inventory is restored
- sale becomes `VOIDED`
- reversal evidence is persisted
- audit event is emitted

### Refund

`POST /pos/sales/{sale_id}/refund`

Rules:

- only for `PAID`
- only full refund in v1
- refund creates mirrored negative payments
- inventory is restored
- sale becomes `REFUNDED`
- reversal evidence is persisted
- audit event is emitted

### Reversal authorization

Allowed role:

- `ADMIN`

---

## 5.3 Customer order

States:

- `CREATED`
- `SENT_TO_BAKERY`
- `READY`
- `DELIVERED`
- `CANCELED`

Rules:

- creating an order does not affect inventory
- order lines freeze price snapshots at creation time
- checkout preview uses frozen order snapshots
- official commercial closure path is delivery through checkout

### Official delivery route

`POST /pos/orders/{order_id}/deliver-checkout`

This route is authoritative because it:

- creates the final sale
- registers payment
- affects inventory
- persists receipt snapshot
- marks order as delivered
- links `delivered_sale_id`

### Exceptional manual delivery route

`POST /pos/orders/{order_id}/deliver`

This route is not the normal commercial flow.

Rules:

- `ADMIN` only
- requires explicit acknowledgement payload
- requires reason
- does not create sale
- keeps `delivered_sale_id = null`
- appends operational audit marker into order note

---

## 5.4 Finished-goods stock registration from POS

### Official route

`POST /pos/stock/finished-goods`

This route exists to make newly available finished goods sellable immediately at branch level.

Rules:

- branch-scoped
- `ADMIN` and `CASHIER` only
- accepts only:
    - active products
    - `is_input = false`
    - `is_sellable_in_pos = true`
- updates `inventory_balance` immediately
- appends immutable `inventory_movement` rows with reason:
    - `POS_FINISHED_GOODS_STOCK_IN`
- emits persisted audit event:
    - `FINISHED_GOODS_STOCK_REGISTERED`

This route is not a generic inventory adjustment endpoint.

---

## 6. Official POS v1 route surface

## 6.1 POS root routes

- `GET /pos/bootstrap`
- `POST /pos/checkout`
- `POST /pos/stock/finished-goods`
- `POST /pos/sales/{sale_id}/reprint`

## 6.2 Cash sessions

- `POST /pos/cash-sessions/open`
- `POST /pos/cash-sessions/{session_id}/close`
- `GET /pos/cash-sessions/current`

## 6.3 Sales

- `POST /pos/sales`
- `GET /pos/sales`
- `GET /pos/sales/{sale_id}`
- `POST /pos/sales/{sale_id}/payments`
- `POST /pos/sales/{sale_id}/void`
- `POST /pos/sales/{sale_id}/refund`

## 6.4 Orders

- `POST /pos/orders`
- `GET /pos/orders`
- `GET /pos/orders/{order_id}`
- `GET /pos/orders/queue`
- `POST /pos/orders/{order_id}/send-to-bakery`
- `POST /pos/orders/{order_id}/ready`
- `GET /pos/orders/{order_id}/checkout-preview`
- `POST /pos/orders/{order_id}/deliver-checkout`
- `POST /pos/orders/{order_id}/deliver`
- `POST /pos/orders/{order_id}/cancel`

## 6.5 POS audit

- `GET /pos/audit-events`

Policy:

- `ADMIN` only

---

## 7. Error model

POS v1 uses the backend error envelope.

Domain-facing canonical codes include:

- `DOMAIN_NOT_FOUND`
- `DOMAIN_CONFLICT`
- `DOMAIN_VALIDATION`
- `DOMAIN_INVARIANT`
- `DOMAIN_FORBIDDEN`

Authorization failures must not be expressed as generic internal errors.

---

## 8. Audit trail

POS v1 persists the following audit event types:

- `CASH_SESSION_OPENED`
- `CASH_SESSION_CLOSED`
- `SALE_CHECKOUT_COMPLETED`
- `ORDER_DELIVERED_VIA_CHECKOUT`
- `SALE_VOIDED`
- `SALE_REFUNDED`
- `FINISHED_GOODS_STOCK_REGISTERED`

Audit event read access is `ADMIN` only.

---

## 9. RBAC summary

### ADMIN

Allowed:

- open/close cash session
- create/list sales
- collect payments
- void sale
- refund sale
- create/list orders
- send order to bakery
- mark order ready
- manually deliver order
- deliver order via checkout
- register finished-goods stock from POS
- read audit events

### CASHIER

Allowed:

- open cash session
- close own cash session only
- create/list sales
- collect payments
- create/list orders
- deliver order via checkout
- register finished-goods stock from POS
- read operational POS routes for own accessible scope

Not allowed:

- void sale
- refund sale
- read audit events
- manually deliver order without sale

### BAKER

Allowed:

- bakery-side order progression where explicitly enabled

Not part of cashier POS surface.

---

## 10. Backward compatibility rules

POS v1 preserves compatibility for:

- subject-only JWT tokens (`sub` only)
- cash-session close requests that provide only `closing_amount`

Compatibility does not change the normative contract for new callers.

---

## 11. Release interpretation

A change should be considered POS v1-compatible only if it does not break:

- route surface defined above
- lifecycle rules defined above
- payment method vocabulary
- RBAC rules
- audit event persistence for critical operations
