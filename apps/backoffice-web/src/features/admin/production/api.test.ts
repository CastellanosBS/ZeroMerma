import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildAdminProductionListPath,
  cancelAdminProduction,
  completeAdminProduction,
  createAdminProduction,
  fetchAdminProduction,
  fetchAdminProductionDetail,
  startAdminProduction,
} from "./api";
import type { AdminProductionListFilters } from "./types";

const filters: AdminProductionListFilters = {
  page: 1,
  pageSize: 25,
  search: "",
  status: "all",
  varianceState: "all",
  warningState: "all",
};

const apiProductionItem = {
  actual_output_qty: null,
  branch_id: "branch-1",
  branch_name: "Main Branch",
  completed_at: null,
  folio: "PROD-12345678",
  id: "production-1",
  operator_name: "Admin",
  planned_at: "2026-05-20T10:00:00Z",
  planned_output_qty: "20.000",
  product_code: "CONCHA-VAN",
  product_id: "product-1",
  product_name: "Vanilla Concha",
  recipe_id: "recipe-1",
  recipe_name: "Base",
  started_at: null,
  status: "DRAFT",
  variance_percent: null,
  variance_qty: null,
  warning_state: "critical",
  warnings: [{ code: "raw_material_shortage", message: "Faltan insumos.", severity: "critical" }],
} as const;

