# ZeroMerma POS v1 Release Checklist

## A. Schema and migrations

- [ ] `alembic upgrade head` runs successfully on a clean database
- [ ] no migration branch divergence remains unresolved
- [ ] current DB revision matches latest POS head
- [ ] new POS tables/columns are visible and usable:
    - [ ] `cash_session.expected_cash`
    - [ ] `cash_session.reconciliation_snapshot`
    - [ ] `sale.voided_at`
    - [ ] `sale.voided_by_id`
    - [ ] `sale.refunded_at`
    - [ ] `sale.refunded_by_id`
    - [ ] `sale.reversal_reason`
    - [ ] `sale.reversal_snapshot`
    - [ ] `pos_audit_event`
- [ ] `inventory_movement` reason check includes:
    - [ ] `POS_FINISHED_GOODS_STOCK_IN`

## B. Core functional flows

- [ ] open cash session
- [ ] atomic checkout with CASH
- [ ] atomic checkout with CARD
- [ ] atomic checkout with TRANSFER
- [ ] sale reprint from receipt snapshot
- [ ] order creation without inventory mutation
- [ ] order checkout preview from frozen snapshots
- [ ] order delivery via checkout
- [ ] manual order delivery remains exceptional and restricted
- [ ] finished-goods stock can be registered from POS
- [ ] stock newly registered through POS becomes immediately sellable
- [ ] full cash-session close reconciliation
- [ ] void OPEN unpaid sale
- [ ] refund PAID sale
- [ ] audit event persistence for critical POS actions

## C. RBAC

- [ ] cashier can open cash session
- [ ] cashier can close own cash session
- [ ] cashier cannot close another cashier session
- [ ] admin can close any accessible cash session
- [ ] cashier cannot void sale
- [ ] cashier cannot refund sale
- [ ] admin can read audit events
- [ ] cashier cannot read audit events
- [ ] admin can register finished-goods stock from POS
- [ ] cashier can register finished-goods stock from POS
- [ ] baker cannot register finished-goods stock from POS

## D. Contract integrity

- [ ] official payment methods are exactly:
    - [ ] `CASH`
    - [ ] `CARD`
    - [ ] `TRANSFER`
    - [ ] `OTHER`
- [ ] official POS v1 route surface exists in OpenAPI
- [ ] documented exceptional routes are still marked and constrained
- [ ] backend error envelope remains consistent

## E. Regression suite

- [ ] `test_pos_checkout_endpoints.py`
- [ ] `test_pos_order_checkout_endpoints.py`
- [ ] `test_cash_session_endpoints.py`
- [ ] `test_pos_sale_reversal_endpoints.py`
- [ ] `test_pos_rbac_endpoints.py`
- [ ] `test_pos_audit_endpoints.py`
- [ ] `test_pos_stock_endpoints.py`
- [ ] `test_auth_context_contracts.py`
- [ ] `test_domain_error_surface_endpoints.py`
- [ ] `test_pos_payment_method_contracts.py`
- [ ] `test_pos_contract_surface.py`

## F. Final engineering closeout

- [ ] no failing Ruff checks
- [ ] no failing Black checks
- [ ] no unintended route drift
- [ ] no unresolved import drift between core/models/services/schemas
- [ ] no known blocker preventing cashier day-to-day operation
- [ ] remaining non-v1 backlog clearly separated from release scope

## G. Explicit non-v1 backlog

These items must remain explicitly out of POS v1 release scope unless promoted intentionally:

- [ ] split tender
- [ ] partial refunds
- [ ] partial returns by item
- [ ] discounts/promotions engine
- [ ] exchange flows
- [ ] reopen sale
- [ ] full removal of manual `/deliver`
- [ ] advanced analytics beyond audit persistence
