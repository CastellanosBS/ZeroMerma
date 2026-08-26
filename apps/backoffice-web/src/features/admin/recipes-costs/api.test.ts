import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildAdminRecipeCostsListPath,
  createAdminRecipe,
  fetchAdminRecipeCostDetail,
  fetchAdminRecipeCosts,
} from "./api";
import type { AdminRecipeCostListFilters } from "./types";

const filters: AdminRecipeCostListFilters = {
  page: 1,
  pageSize: 25,
  recipeState: "all",
  search: "",
};

const apiProduct = {
  active_recipe_id: "recipe-1",
  active_recipe_updated_at: "2026-05-20T10:00:00Z",
  active_recipe_version_name: "Base",
  brand_id: "brand-1",
  brand_name: "El Mejor Pan",
  calculated_unit_cost: "4.00",
  class_id: "class-1",
  class_name: "Pan dulce",
  cost_variance: "1.00",
  cost_variance_percent: "25.00",
  currency_code: "MXN",
  health_status: "warning",
  product_code: "CONCHA-VAN",
  product_id: "product-1",
  product_name: "Vanilla Concha",
  product_standard_cost: "3.00",
  product_status: "active",
  product_unit_price: "12.00",
  recipe_input_count: 1,
  total_batch_cost: "40.00",
  unit_of_measure: "piece",
  updated_at: "2026-05-20T10:00:00Z",
  warnings: {
    codes: ["high_cost_variance"],
    messages: ["El costo calculado difiere del costo estandar."],
  },
  yield_qty: "10.000",
  yield_uom: "piece",
};

const apiRecipe = {
  calculated_unit_cost: "4.00",
  created_at: "2026-05-20T10:00:00Z",
  id: "recipe-1",
  input_count: 1,
  inputs: [
    {
      extended_cost: "40.00",
      id: "input-1",
      input_product_code: "RAW-FLOUR",
      input_product_id: "raw-1",
      input_product_name: "Raw Flour",
      quantity: "2.000",
      standard_cost: "20.00",
      status: "active",
      unit_of_measure: "kg",
    },
  ],
  is_active: true,
  product_id: "product-1",
  total_batch_cost: "40.00",
  updated_at: "2026-05-20T10:00:00Z",
  version_name: "Base",
  yield_qty: "10.000",
  yield_uom: "piece",
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

describe("admin recipe costs API boundary", () => {
  it("builds recipe cost list query parameters", () => {
    const path = buildAdminRecipeCostsListPath({
      ...filters,
      brandId: "brand-1",
      classId: "class-1",
      recipeState: "warning",
      search: "concha",
    });

    expect(path).toContain("/v1/admin/recipes-costs/products?");
    expect(path).toContain("brand_id=brand-1");
    expect(path).toContain("class_id=class-1");
    expect(path).toContain("recipe_state=warning");
    expect(path).toContain("search=concha");
  });

  it("fetches and maps product-centered recipe rows", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        filter_options: {
          brands: [{ id: "brand-1", label: "El Mejor Pan" }],
          classes: [{ id: "class-1", label: "Pan dulce" }],
          raw_materials: [{ id: "raw-1", label: "Raw Flour" }],
        },
        is_backend_connected: true,
        items: [apiProduct],
        metrics: {
          high_variance: 1,
          recently_updated: 1,
          with_active_recipe: 1,
          without_recipe: 0,
          with_warnings: 1,
        },
        page: 1,
        page_size: 25,
        total: 1,
      }),
    );

    const response = await fetchAdminRecipeCosts("token-1", filters);

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/recipes-costs/products?page=1&page_size=25"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(response.items[0]?.productName).toBe("Vanilla Concha");
    expect(response.items[0]?.calculatedUnitCost).toBe("4.00");
    expect(response.filterOptions.rawMaterials[0]?.label).toBe("Raw Flour");
  });

  it("loads recipe detail by product id", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        active_recipe: apiRecipe,
        product: apiProduct,
        recipe_versions: [apiRecipe],
      }),
    );

    const detail = await fetchAdminRecipeCostDetail("token-1", "product-1");

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/recipes-costs/products/product-1"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(detail.activeRecipe?.inputs[0]?.inputProductName).toBe("Raw Flour");
  });

  it("submits new recipes through the backend contract", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        active_recipe: apiRecipe,
        product: apiProduct,
        recipe_versions: [apiRecipe],
      }, 201),
    );

    const detail = await createAdminRecipe("token-1", {
      activate: true,
      inputs: [{ inputProductId: "raw-1", quantity: "2.000" }],
      productId: "product-1",
      versionName: "Base",
      yieldQty: "10.000",
      yieldUom: "piece",
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/recipes-costs/recipes"),
      expect.objectContaining({
        body: JSON.stringify({
          activate: true,
          inputs: [{ input_product_id: "raw-1", quantity: "2.000" }],
          product_id: "product-1",
          version_name: "Base",
          yield_qty: "10.000",
          yield_uom: "piece",
        }),
        method: "POST",
      }),
    );
    expect(detail.product.productId).toBe("product-1");
  });
});
