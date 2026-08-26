import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildAdminInventoryListPath,
  createAdminInventoryAdjustment,
  fetchAdminInventory,
  fetchAdminInventoryDetail,
  fetchAdminInventoryMovements,
} from "./api";
import type { AdminInventoryListFilters } from "./types";

const filters: AdminInventoryListFilters = {
  locationCode: "all",
  page: 1,
  pageSize: 25,
  productKind: "all",
  productStatus: "all",
  search: "",
  stockState: "all",
};

const apiInventoryItem = {
  available_quantity: "12.000",
  balance_id: "balance-1",
  branch_id: "branch-1",
  branch_is_active: true,
  branch_name: "Main Branch",
  class_id: "class-1",
  class_name: "Pan dulce",
  in_transit_quantity: null,
  last_movement_at: "2026-05-20T10:00:00Z",
  location_code: "BACKROOM",
  location_name: "Fondo",
  product_code: "CONCHA-VAN",
  product_id: "product-1",
  product_is_active: true,
  product_kind: "FINISHED_GOOD",
  product_name: "Vanilla Concha",
  quantity_on_hand: "12.000",
  reserved_quantity: null,
  stock_state: "in_stock",
  unit_of_measure: "piece",
  warning_state: null,
  warnings: [],
} as const;

const apiMovement = {
  balance_after: "12.000",
  branch_id: "branch-1",
  branch_name: "Main Branch",
  direction: "IN",
  id: "movement-1",
  location_code: "BACKROOM",
  movement_type: "MANUAL_ADJUSTMENT",
  notes: null,
  occurred_at: "2026-05-20T10:00:00Z",
  operator_name: "Admin",
  product_id: "product-1",
  quantity: "12.000",
  reason: "Initial count",
  source_document_id: "adjustment-1",
  source_document_type: "INVENTORY_ADJUSTMENT",
  unit_of_measure: "piece",
} as const;

const apiDetail = {
  balance_id: "balance-1",
  branch_location: {
    branch_id: "branch-1",
    branch_is_active: true,
    branch_name: "Main Branch",
    location_code: "BACKROOM",
    location_model_supported: true,
    location_name: "Fondo",
  },
  movement_summary: {
    last_adjustment_at: "2026-05-20T10:00:00Z",
    last_inbound_at: "2026-05-20T10:00:00Z",
    last_movement_at: "2026-05-20T10:00:00Z",
    last_outbound_at: null,
  },
  movements: [apiMovement],
  product: {
    class_id: "class-1",
    class_name: "Pan dulce",
    code: "CONCHA-VAN",
    id: "product-1",
    is_active: true,
    is_sellable: true,
    name: "Vanilla Concha",
    product_kind: "FINISHED_GOOD",
    standard_cost: "5.0000",
    unit_of_measure: "piece",
  },
  related_actions: {
    can_create_adjustment: true,
    can_open_branch: true,
    can_open_product: true,
    can_start_count: false,
    count_endpoint_available: false,
  },
  stock_breakdown: {
    available_quantity: "12.000",
    estimated_value: "60.000",
    in_transit_quantity: null,
    quantity_on_hand: "12.000",
    reserved_quantity: null,
    unit_of_measure: "piece",
  },
  stock_state: "in_stock",
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

describe("admin inventory API boundary", () => {
  it("builds inventory list query parameters", () => {
    const path = buildAdminInventoryListPath({
      ...filters,
      branchId: "branch-1",
      classId: "class-1",
      locationCode: "BACKROOM",
      productKind: "FINISHED_GOOD",
      productStatus: "active",
      search: "concha",
      stockState: "in_stock",
    });

    expect(path).toContain("/v1/admin/inventory?");
    expect(path).toContain("branch_id=branch-1");
    expect(path).toContain("class_id=class-1");
    expect(path).toContain("location_code=BACKROOM");
    expect(path).toContain("product_kind=FINISHED_GOOD");
    expect(path).toContain("product_status=active");
    expect(path).toContain("search=concha");
    expect(path).toContain("stock_state=in_stock");
  });

  it("fetches and maps inventory list rows from the backend", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        filter_options: {
          branches: [{ id: "branch-1", label: "Main Branch - MAIN" }],
          classes: [{ id: "class-1", label: "Pan dulce" }],
          locations: [{ id: "BACKROOM", label: "Fondo" }],
          product_kinds: [{ id: "FINISHED_GOOD", label: "Producto terminado" }],
          products: [{ id: "product-1", label: "Vanilla Concha - CONCHA-VAN" }],
        },
        is_backend_connected: true,
        items: [apiInventoryItem],
        metrics: {
          estimated_value: "60.000",
          negative_stock: 0,
          products_with_stock: 1,
          stale_stock: 0,
          total_records: 1,
        },
        page: 1,
        page_size: 25,
        total: 1,
      }),
    );

    const response = await fetchAdminInventory("token-1", filters);

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/inventory?page=1&page_size=25"),
      expect.objectContaining({
        headers: expect.any(Headers),
        method: "GET",
      }),
    );
    expect(response.items).toHaveLength(1);
    expect(response.items[0]?.productCode).toBe("CONCHA-VAN");
    expect(response.metrics.productsWithStock).toBe("1");
    expect(response.filterOptions.products[0]?.label).toBe("Vanilla Concha - CONCHA-VAN");
  });

  it("loads inventory detail and movements", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementationOnce(() => mockJsonResponse(apiDetail))
      .mockImplementationOnce(() =>
        mockJsonResponse({
          items: [apiMovement],
          page: 1,
          page_size: 25,
          total: 1,
        }),
      );

    const detail = await fetchAdminInventoryDetail("token-1", "balance-1");
    const movements = await fetchAdminInventoryMovements("token-1", "balance-1");

    expect(fetchSpy).toHaveBeenNthCalledWith(
      1,
      expect.stringContaining("/v1/admin/inventory/balance-1"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(detail.product.code).toBe("CONCHA-VAN");
    expect(detail.movements[0]?.movementType).toBe("MANUAL_ADJUSTMENT");
    expect(movements.items[0]?.direction).toBe("IN");
  });

  it("submits audited inventory adjustments through the backend contract", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse(
        {
          adjustment_type: "INCREASE",
          balance_id: "balance-1",
          branch_id: "branch-1",
          created_at: "2026-05-20T10:00:00Z",
          created_by_user_id: "user-1",
          id: "adjustment-1",
          location_code: "BACKROOM",
          new_quantity: "12.000",
          notes: null,
          previous_quantity: "0.000",
          product_id: "product-1",
          quantity: "12.000",
          reason: "Initial count",
        },
        201,
      ),
    );

    const adjustment = await createAdminInventoryAdjustment("token-1", {
      adjustmentType: "INCREASE",
      branchId: "branch-1",
      locationCode: "BACKROOM",
      notes: null,
      productId: "product-1",
      quantity: "12.000",
      reason: "Initial count",
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/inventory/adjustments"),
      expect.objectContaining({
        body: JSON.stringify({
          adjustment_type: "INCREASE",
          branch_id: "branch-1",
          location_code: "BACKROOM",
          notes: null,
          product_id: "product-1",
          quantity: "12.000",
          reason: "Initial count",
        }),
        method: "POST",
      }),
    );
    expect(adjustment.balanceId).toBe("balance-1");
    expect(adjustment.newQuantity).toBe("12.000");
  });
});
