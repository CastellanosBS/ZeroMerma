import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildAdminWasteListPath,
  createAdminWaste,
  fetchAdminWaste,
  fetchAdminWasteDetail,
} from "./api";
import type { AdminWasteListFilters } from "./types";

const filters: AdminWasteListFilters = {
  evidenceState: "all",
  impactLevel: "all",
  locationCode: "all",
  page: 1,
  pageSize: 25,
  reasonCode: "all",
  search: "",
  status: "all",
  warningState: "all",
};

const apiWasteItem = {
  branch_id: "branch-1",
  branch_name: "Main Branch",
  created_at: "2026-05-20T10:00:00Z",
  estimated_value: null,
  folio: "WST-12345678",
  has_evidence: false,
  id: "waste-1",
  impact_level: "high",
  line_count: 1,
  location_code: "BACKROOM",
  location_name: "Fondo",
  operator_name: "Admin",
  product_code: "CONCHA-VAN",
  product_id: "product-1",
  product_kind: "FINISHED_GOOD",
  product_name: "Vanilla Concha",
  quantity: "12.000",
  reason_code: "EXPIRED",
  reason_label: "Expired",
  status: "COMMITTED",
  uom: "piece",
  warning_state: "warning",
  warnings: [{ code: "high_impact", message: "Merma marcada como alto impacto.", severity: "warning" }],
} as const;

