import { describe, expect, it, vi } from "vitest";

import {
  buildAdminSalesTicketsListPath,
  fetchAdminSalesTicketDetail,
  fetchAdminSalesTickets,
  reprintAdminSalesTicket,
} from "./api";
import type { AdminSalesTicketListFilters } from "./types";

const baseFilters: AdminSalesTicketListFilters = {
  page: 1,
  pageSize: 25,
  branchId: "all",
  cashierId: "all",
  dateFrom: null,
  dateTo: null,
  maxAmount: null,
  minAmount: null,
  paymentMethod: "all",
  search: "",
  status: "all",
  workstationId: "all",
};

const apiListPayload = {
  backend_contract: {
    detail_endpoint: "GET /v1/admin/sales/tickets/{ticket_id}",
    list_endpoint: "GET /v1/admin/sales/tickets",
    reprint_endpoint: "POST /v1/admin/sales/tickets/{ticket_id}/reprint",
  },
  filter_options: {
    branches: [{ id: "branch-1", label: "Main Branch" }],
    cashiers: [{ id: "user-1", label: "Main Branch Cashier" }],
    payment_methods: [{ id: "CASH", label: "Efectivo" }],
    statuses: [{ id: "CONFIRMED", label: "Confirmados" }],
    workstations: [{ id: "workstation-1", label: "POS-01" }],
  },
  is_backend_connected: true,
  items: [
    {
      branch_id: "branch-1",
      branch_name: "Main Branch",
      cashier_id: "user-1",
      cashier_name: "Main Branch Cashier",
      currency_code: "MXN",
      folio: "TCK-123",
      has_returns: false,
      id: "ticket-1",
      item_count: 1,
      occurred_at: "2026-05-20T10:00:00Z",
      payment_methods_label: "CASH",
      payment_summary: [{ amount: "42.00", currency_code: "MXN", payment_method_code: "CASH" }],
      return_count: 0,
      return_status: "NOT_RETURNED",
      sale_id: "ticket-1",
      status: "CONFIRMED",
      total_amount: "42.00",
      unit_count: "3.000",
      workstation_code: "POS-01",
      workstation_id: "workstation-1",
      workstation_name: "Front Register 01",
    },
  ],
  metrics: {
    average_ticket_amount: "42.00",
    card_amount: "0.00",
    cash_amount: "42.00",
    ticket_count: 1,
    tickets_with_returns: 0,
    total_sales_amount: "42.00",
  },
  page: 1,
  page_size: 25,
  total: 1,
};

const apiDetailPayload = {
  lines: [
    {
      capture_mode: "PRODUCT_DIRECT",
      catalog_code: "PAN",
      catalog_name: "Pan dulce",
      discount_amount: "0.00",
      id: "line-1",
      line_total_amount: "42.00",
      physical_attribution_status: "DIRECT_ASSIGNED",
      product_class_id: null,
      product_id: "product-1",
      quantity: "3.000",
      sequence: 1,
      unit_price: "14.00",
    },
  ],
  operational_context: {
    branch_id: "branch-1",
    branch_name: "Main Branch",
    cash_session_id: "cash-session-1",
    cashier_email: "cashier@zeromerma.local",
    cashier_id: "user-1",
    cashier_name: "Main Branch Cashier",
    confirmed_at: "2026-05-20T10:00:00Z",
    created_at: "2026-05-20T10:00:00Z",
    sale_id: "ticket-1",
    workstation_code: "POS-01",
    workstation_id: "workstation-1",
    workstation_name: "Front Register 01",
  },
  overview: {
    change_amount: "0.00",
    confirmed_at: "2026-05-20T10:00:00Z",
    currency_code: "MXN",
    folio: "TCK-123",
    id: "ticket-1",
    item_count: 1,
    paid_amount: "42.00",
    return_count: 0,
    return_status: "NOT_RETURNED",
    returned_amount: "0.00",
    status: "CONFIRMED",
    subtotal_amount: "42.00",
    total_amount: "42.00",
    unit_count: "3.000",
  },
  payments: [
    {
      applied_amount: "42.00",
      change_amount: "0.00",
      currency_code: "MXN",
      id: "payment-1",
      payment_method_code: "CASH",
      received_at: "2026-05-20T10:00:00Z",
      sequence: 1,
      tendered_amount: "42.00",
    },
  ],
  printable_ticket: {
    can_reprint: true,
    note: null,
    preview_available: false,
  },
  related_documents: [],
};

describe("admin sales tickets api", () => {
  it("builds list query params", () => {
    const path = buildAdminSalesTicketsListPath({
      ...baseFilters,
      branchId: "branch-1",
      cashierId: "user-1",
      dateFrom: "2026-05-01",
      dateTo: "2026-05-20",
      maxAmount: "100",
      minAmount: "10",
      paymentMethod: "CASH",
      search: " TCK-123 ",
      status: "CONFIRMED",
      workstationId: "workstation-1",
    });

    expect(path).toContain("/v1/admin/sales/tickets?");
    expect(path).toContain("branch_id=branch-1");
    expect(path).toContain("cashier_id=user-1");
    expect(path).toContain("date_from=2026-05-01T00%3A00%3A00.000Z");
    expect(path).toContain("date_to=2026-05-20T23%3A59%3A59.999Z");
    expect(path).toContain("payment_method=CASH");
    expect(path).toContain("search=TCK-123");
    expect(path).toContain("status=CONFIRMED");
    expect(path).toContain("workstation_id=workstation-1");
  });

  it("maps list responses from backend contract", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(apiListPayload), { status: 200 }),
    );

    const response = await fetchAdminSalesTickets("token", baseFilters);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/v1/admin/sales/tickets?page=1&page_size=25",
      expect.objectContaining({ method: "GET" }),
    );
    expect(response.items[0]?.folio).toBe("TCK-123");
    expect(response.items[0]?.paymentMethodsLabel).toBe("CASH");
    expect(response.metrics.cashAmount).toBe("42.00");
    fetchMock.mockRestore();
  });

  it("loads detail and posts reprint endpoint", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify(apiDetailPayload), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(apiDetailPayload), { status: 200 }));

    const detail = await fetchAdminSalesTicketDetail("token", "ticket-1");
    await reprintAdminSalesTicket("token", "ticket-1");

    expect(detail.overview.folio).toBe("TCK-123");
    expect(detail.lines[0]?.catalogName).toBe("Pan dulce");
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://localhost:8000/v1/admin/sales/tickets/ticket-1/reprint",
      expect.objectContaining({ method: "POST" }),
    );
    fetchMock.mockRestore();
  });
});
