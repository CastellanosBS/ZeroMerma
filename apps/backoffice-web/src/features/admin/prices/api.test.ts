import { describe, expect, it, vi } from "vitest";

import { buildAdminPricesListPath, fetchAdminPrices, updateAdminPrice } from "./api";
import type { AdminPriceRow } from "./types";

const apiPriceRow = {
  brand_id: "brand-1",
  brand_name: "Brand",
  capture_mode: "PRODUCT_DIRECT",
  class_id: "class-1",
  class_name: "Bebidas",
  currency_code: "MXN",
  current_price: "18.00",
  entity_code: "COCA-355",
  entity_id: "product-1",
  entity_name: "Coca 355",
  entity_type: "product",
  health: "healthy",
  margin_percent: "44.44",
  price_cost_delta: "8.00",
  price_owner: "product_unit_price",
  related_class_id: "class-1",
  related_product_id: "product-1",
  standard_cost: "10.00",
  status: "active",
  updated_at: "2026-05-20T10:00:00Z",
  warnings: {
    codes: [],
    messages: [],
  },
} as const;

describe("admin prices api", () => {
  it("builds compact query params", () => {
    expect(
      buildAdminPricesListPath({
        brandId: "brand-1",
        captureMode: "PRODUCT_DIRECT",
        classId: "class-1",
        entityType: "product",
        page: 2,
        pageSize: 10,
        priceHealth: "healthy",
        search: " coca ",
        status: "active",
        updatedFrom: "2026-05-01",
        updatedTo: "2026-05-20",
      }),
    ).toBe(
      "/v1/admin/prices?page=2&page_size=10&brand_id=brand-1&capture_mode=PRODUCT_DIRECT&class_id=class-1&entity_type=product&price_health=healthy&search=coca&status=active&updated_from=2026-05-01&updated_to=2026-05-20",
    );
  });

  it("maps list responses from the backend contract", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          filter_options: {
            brands: [{ id: "brand-1", label: "Brand" }],
            classes: [{ id: "class-1", label: "Bebidas" }],
          },
          is_backend_connected: true,
          items: [apiPriceRow],
          metrics: {
            class_capture: 1,
            high_variance: 0,
            missing_or_invalid: 0,
            product_direct: 1,
            recently_changed: 1,
            total_entities: 2,
          },
          page: 1,
          page_size: 25,
          total: 1,
        }),
        { status: 200 },
      ),
    );

    const response = await fetchAdminPrices("token", {
      page: 1,
      pageSize: 25,
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/v1/admin/prices?page=1&page_size=25",
      expect.objectContaining({
        headers: expect.any(Headers),
        method: "GET",
      }),
    );
    expect(response.items[0]).toMatchObject({
      entityId: "product-1",
      currentPrice: "18.00",
      priceOwner: "product_unit_price",
    });
    expect(response.metrics.totalEntities).toBe("2");

    fetchMock.mockRestore();
  });

  it("updates the selected canonical owner endpoint", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          history_note: null,
          price: apiPriceRow,
        }),
        { status: 200 },
      ),
    );

    const row: AdminPriceRow = {
      brandId: "brand-1",
      brandName: "Brand",
      captureMode: "PRODUCT_DIRECT",
      classId: "class-1",
      className: "Bebidas",
      currencyCode: "MXN",
      currentPrice: "18.00",
      entityCode: "COCA-355",
      entityId: "product-1",
      entityName: "Coca 355",
      entityType: "product",
      health: "healthy",
      marginPercent: "44.44",
      priceCostDelta: "8.00",
      priceOwner: "product_unit_price",
      relatedClassId: "class-1",
      relatedProductId: "product-1",
      standardCost: "10.00",
      status: "active",
      updatedAt: "2026-05-20T10:00:00Z",
      warnings: { codes: [], messages: [] },
    };

    await updateAdminPrice("token", row, { price: "19.50" });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/v1/admin/prices/product/product-1",
      expect.objectContaining({
        body: JSON.stringify({ price: "19.50" }),
        method: "PATCH",
      }),
    );

    fetchMock.mockRestore();
  });
});