const apiWasteDetail = {
  available_actions: {
    can_create_correction: true,
    can_edit: false,
    can_open_inventory_movement: true,
    can_print: false,
  },
  evidence: {
    attachment_supported: false,
    evidence_items: [],
    notes: "Expired batch",
  },
  inventory_impact: {
    integration_available: true,
    movements: [
      {
        balance_after: "8.000",
        direction: "OUT",
        id: "movement-1",
        location_code: "BACKROOM",
        movement_type: "WASTE_RECORD",
        product_id: "product-1",
        quantity: "12.000",
        source_document_id: "waste-1",
        source_document_type: "WASTE_RECORD",
        unit_of_measure: "piece",
      },
    ],
    notes: null,
  },
  lines: [
    {
      estimated_value: null,
      line_number: 1,
      product_code: "CONCHA-VAN",
      product_id: "product-1",
      product_kind: "FINISHED_GOOD",
      product_name: "Vanilla Concha",
      quantity: "12.000",
      uom: "piece",
    },
  ],
  overview: {
    branch_id: "branch-1",
    branch_name: "Main Branch",
    confirmed_at: "2026-05-20T10:00:00Z",
    created_at: "2026-05-20T10:00:00Z",
    folio: "WST-12345678",
    has_evidence: false,
    id: "waste-1",
    impact_level: "high",
    location_code: "BACKROOM",
    location_name: "Fondo",
    notes: "Expired batch",
    operator_id: "user-1",
    operator_name: "Admin",
    quantity: "12.000",
    reason_code: "EXPIRED",
    reason_label: "Expired",
    status: "COMMITTED",
    uom: "piece",
    warning_state: "warning",
    workstation_code: "POS-01",
    workstation_name: "Front POS",
  },
  product_inventory_context: {
    branch_id: "branch-1",
    branch_name: "Main Branch",
    class_id: "class-1",
    class_name: "Pan dulce",
    current_stock: "8.000",
    product_code: "CONCHA-VAN",
    product_id: "product-1",
    product_is_active: true,
    product_kind: "FINISHED_GOOD",
    product_name: "Vanilla Concha",
    stock_after: "8.000",
    stock_before: "20.000",
    uom: "piece",
  },
  reason_classification: {
    category: "EXPIRED",
    description: "Producto o insumo caducado.",
    label: "Expired",
    requires_evidence: false,
    requires_note: false,
  },
  related_documents: [{ document_id: "movement-1", document_type: "INVENTORY_MOVEMENT", folio: "WASTE_RECORD", status: "OUT" }],
  warnings: [{ code: "high_impact", message: "Merma marcada como alto impacto.", severity: "warning" }],
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

describe("admin waste API boundary", () => {
  it("builds waste list query parameters", () => {
    const path = buildAdminWasteListPath({
      ...filters,
      branchId: "branch-1",
      classId: "class-1",
      dateFrom: "2026-05-01",
      dateTo: "2026-05-20",
      evidenceState: "without_evidence",
      impactLevel: "high",
      locationCode: "BACKROOM",
      operatorUserId: "user-1",
      productId: "product-1",
      productKind: "FINISHED_GOOD",
      reasonCode: "EXPIRED",
      search: "WST",
      status: "COMMITTED",
      warningState: "warning",
    });

    expect(path).toContain("/v1/admin/waste?");
    expect(path).toContain("branch_id=branch-1");
    expect(path).toContain("class_id=class-1");
    expect(path).toContain("date_from=2026-05-01");
    expect(path).toContain("date_to=2026-05-20");
    expect(path).toContain("evidence_state=without_evidence");
    expect(path).toContain("impact_level=high");
    expect(path).toContain("location_code=BACKROOM");
    expect(path).toContain("operator_user_id=user-1");
    expect(path).toContain("product_id=product-1");
    expect(path).toContain("product_kind=FINISHED_GOOD");
    expect(path).toContain("reason_code=EXPIRED");
    expect(path).toContain("search=WST");
    expect(path).toContain("status=COMMITTED");
    expect(path).toContain("warning_state=warning");
  });

  it("fetches and maps waste list rows from backend", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        backend_contract: undefined,
        filter_options: {
          branches: [{ id: "branch-1", label: "Main Branch - MAIN" }],
          classes: [{ id: "class-1", label: "Pan dulce" }],
          evidence_states: [{ id: "without_evidence", label: "Sin evidencia" }],
          impact_levels: [{ id: "high", label: "Alto impacto" }],
          locations: [{ id: "BACKROOM", label: "Fondo" }],
          operators: [{ id: "user-1", label: "Admin" }],
          product_kinds: [{ id: "FINISHED_GOOD", label: "Producto terminado" }],
          products: [{ id: "product-1", label: "Vanilla Concha - CONCHA-VAN" }],
          reasons: [
            {
              code: "EXPIRED",
              display_order: 40,
              high_impact_default: false,
              label: "Expired",
              requires_evidence: false,
              requires_note: false,
            },
          ],
          statuses: [{ id: "COMMITTED", label: "Confirmada" }],
        },
        is_backend_connected: true,
        items: [apiWasteItem],
        metrics: {
          contaminated_or_damaged: 0,
          evidence_records: 0,
          estimated_value: "0",
          expired_records: 1,
          high_impact_records: 1,
          total_quantity: "12.000",
          total_records: 1,
        },
        page: 1,
        page_size: 25,
        total: 1,
      }),
    );

    const response = await fetchAdminWaste("token-1", filters);

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/waste?page=1&page_size=25"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(response.items[0]?.folio).toBe("WST-12345678");
    expect(response.items[0]?.impactLevel).toBe("high");
    expect(response.filterOptions.evidenceStates[0]?.id).toBe("without_evidence");
    expect(response.metrics.highImpactRecords).toBe("1");
  });

  it("loads waste detail", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse(apiWasteDetail));

    const detail = await fetchAdminWasteDetail("token-1", "waste-1");

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/waste/waste-1"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(detail.overview.folio).toBe("WST-12345678");
    expect(detail.productInventoryContext.stockBefore).toBe("20.000");
    expect(detail.inventoryImpact.movements[0]?.movementType).toBe("WASTE_RECORD");
  });

  it("creates waste through canonical backend endpoint", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse(apiWasteDetail, 201));

    await createAdminWaste("token-1", {
      branchId: "branch-1",
      locationCode: "BACKROOM",
      notes: "Expired batch",
      productId: "product-1",
      quantity: "12.000",
      reasonCode: "EXPIRED",
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/waste"),
      expect.objectContaining({
        body: JSON.stringify({
          branch_id: "branch-1",
          location_code: "BACKROOM",
          notes: "Expired batch",
          product_id: "product-1",
          quantity: "12.000",
          reason_code: "EXPIRED",
        }),
        method: "POST",
      }),
    );
  });
});
