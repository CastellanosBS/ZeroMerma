import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildAdminPurchasesListPath,
  cancelAdminPurchase,
  confirmAdminPurchase,
  createAdminDirectEntry,
  createAdminPurchase,
  fetchAdminPurchaseDetail,
  fetchAdminPurchases,
  receiveAdminPurchase,
} from "./api";
import type { AdminPurchaseListFilters } from "./types";

const filters: AdminPurchaseListFilters = {
  discrepancyState: "all",
  page: 1,
  pageSize: 25,
  productKind: "all",
  search: "",
  status: "all",
  warningState: "all",
};

const apiPurchaseItem = {
  branch_id: "branch-1",
  branch_name: "Centro",
  created_at: "2026-05-20T10:00:00Z",
  document_date: "2026-05-20T10:00:00Z",
  document_type: "PURCHASE",
  external_document_number: "REM-100",
  folio: "CMP-100",
  has_discrepancy: true,
  id: "purchase-1",
  line_count: 1,
  operator_name: "Admin",
  received_at: null,
  received_unit_count: "2.000",
  status: "PARTIALLY_RECEIVED",
  supplier_id: "supplier-1",
  supplier_name: "Harinas del Centro",
  total_amount: "120.0000",
  warning_state: "critical",
  warnings: [{ code: "receipt_discrepancy", message: "Diferencia de recepcion.", severity: "critical" }],
} as const;

