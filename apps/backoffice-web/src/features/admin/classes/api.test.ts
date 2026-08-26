import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildAdminProductClassesListPath,
  createAdminProductClass,
  fetchAdminProductClassDetail,
  fetchAdminProductClasses,
  updateAdminProductClass,
} from "./api";
import type { AdminProductClassListFilters } from "./types";

const filters: AdminProductClassListFilters = {
  page: 1,
  pageSize: 25,
  captureMode: "all",
  productPresence: "all",
  search: "",
  status: "all",
};

const apiProductClass = {
  active_product_count: 2,
  brand_id: "brand-1",
  brand_name: "El Mejor Pan",
  capture_mode_default: "CLASS_CAPTURE",
  class_capture_unit_price: "12.00",
  code: "PAN-DULCE",
  currency_code: "MXN",
  display_order: 10,
  id: "class-1",
  inactive_product_count: 0,
  is_sellable: true,
  linked_products: [
    {
      code: "CONCHA-VAN",
      id: "product-1",
      name: "Vanilla Concha",
      status: "active",
      unit_price: "12.00",
      updated_at: "2026-05-19T10:00:00Z",
    },
  ],
  name: "Pan dulce",
  product_count: 2,
  quick_name: "Dulce",
  readiness: "ready",
  search_aliases: "pan dulce",
  status: "active",
  updated_at: "2026-05-19T10:00:00Z",
  warnings: {
    codes: [],
    messages: [],
  },
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

describe("admin product classes API boundary", () => {
  it("builds real class list query parameters", () => {
    const path = buildAdminProductClassesListPath({
      ...filters,
      brandId: "brand-1",
      captureMode: "CLASS_CAPTURE",
      productPresence: "with_products",
      search: "pan",
      status: "active",
    });

    expect(path).toContain("/v1/admin/product-classes?");
    expect(path).toContain("brand_id=brand-1");
    expect(path).toContain("capture_mode=CLASS_CAPTURE");
    expect(path).toContain("product_presence=with_products");
    expect(path).toContain("search=pan");
    expect(path).toContain("status=active");
  });

  it("fetches and maps class list rows from the backend", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        filter_options: {
          brands: [{ id: "brand-1", label: "El Mejor Pan" }],
        },
        is_backend_connected: true,
        items: [apiProductClass],
        metrics: {
          active_classes: 1,
          class_capture: 1,
          product_direct: 0,
          total_classes: 1,
          with_warnings: 0,
          without_products: 0,
        },
        page: 1,
        page_size: 25,
        total: 1,
      }),
    );

    const response = await fetchAdminProductClasses("token-1", filters);

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/product-classes?page=1&page_size=25"),
      expect.objectContaining({
        headers: expect.any(Headers),
        method: "GET",
      }),
    );
    expect(response.isBackendConnected).toBe(true);
    expect(response.items[0]?.name).toBe("Pan dulce");
    expect(response.items[0]?.captureModeDefault).toBe("CLASS_CAPTURE");
    expect(response.items[0]?.linkedProducts[0]?.name).toBe("Vanilla Concha");
    expect(response.metrics.totalClasses).toBe("1");
    expect(response.filterOptions.brands[0]?.label).toBe("El Mejor Pan");
  });

  it("loads class detail by id", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse(apiProductClass),
    );

    const productClass = await fetchAdminProductClassDetail("token-1", "class-1");

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/product-classes/class-1"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(productClass.id).toBe("class-1");
    expect(productClass.classCaptureUnitPrice).toBe("12.00");
  });

  it("submits new classes through the backend contract", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse(apiProductClass, 201),
    );

    const productClass = await createAdminProductClass("token-1", {
      brandId: "brand-1",
      captureModeDefault: "CLASS_CAPTURE",
      classCaptureUnitPrice: "12.00",
      code: "PAN-DULCE",
      currencyCode: "MXN",
      displayOrder: 10,
      isSellable: true,
      name: "Pan dulce",
      quickName: "Dulce",
      searchAliases: "pan dulce",
      status: "active",
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/product-classes"),
      expect.objectContaining({
        body: JSON.stringify({
          brand_id: "brand-1",
          capture_mode_default: "CLASS_CAPTURE",
          class_capture_unit_price: "12.00",
          code: "PAN-DULCE",
          currency_code: "MXN",
          display_order: 10,
          is_sellable: true,
          name: "Pan dulce",
          quick_name: "Dulce",
          search_aliases: "pan dulce",
          status: "active",
        }),
        method: "POST",
      }),
    );
    expect(productClass.name).toBe("Pan dulce");
  });

  it("updates classes through the backend contract", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse(apiProductClass),
    );

    const productClass = await updateAdminProductClass("token-1", "class-1", {
      displayOrder: 20,
      status: "inactive",
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/product-classes/class-1"),
      expect.objectContaining({
        body: JSON.stringify({
          display_order: 20,
          status: "inactive",
        }),
        method: "PATCH",
      }),
    );
    expect(productClass.id).toBe("class-1");
  });
});
