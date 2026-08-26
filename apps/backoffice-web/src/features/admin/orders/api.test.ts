import { describe, expect, it, vi } from "vitest";

import {
  buildAdminOrdersListPath,
  cancelAdminOrder,
  deliverAdminOrder,
  fetchAdminOrderDetail,
  fetchAdminOrders,
  markAdminOrderReady,
  mapAdminOrderFromApi,
} from "./api";

const apiBase = "http://localhost:8000";

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status: 200,
    ...init,
  });
}

const listItem = {
  advance_amount: "10.00",
  branch_id: "branch-1",
  branch_name: "Main Branch",
  cancellation_refund_amount: "10.00",
  cancellation_refund_eligible: true,
  created_at_utc: "2026-05-20T10:00:00Z",
  created_by_user_full_name: "Cashier",
  created_by_user_id: "user-1",
  currency_code: "MXN",
  customer_name: "Sergio",
  customer_phone: "6621234567",
  folio: "PED-123",
  id: "order-1",
  line_count: 2,
  payment_state: "PARTIAL_DEPOSIT",
  remaining_balance_amount: "24.00",
  requested_for_at: "2026-05-21T18:00:00Z",
  status: "PENDING",
  total_amount: "34.00",
  total_units: "5.000",
  updated_at_utc: "2026-05-20T10:05:00Z",
  warning_state: null,
  workstation_code: "POS-01",
  workstation_id: "workstation-1",
  workstation_name: "Front Register",
};

const listResponse = {
  backend_contract: {
    cancel_endpoint: "POST /v1/admin/orders/{order_id}/cancel",
    create_endpoint: null,
    deliver_endpoint: "POST /v1/admin/orders/{order_id}/deliver",
    detail_endpoint: "GET /v1/admin/orders/{order_id}",
    financial_capture_endpoint: null,
    list_endpoint: "GET /v1/admin/orders",
    mark_ready_endpoint: "POST /v1/admin/orders/{order_id}/mark-ready",
  },
  filter_options: {
    branches: [{ id: "branch-1", label: "Main Branch" }],
    cashiers: [{ id: "user-1", label: "Cashier" }],
    payment_states: [{ id: "PARTIAL_DEPOSIT", label: "Anticipo parcial" }],
    statuses: [{ id: "PENDING", label: "Pendiente" }],
    workstations: [{ id: "workstation-1", label: "Front Register (POS-01)" }],
  },
  is_backend_connected: true,
  items: [listItem],
  metrics: {
    active_orders: 1,
    canceled_orders: 0,
    deposits_received_amount: "10.00",
    due_today: 0,
    outstanding_balance_amount: "24.00",
    ready_orders: 0,
  },
  page: 1,
  page_size: 25,
  total: 1,
};

const detailResponse = {
  available_actions: {
    can_cancel: true,
    can_capture_balance: false,
    can_create_from_backoffice: false,
    can_deliver: false,
    can_mark_ready: true,
    financial_action_note: null,
    requires_cash_session_for_financial_action: false,
    requires_settlement_on_delivery: false,
  },
  backend_contract: listResponse.backend_contract,
  customer: { name: "Sergio", notes: "Sin azucar", phone: "6621234567" },
  lines: [
    {
      id: "line-1",
      line_number: 1,
      line_total_amount: "24.00",
      product_class_code: "PAN-DULCE",
      product_class_id: "class-1",
      product_class_name: "Pan dulce",
      product_code: "CONCHA",
      product_id: "product-1",
      product_name: "Concha",
      quantity: "2.000",
      unit_price: "12.00",
    },
  ],
  operational_context: {
    active_cash_session_id: "cash-1",
    branch_id: "branch-1",
    branch_name: "Main Branch",
    canceled_by_user_full_name: null,
    created_by_user_full_name: "Cashier",
    created_by_user_id: "user-1",
    delivered_by_user_full_name: null,
    workstation_code: "POS-01",
    workstation_id: "workstation-1",
    workstation_name: "Front Register",
  },
  overview: {
    advance_amount: "10.00",
    branch_id: "branch-1",
    branch_name: "Main Branch",
    canceled_at: null,
    cancellation_reason: null,
    cancellation_refund_amount: "10.00",
    cancellation_refund_eligible: true,
    created_at_utc: "2026-05-20T10:00:00Z",
    currency_code: "MXN",
    customer_name: "Sergio",
    customer_phone: "6621234567",
    delivered_at: null,
    folio: "PED-123",
    id: "order-1",
    payment_state: "PARTIAL_DEPOSIT",
    remaining_balance_amount: "24.00",
    requested_for_at: "2026-05-21T18:00:00Z",
    status: "PENDING",
    total_amount: "34.00",
    updated_at_utc: "2026-05-20T10:05:00Z",
  },
  payments: [
    {
      amount: "10.00",
      currency_code: "MXN",
      id: "payment-1",
      payment_method_code: "CASH",
      payment_type: "ADVANCE",
      recorded_at_utc: "2026-05-20T10:00:00Z",
      recorded_by_user_full_name: "Cashier",
      recorded_by_user_id: "user-1",
      sequence: 1,
    },
  ],
  related_documents: [],
  timeline: [
    {
      description: "PED-123",
      key: "created",
      label: "Pedido creado",
      occurred_at: "2026-05-20T10:00:00Z",
    },
  ],
};

describe("admin orders API", () => {
  it("builds compact list query params", () => {
    expect(
      buildAdminOrdersListPath({
        branchId: "branch-1",
        cashierId: "all",
        dateFrom: "2026-05-20",
        dateTo: "2026-05-21",
        page: 2,
        pageSize: 50,
        paymentState: "BALANCE_PENDING",
        search: " PED-123 ",
        status: "READY",
        workstationId: "workstation-1",
      }),
    ).toBe(
      "/v1/admin/orders?page=2&page_size=50&branch_id=branch-1&date_from=2026-05-20T00%3A00%3A00.000Z&date_to=2026-05-21T23%3A59%3A59.999Z&payment_state=BALANCE_PENDING&search=PED-123&status=READY&workstation_id=workstation-1",
    );
  });

  it("maps list item shape", () => {
    expect(mapAdminOrderFromApi(listItem).customerName).toBe("Sergio");
    expect(mapAdminOrderFromApi(listItem).paymentState).toBe("PARTIAL_DEPOSIT");
  });

  it("fetches list detail and action endpoints", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse(listResponse))
      .mockResolvedValueOnce(jsonResponse(detailResponse))
      .mockResolvedValueOnce(jsonResponse(detailResponse))
      .mockResolvedValueOnce(jsonResponse(detailResponse))
      .mockResolvedValueOnce(jsonResponse(detailResponse));

    const list = await fetchAdminOrders("token", {
      page: 1,
      pageSize: 25,
      search: "",
      status: "all",
    });
    const detail = await fetchAdminOrderDetail("token", "order-1");
    await markAdminOrderReady("token", "order-1");
    await deliverAdminOrder("token", "order-1");
    await cancelAdminOrder("token", "order-1");

    expect(list.total).toBe(1);
    expect(detail.lines[0].productName).toBe("Concha");
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      `${apiBase}/v1/admin/orders/order-1/mark-ready`,
      expect.objectContaining({ method: "POST" }),
    );
    fetchMock.mockRestore();
  });
});