const apiProductionDetail = {
  actual_consumption: [
    {
      consumed_qty: null,
      difference_qty: null,
      expected_qty: "4.000",
      input_product_code: "RAW-FLOUR",
      input_product_id: "raw-1",
      input_product_name: "Flour",
      uom: "kg",
    },
  ],
  available_actions: {
    can_cancel: true,
    can_complete: false,
    can_edit: true,
    can_start: true,
    can_view_movements: true,
  },
  inventory_impact: {
    integration_available: true,
    movements: [],
    notes: null,
  },
  output_yield: {
    actual_output_qty: null,
    planned_output_qty: "20.000",
    uom: "piece",
    variance_percent: null,
    variance_qty: null,
    variance_reason: null,
  },
  overview: {
    actual_output_qty: null,
    branch_id: "branch-1",
    branch_name: "Main Branch",
    cancelled_at: null,
    completed_at: null,
    completed_by_user_id: null,
    completed_by_user_name: null,
    created_at: "2026-05-20T10:00:00Z",
    created_by_user_id: "user-1",
    created_by_user_name: "Admin",
    folio: "PROD-12345678",
    id: "production-1",
    notes: null,
    planned_at: "2026-05-20T10:00:00Z",
    planned_output_qty: "20.000",
    started_at: null,
    started_by_user_id: null,
    started_by_user_name: null,
    status: "DRAFT",
    variance_percent: null,
    variance_qty: null,
    variance_reason: null,
    warning_state: "critical",
  },
  planned_inputs: [
    {
      available_qty: "0.000",
      input_product_code: "RAW-FLOUR",
      input_product_id: "raw-1",
      input_product_name: "Flour",
      required_qty: "4.000",
      shortage_qty: "4.000",
      standard_cost: "20.0000",
      status: "unavailable",
      uom: "kg",
    },
  ],
  product_recipe: {
    product_code: "CONCHA-VAN",
    product_id: "product-1",
    product_is_active: true,
    product_kind: "FINISHED_GOOD",
    product_name: "Vanilla Concha",
    product_unit_of_measure: "piece",
    recipe_id: "recipe-1",
    recipe_is_active: true,
    recipe_name: "Base",
    recipe_yield_qty: "10.000",
    recipe_yield_uom: "piece",
  },
  related_documents: [{ document_id: "recipe-1", document_type: "RECIPE", folio: "Base", status: "active" }],
  warnings: [{ code: "raw_material_shortage", message: "Faltan insumos.", severity: "critical" }],
  waste_scrap: {
    integration_available: false,
    notes: "Waste/scrap is represented as production yield variance; dedicated merma documents are pending contract.",
    records: [],
  },
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

describe("admin production API boundary", () => {
  it("builds production list query parameters", () => {
    const path = buildAdminProductionListPath({
      ...filters,
      branchId: "branch-1",
      dateFrom: "2026-05-01",
      dateTo: "2026-05-20",
      operatorUserId: "user-1",
      productId: "product-1",
      recipeId: "recipe-1",
      search: "PROD",
      status: "IN_PROGRESS",
      varianceState: "with_variance",
      warningState: "critical",
    });

    expect(path).toContain("/v1/admin/production?");
    expect(path).toContain("branch_id=branch-1");
    expect(path).toContain("date_from=2026-05-01");
    expect(path).toContain("date_to=2026-05-20");
    expect(path).toContain("operator_user_id=user-1");
    expect(path).toContain("product_id=product-1");
    expect(path).toContain("recipe_id=recipe-1");
    expect(path).toContain("search=PROD");
    expect(path).toContain("status=IN_PROGRESS");
    expect(path).toContain("variance_state=with_variance");
    expect(path).toContain("warning_state=critical");
  });

  it("fetches and maps production list rows from backend", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        backend_contract: undefined,
        filter_options: {
          branches: [{ id: "branch-1", label: "Main Branch - MAIN" }],
          operators: [{ id: "user-1", label: "Admin" }],
          products: [{ id: "product-1", label: "Vanilla Concha - CONCHA-VAN" }],
          recipes: [{ id: "recipe-1", label: "Vanilla Concha - Base" }],
          statuses: [{ id: "DRAFT", label: "Pendiente" }],
        },
        is_backend_connected: true,
        items: [apiProductionItem],
        metrics: {
          completed_batches: 0,
          in_progress_batches: 0,
          pending_batches: 1,
          produced_units: "0.000",
          total_batches: 1,
          with_shortages: 1,
          with_variance: 0,
        },
        page: 1,
        page_size: 25,
        total: 1,
      }),
    );

    const response = await fetchAdminProduction("token-1", filters);

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/production?page=1&page_size=25"),
      expect.objectContaining({
        headers: expect.any(Headers),
        method: "GET",
      }),
    );
    expect(response.items[0]?.folio).toBe("PROD-12345678");
    expect(response.items[0]?.warnings[0]?.code).toBe("raw_material_shortage");
    expect(response.metrics.pendingBatches).toBe("1");
  });

  it("loads production detail", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse(apiProductionDetail));

    const detail = await fetchAdminProductionDetail("token-1", "production-1");

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/production/production-1"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(detail.overview.folio).toBe("PROD-12345678");
    expect(detail.productRecipe.productCode).toBe("CONCHA-VAN");
    expect(detail.plannedInputs[0]?.status).toBe("unavailable");
  });

  it("creates, starts, completes, and cancels through canonical endpoints", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse(apiProductionDetail, 201));

    await createAdminProduction("token-1", {
      branchId: "branch-1",
      notes: "Bake today",
      plannedAt: "2026-05-20T10:00:00Z",
      plannedOutputQty: "20.000",
      productId: "product-1",
      recipeId: "recipe-1",
    });
    await startAdminProduction("token-1", "production-1", "Start");
    await completeAdminProduction("token-1", "production-1", {
      actualOutputQty: "18.000",
      notes: "Completed",
      varianceReason: "Shrinkage",
    });
    await cancelAdminProduction("token-1", "production-1", "Not needed");

    expect(fetchSpy).toHaveBeenNthCalledWith(
      1,
      expect.stringContaining("/v1/admin/production"),
      expect.objectContaining({
        body: JSON.stringify({
          branch_id: "branch-1",
          notes: "Bake today",
          planned_at: "2026-05-20T10:00:00Z",
          planned_output_qty: "20.000",
          product_id: "product-1",
          recipe_id: "recipe-1",
        }),
        method: "POST",
      }),
    );
    expect(fetchSpy).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining("/v1/admin/production/production-1/start"),
      expect.objectContaining({ body: JSON.stringify({ notes: "Start" }), method: "POST" }),
    );
    expect(fetchSpy).toHaveBeenNthCalledWith(
      3,
      expect.stringContaining("/v1/admin/production/production-1/complete"),
      expect.objectContaining({
        body: JSON.stringify({
          actual_output_qty: "18.000",
          notes: "Completed",
          variance_reason: "Shrinkage",
        }),
        method: "POST",
      }),
    );
    expect(fetchSpy).toHaveBeenNthCalledWith(
      4,
      expect.stringContaining("/v1/admin/production/production-1/cancel"),
      expect.objectContaining({ body: JSON.stringify({ reason: "Not needed" }), method: "POST" }),
    );
  });
});
