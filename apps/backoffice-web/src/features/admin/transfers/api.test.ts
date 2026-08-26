import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildAdminTransferListPath,
  cancelAdminTransfer,
  createAdminTransfer,
  dispatchAdminTransfer,
  fetchAdminTransferDetail,
  fetchAdminTransfers,
  receiveAdminTransfer,
} from "./api";
import type { AdminTransferListFilters } from "./types";

const filters: AdminTransferListFilters = {
  discrepancyState: "all",
  page: 1,
  pageSize: 25,
  search: "",
  status: "all",
};

const apiTransferItem = {
  created_at: "2026-05-20T10:00:00Z",
  destination_branch_code: "NORTH",
  destination_branch_id: "branch-2",
  destination_branch_name: "North Branch",
  dispatched_at: null,
  folio: "TRF-12345678",
  has_discrepancy: false,
  id: "transfer-1",
  line_count: 1,
  operator_name: "Admin",
  origin_branch_code: "MAIN",
  origin_branch_id: "branch-1",
  origin_branch_name: "Main Branch",
  received_at: null,
  received_unit_count: null,
  requested_unit_count: "10.000",
  sent_unit_count: "10.000",
  status: "DRAFT",
  warning_state: null,
  warnings: [],
} as const;

const apiTransferDetail = {
  available_actions: {
    can_cancel: true,
    can_dispatch: true,
    can_edit: true,
    can_receive: false,
    can_view_movements: true,
  },
  destination: {
    branch_code: "NORTH",
    branch_id: "branch-2",
    branch_is_active: true,
    branch_name: "North Branch",
    timezone: "America/Hermosillo",
  },
  inventory_impact: {
    integration_available: true,
    movements: [],
    notes: null,
  },
  lines: [
    {
      difference: null,
      line_status: "pending_dispatch",
      notes: null,
      product_code: "BOLILLO",
      product_id: "product-1",
      product_kind: "FINISHED_GOOD",
      product_name: "Bolillo",
      received_quantity: null,
      requested_quantity: "10.000",
      sent_quantity: "10.000",
      shipment_line_id: "line-1",
      unit_of_measure: "PCS",
      variance_reason: null,
    },
  ],
  origin: {
    branch_code: "MAIN",
    branch_id: "branch-1",
    branch_is_active: true,
    branch_name: "Main Branch",
    timezone: "America/Hermosillo",
  },
  overview: {
    created_at: "2026-05-20T10:00:00Z",
    created_by_user_id: "user-1",
    created_by_user_name: "Admin",
    dispatched_at: null,
    folio: "TRF-12345678",
    has_discrepancy: false,
    id: "transfer-1",
    line_count: 1,
    notes: null,
    received_at: null,
    received_by_user_id: null,
    received_by_user_name: null,
    received_unit_count: null,
    requested_unit_count: "10.000",
    sent_unit_count: "10.000",
    status: "DRAFT",
  },
  receipt: {
    difference: null,
    discrepancy_reason_required: false,
    expected_total_quantity: "10.000",
    has_discrepancy: false,
    receipt_document_id: null,
    received_total_quantity: null,
    state: "not_dispatched",
  },
  related_documents: [],
  warnings: [],
} as const;

