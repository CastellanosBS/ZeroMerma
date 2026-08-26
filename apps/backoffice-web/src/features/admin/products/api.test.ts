import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildAdminProductsListPath,
  createAdminProduct,
  fetchAdminProductDetail,
  fetchAdminProducts,
} from "./api";
import type { AdminProductListFilters } from "./types";

const filters: AdminProductListFilters = {
  page: 1,
  pageSize: 25,
  captureMode: "all",
  readiness: "all",
  search: "",
  status: "all",
};

const apiProduct = {
  availability: {
    configured_branches_count: null,
    state: "unknown",
    total_branches_count: null,
  },
  branch_availability: [],
  brand_id: null,
  brand_name: null,
  capture_mode: "PRODUCT_DIRECT",
  class_id: "class-1",
  class_name: "Pan dulce",
  code: "CONCHA-VAN",
  currency_code: "MXN",
  description: null,
  id: "product-1",
  name: "Concha vainilla",
  readiness: {
    missing_requirements: ["Disponibilidad por sucursal pendiente de integración."],
    related: {
      audit_trail: "ready",
      branch_availability: "pending_integration",
      inventory: "pending_integration",
      pos_visibility: "ready",
      price: "ready",
      recipe: "pending_integration",
    },
    status: "requires_attention",
  },
  sku: "CONCHA-VAN",
  status: "active",
  unit_of_measure: "piece",
  unit_price: "12.00",
  updated_at: "2026-05-19T10:00:00Z",
  visible_in_pos: true,
};

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

describe("admin products API boundary", () => {
  it("builds real product list query parameters", () => {
    const path = buildAdminProductsListPath({
      ...filters,
      branchId: "branch-1",
      captureMode: "PRODUCT_DIRECT",
      classId: "class-1",
      readiness: "requires_attention",
      search: "concha",
      status: "active",
    });

    expect(path).toContain("/v1/admin/products?");
    expect(path).toContain("branch_id=branch-1");
    expect(path).toContain("class_id=class-1");
    expect(path).toContain("capture_mode=PRODUCT_DIRECT");
    expect(path).toContain("readiness=requires_attention");
    expect(path).toContain("search=concha");
    expect(path).toContain("status=active");
  });

  it("fetches and maps product list rows from the backend", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        filter_options: {
          branches: [{ id: "branch-1", label: "Sucursal larga" }],
          brands: [],
          classes: [{ id: "class-1", label: "Pan dulce" }],
        },
        is_backend_connected: true,
        items: [apiProduct],
        metrics: {
          active_products: 1,
          class_capture: 0,
          product_direct: 1,
          require_attention: 1,
          without_branch_availability: null,
        },
        page: 1,
        page_size: 25,
        total: 1,
      }),
    );

    const response = await fetchAdminProducts("token-1", filters);

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/products?page=1&page_size=25"),
      expect.objectContaining({
        headers: expect.any(Headers),
        method: "GET",
      }),
    );
    expect(response.isBackendConnected).toBe(true);
    expect(response.items).toHaveLength(1);
    expect(response.items[0]?.name).toBe("Concha vainilla");
    expect(response.items[0]?.captureMode).toBe("PRODUCT_DIRECT");
    expect(response.metrics.activeProducts).toBe("1");
    expect(response.filterOptions.classes[0]?.label).toBe("Pan dulce");
  });

  it("loads product detail by id", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse(apiProduct));

    const product = await fetchAdminProductDetail("token-1", "product-1");

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/products/product-1"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(product.id).toBe("product-1");
    expect(product.readiness.related.branchAvailability).toBe("pending_integration");
  });

  it("submits new products through the backend contract", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse(apiProduct, 201));

    const product = await createAdminProduct("token-1", {
      code: "CONCHA-VAN",
      name: "Concha vainilla",
      productClassId: "class-1",
      quickName: "Concha",
      searchAliases: null,
      status: "active",
      unitPrice: "12.00",
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/products"),
      expect.objectContaining({
        body: JSON.stringify({
          code: "CONCHA-VAN",
          name: "Concha vainilla",
          product_class_id: "class-1",
          quick_name: "Concha",
          search_aliases: null,
          status: "active",
          unit_price: "12.00",
        }),
        method: "POST",
      }),
    );
    expect(product.name).toBe("Concha vainilla");
  });
});