const apiPurchaseDetail = {
  available_actions: {
    can_cancel: false,
    can_confirm: false,
    can_edit: false,
    can_receive: true,
    can_view_movements: true,
  },
  cost_summary: {
    currency: "MXN",
    received_total: "24.0000",
    subtotal: "120.0000",
    taxes: null,
    total: "120.0000",
  },
  inventory_impact: {
    integration_available: true,
    movements: [
      {
        balance_after: "2.000",
        branch_id: "branch-1",
        direction: "IN",
        id: "movement-1",
        location_code: "BACKROOM",
        movement_type: "PURCHASE_RECEIPT",
        product_id: "product-1",
        quantity: "2.000",
        source_document_id: "receipt-1",
        source_document_type: "PURCHASE_RECEIPT",
        unit_of_measure: "KG",
      },
    ],
    notes: null,
  },
  lines: [
    {
      discrepancy: "8.000",
      discrepancy_reason: "Entrega parcial",
      line_status: "partial",
      line_total: "120.0000",
      notes: null,
      ordered_quantity: "10.000",
      pending_quantity: "8.000",
      product_code: "HARINA",
      product_id: "product-1",
      product_kind: "RAW_MATERIAL",
      product_name: "Harina",
      purchase_line_id: "line-1",
      received_quantity: "2.000",
      standard_cost: null,
      supplier_last_known_price: "12.0000",
      unit_cost: "12.0000",
      unit_of_measure: "KG",
    },
  ],
  overview: {
    branch_id: "branch-1",
    branch_name: "Centro",
    confirmed_at: "2026-05-20T10:10:00Z",
    created_at: "2026-05-20T10:00:00Z",
    created_by_user_id: "user-1",
    created_by_user_name: "Admin",
    document_date: "2026-05-20T10:00:00Z",
    document_type: "PURCHASE",
    external_document_number: "REM-100",
    external_document_type: "REMISSION",
    folio: "CMP-100",
    has_discrepancy: true,
    id: "purchase-1",
    line_count: 1,
    notes: "Compra semanal",
    received_at: "2026-05-20T11:00:00Z",
    received_unit_count: "2.000",
    status: "PARTIALLY_RECEIVED",
    supplier_id: "supplier-1",
    supplier_name: "Harinas del Centro",
    total_amount: "120.0000",
    warning_state: "critical",
  },
  receipt: {
    expected_quantity: "10.000",
    has_discrepancy: true,
    pending_quantity: "8.000",
    receipt_count: 1,
    received_quantity: "2.000",
    state: "partial",
  },
  receiving_branch: {
    branch_code: "MAIN",
    branch_id: "branch-1",
    branch_is_active: true,
    branch_name: "Centro",
    timezone: "America/Hermosillo",
  },
  related_documents: [{ document_id: "receipt-1", document_type: "PURCHASE_RECEIPT", folio: "REC-1", status: "COMMITTED" }],
  supplier_context: {
    commercial_name: "Harinas Centro",
    lead_time_days: 2,
    payment_terms_summary: "Credito 15 dias",
    primary_contact: "Ana - 555",
    status: "ACTIVE",
    supplier_id: "supplier-1",
    supplier_name: "Harinas del Centro",
  },
  warnings: [{ code: "receipt_discrepancy", message: "Diferencia de recepcion.", severity: "critical" }],
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

describe("admin purchases API boundary", () => {
  it("builds purchase list query parameters", () => {
    const path = buildAdminPurchasesListPath({
      ...filters,
      amountMax: "500",
      amountMin: "10",
      branchId: "branch-1",
      dateFrom: "2026-05-20",
      dateTo: "2026-05-21",
      discrepancyState: "with_discrepancy",
      productKind: "RAW_MATERIAL",
      search: "REM-100",
      status: "PARTIALLY_RECEIVED",
      supplierId: "supplier-1",
    });

    expect(path).toContain("/v1/admin/purchases?");
    expect(path).toContain("amount_max=500");
    expect(path).toContain("amount_min=10");
    expect(path).toContain("branch_id=branch-1");
    expect(path).toContain("date_from=2026-05-20");
    expect(path).toContain("date_to=2026-05-21");
    expect(path).toContain("discrepancy_state=with_discrepancy");
    expect(path).toContain("product_kind=RAW_MATERIAL");
    expect(path).toContain("search=REM-100");
    expect(path).toContain("status=PARTIALLY_RECEIVED");
    expect(path).toContain("supplier_id=supplier-1");
  });

  it("fetches and maps purchases from backend", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        backend_contract: undefined,
        filter_options: {
          branches: [{ id: "branch-1", label: "Centro - MAIN" }],
          operators: [{ id: "user-1", label: "Admin" }],
          product_kinds: [{ id: "RAW_MATERIAL", label: "Materia prima" }],
          products: [{ id: "product-1", label: "Harina - HARINA" }],
          statuses: [{ id: "PARTIALLY_RECEIVED", label: "Parcial" }],
          suppliers: [{ id: "supplier-1", label: "Harinas del Centro" }],
        },
        is_backend_connected: true,
        items: [apiPurchaseItem],
        metrics: {
          active_suppliers_used: 1,
          confirmed_entries: 0,
          partially_received: 1,
          pending_receipt: 1,
          total_amount: "120.0000",
          total_documents: 1,
          with_discrepancies: 1,
        },
        page: 1,
        page_size: 25,
        total: 1,
      }),
    );

    const response = await fetchAdminPurchases("token-1", filters);

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/purchases?page=1&page_size=25"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(response.items[0]?.folio).toBe("CMP-100");
    expect(response.items[0]?.hasDiscrepancy).toBe(true);
    expect(response.filterOptions.suppliers[0]?.id).toBe("supplier-1");
    expect(response.metrics.withDiscrepancies).toBe("1");
  });

  it("loads purchase detail and inventory impact", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse(apiPurchaseDetail));

    const detail = await fetchAdminPurchaseDetail("token-1", "purchase-1");

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/purchases/purchase-1"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(detail.overview.folio).toBe("CMP-100");
    expect(detail.lines[0]?.productCode).toBe("HARINA");
    expect(detail.inventoryImpact.movements[0]?.movementType).toBe("PURCHASE_RECEIPT");
  });

  it("uses create, direct entry, receive, confirm and cancel endpoints", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse(apiPurchaseDetail, 201));

    await createAdminPurchase("token-1", {
      branchId: "branch-1",
      confirmNow: true,
      externalDocumentNumber: "REM-100",
      externalDocumentType: "REMISSION",
      lines: [{ orderedQuantity: "10.000", productId: "product-1", unitCost: "12.0000" }],
      supplierId: "supplier-1",
    });
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/purchases"),
      expect.objectContaining({ body: expect.stringContaining("\"confirm_now\":true"), method: "POST" }),
    );

    await createAdminDirectEntry("token-1", {
      branchId: "branch-1",
      lines: [{ productId: "product-1", receivedQuantity: "2.000", unitCost: "12.0000" }],
      supplierId: "supplier-1",
    });
    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining("/v1/admin/purchases/direct-entry"),
      expect.objectContaining({ method: "POST" }),
    );

    await receiveAdminPurchase("token-1", "purchase-1", {
      lines: [{ discrepancyReason: "Entrega parcial", purchaseLineId: "line-1", receivedQuantity: "2.000" }],
    });
    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining("/v1/admin/purchases/purchase-1/receive"),
      expect.objectContaining({ body: expect.stringContaining("\"discrepancy_reason\":\"Entrega parcial\"") }),
    );

    await confirmAdminPurchase("token-1", "purchase-1");
    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining("/v1/admin/purchases/purchase-1/confirm"),
      expect.objectContaining({ method: "POST" }),
    );

    await cancelAdminPurchase("token-1", "purchase-1", { reason: "Duplicada" });
    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining("/v1/admin/purchases/purchase-1/cancel"),
      expect.objectContaining({ body: JSON.stringify({ reason: "Duplicada" }), method: "POST" }),
    );
  });
});