function mockJsonResponse(payload: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      headers: { "Content-Type": "application/json" },
      status,
    }),
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("admin transfers API boundary", () => {
  it("builds transfer list query parameters", () => {
    const path = buildAdminTransferListPath({
      ...filters,
      dateFrom: "2026-05-01",
      dateTo: "2026-05-20",
      destinationBranchId: "branch-2",
      discrepancyState: "with_discrepancy",
      operatorUserId: "user-1",
      originBranchId: "branch-1",
      productId: "product-1",
      search: "TRF",
      status: "IN_TRANSIT",
    });

    expect(path).toContain("/v1/admin/transfers?");
    expect(path).toContain("date_from=2026-05-01");
    expect(path).toContain("date_to=2026-05-20");
    expect(path).toContain("destination_branch_id=branch-2");
    expect(path).toContain("discrepancy_state=with_discrepancy");
    expect(path).toContain("operator_user_id=user-1");
    expect(path).toContain("origin_branch_id=branch-1");
    expect(path).toContain("product_id=product-1");
    expect(path).toContain("search=TRF");
    expect(path).toContain("status=IN_TRANSIT");
  });

  it("fetches and maps transfer list rows from backend", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        backend_contract: undefined,
        filter_options: {
          branches: [{ id: "branch-1", label: "Main Branch - MAIN" }],
          operators: [{ id: "user-1", label: "Admin" }],
          products: [{ id: "product-1", label: "Bolillo - BOLILLO" }],
          statuses: [{ id: "DRAFT", label: "Borrador" }],
        },
        is_backend_connected: true,
        items: [apiTransferItem],
        metrics: {
          cancelled_transfers: 0,
          in_transit_transfers: 0,
          pending_receipt_transfers: 0,
          received_transfers: 0,
          total_transfers: 1,
          units_in_transit: "0.000",
          with_discrepancies: 0,
        },
        page: 1,
        page_size: 25,
        total: 1,
      }),
    );

    const response = await fetchAdminTransfers("token-1", filters);

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/transfers?page=1&page_size=25"),
      expect.objectContaining({
        headers: expect.any(Headers),
        method: "GET",
      }),
    );
    expect(response.items[0]?.folio).toBe("TRF-12345678");
    expect(response.metrics.totalTransfers).toBe("1");
    expect(response.filterOptions.products[0]?.label).toBe("Bolillo - BOLILLO");
  });

  it("loads transfer detail", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse(apiTransferDetail));

    const detail = await fetchAdminTransferDetail("token-1", "transfer-1");

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/transfers/transfer-1"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(detail.overview.folio).toBe("TRF-12345678");
    expect(detail.lines[0]?.productCode).toBe("BOLILLO");
  });

  it("creates, dispatches, receives, and cancels through canonical endpoints", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse(apiTransferDetail, 201));

    await createAdminTransfer("token-1", {
      destinationBranchId: "branch-2",
      lines: [{ notes: null, productId: "product-1", quantity: "10.000" }],
      notes: "Send today",
      originBranchId: "branch-1",
    });
    await dispatchAdminTransfer("token-1", "transfer-1", "Dispatch");
    await receiveAdminTransfer("token-1", "transfer-1", {
      lines: [{ notes: null, receivedQuantity: "9.000", shipmentLineId: "line-1", varianceReason: "Missing item" }],
      notes: "Received",
    });
    await cancelAdminTransfer("token-1", "transfer-1", "Not needed");

    expect(fetchSpy).toHaveBeenNthCalledWith(
      1,
      expect.stringContaining("/v1/admin/transfers"),
      expect.objectContaining({
        body: JSON.stringify({
          destination_branch_id: "branch-2",
          lines: [{ notes: null, product_id: "product-1", quantity: "10.000" }],
          notes: "Send today",
          origin_branch_id: "branch-1",
        }),
        method: "POST",
      }),
    );
    expect(fetchSpy).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining("/v1/admin/transfers/transfer-1/dispatch"),
      expect.objectContaining({ body: JSON.stringify({ notes: "Dispatch" }), method: "POST" }),
    );
    expect(fetchSpy).toHaveBeenNthCalledWith(
      3,
      expect.stringContaining("/v1/admin/transfers/transfer-1/receive"),
      expect.objectContaining({
        body: JSON.stringify({
          lines: [
            {
              notes: null,
              received_quantity: "9.000",
              shipment_line_id: "line-1",
              variance_reason: "Missing item",
            },
          ],
          notes: "Received",
        }),
        method: "POST",
      }),
    );
    expect(fetchSpy).toHaveBeenNthCalledWith(
      4,
      expect.stringContaining("/v1/admin/transfers/transfer-1/cancel"),
      expect.objectContaining({ body: JSON.stringify({ reason: "Not needed" }), method: "POST" }),
    );
  });
});
