import { afterEach, describe, expect, it, vi } from "vitest";

import {
  addAdminInputSupplySupplierRelation,
  buildAdminInputSuppliesListPath,
  changeAdminInputSupplyStatus,
  createAdminInputSupply,
  fetchAdminInputSupplies,
  fetchAdminInputSupplyDetail,
} from "./api";
import type { AdminInputSupplyListFilters } from "./types";

const filters: AdminInputSupplyListFilters = {
  classId: null,
  costState: "all",
  inventoryTracked: "all",
  page: 1,
  pageSize: 25,
  productKind: "all",
  purchasable: "all",
  recipeUsage: "all",
  search: "",
  status: "all",
  stockState: "all",
  supplierId: null,
  usageType: null,
  warningState: "all",
  withoutSupplier: "all",
};

const apiInputItem = {
  base_uom: "KG",
  category_id: "class-1",
  category_name: "Harinas",
  code: "HARINA-1KG",
  id: "product-1",
  is_active: true,
  is_inventory_tracked: true,
  is_purchasable: true,
  last_movement_at: "2026-05-20T10:00:00Z",
  last_purchase_cost: "18.50",
  name: "Harina panadera",
  primary_supplier_name: "Harinas del Centro",
  product_kind: "RAW_MATERIAL",
  purchase_uom: "KG",
  recipe_usage_count: 1,
  standard_cost: "17.75",
  stock_state: "low_stock",
  supplier_count: 1,
  updated_at: "2026-05-20T11:00:00Z",
  warning_state: "warning",
  warnings: [
    {
      code: "low_stock",
      message: "Existencia por debajo del punto de reorden.",
      severity: "warning",
    },
  ],
} as const;

const apiInputDetail = {
  available_actions: {
    can_add_supplier: true,
    can_deactivate: true,
    can_edit: true,
    can_open_inventory: true,
    can_open_product: true,
    can_open_recipes: true,
  },
  classification: {
    kind: "RAW_MATERIAL",
    notes: "Insumo prioritario",
    status: "active",
    storage_group: "Harinas",
    usage_type: "RECIPE_INPUT",
  },
  cost: {
    cost_updated_at: "2026-05-20T11:00:00Z",
    currency: "MXN",
    last_purchase_cost: "18.50",
    standard_cost: "17.75",
    supplier_price_max: "18.50",
    supplier_price_min: "18.50",
    warnings: [],
  },
  inventory_status: {
    integration_available: true,
    last_movement_at: "2026-05-20T10:00:00Z",
    minimum_stock: "10.000",
    preferred_order_quantity: "25.000",
    reorder_point: "15.000",
    stock_by_branch: [
      {
        branch_id: "branch-1",
        branch_name: "Centro",
        last_movement_at: "2026-05-20T10:00:00Z",
        quantity_on_hand: "12.000",
        stock_state: "low_stock",
      },
    ],
    stock_state: "low_stock",
    total_stock: "12.000",
    unit_of_measure: "KG",
  },
  overview: {
    base_uom: "KG",
    category_id: "class-1",
    category_name: "Harinas",
    code: "HARINA-1KG",
    created_at: "2026-05-20T09:00:00Z",
    id: "product-1",
    is_active: true,
    is_inventory_tracked: true,
    is_purchasable: true,
    last_purchase_cost: "18.50",
    name: "Harina panadera",
    product_kind: "RAW_MATERIAL",
    purchase_uom: "KG",
    readiness_state: "warning",
    standard_cost: "17.75",
    updated_at: "2026-05-20T11:00:00Z",
    warning_state: "warning",
  },
  procurement_warnings: [
    {
      code: "low_stock",
      message: "Existencia por debajo del punto de reorden.",
      severity: "warning",
    },
  ],
  recipe_usage: [
    {
      finished_product_code: "CONCHA",
      finished_product_id: "finished-1",
      finished_product_name: "Concha",
      quantity: "0.200",
      recipe_id: "recipe-1",
      recipe_version_name: "Base",
      unit_of_measure: "KG",
    },
  ],
  related_documents: [
    {
      document_id: "supplier-product-1",
      document_type: "SUPPLIER_PRODUCT",
      folio: "SUP-1",
      status: "active",
    },
  ],
  suppliers: [
    {
      conversion_factor: "1.000",
      currency: "MXN",
      id: "supplier-product-1",
      is_active: true,
      last_known_price: "18.50",
      lead_time_days: 2,
      minimum_order_qty: "25.000",
      notes: null,
      purchase_uom: "KG",
      supplier_id: "supplier-1",
      supplier_name: "Harinas del Centro",
      supplier_sku: "H-1KG",
    },
  ],
  units_conversion: {
    base_uom: "KG",
    consumption_uom: "KG",
    conversion_factor: "1.000",
    minimum_purchase_quantity: "25.000",
    purchase_uom: "KG",
    unit_conversion_supported: true,
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

describe("admin inputs and supplies API boundary", () => {
  it("builds input list query parameters", () => {
    const path = buildAdminInputSuppliesListPath({
      ...filters,
      classId: "class-1",
      costState: "missing_cost",
      inventoryTracked: "true",
      productKind: "RAW_MATERIAL",
      recipeUsage: "used",
      search: "harina",
      status: "active",
      stockState: "low_stock",
      supplierId: "supplier-1",
      usageType: "RECIPE_INPUT",
      warningState: "with_warnings",
      withoutSupplier: "true",
    });

    expect(path).toContain("/v1/admin/inputs-supplies?");
    expect(path).toContain("class_id=class-1");
    expect(path).toContain("cost_state=missing_cost");
    expect(path).toContain("inventory_tracked=true");
    expect(path).toContain("product_kind=RAW_MATERIAL");
    expect(path).toContain("recipe_usage=used");
    expect(path).toContain("search=harina");
    expect(path).toContain("status=active");
    expect(path).toContain("stock_state=low_stock");
    expect(path).toContain("supplier_id=supplier-1");
    expect(path).toContain("usage_type=RECIPE_INPUT");
    expect(path).toContain("warning_state=with_warnings");
    expect(path).toContain("without_supplier=true");
  });

  it("fetches and maps input list data from backend", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        backend_contract: undefined,
        filter_options: {
          classes: [{ id: "class-1", label: "Harinas" }],
          cost_states: [{ id: "missing_cost", label: "Sin costo" }],
          product_kinds: [{ id: "RAW_MATERIAL", label: "Materia prima" }],
          recipe_usage_states: [{ id: "used", label: "Usado en recetas" }],
          statuses: [{ id: "active", label: "Activo" }],
          stock_states: [{ id: "low_stock", label: "Stock bajo" }],
          suppliers: [{ id: "supplier-1", label: "Harinas del Centro" }],
          usage_types: [{ id: "RECIPE_INPUT", label: "Insumo de receta" }],
          warning_states: [{ id: "with_warnings", label: "Con advertencias" }],
        },
        is_backend_connected: true,
        items: [apiInputItem],
        metrics: {
          active_consumables: 0,
          active_disposables: 0,
          active_raw_materials: 1,
          low_stock: 1,
          missing_cost: 0,
          used_in_recipes: 1,
          without_supplier: 0,
        },
        page: 1,
        page_size: 25,
        total: 1,
      }),
    );

    const response = await fetchAdminInputSupplies("token-1", filters);

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/inputs-supplies?page=1&page_size=25"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(response.items[0]?.name).toBe("Harina panadera");
    expect(response.items[0]?.stockState).toBe("low_stock");
    expect(response.filterOptions.usageTypes[0]?.id).toBe("RECIPE_INPUT");
    expect(response.metrics.activeRawMaterials).toBe("1");
  });

  it("loads input detail with supplier, inventory and recipe context", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() => mockJsonResponse(apiInputDetail));

    const detail = await fetchAdminInputSupplyDetail("token-1", "product-1");

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/inputs-supplies/product-1"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(detail.overview.code).toBe("HARINA-1KG");
    expect(detail.suppliers[0]?.supplierName).toBe("Harinas del Centro");
    expect(detail.inventoryStatus.stockByBranch[0]?.branchName).toBe("Centro");
    expect(detail.recipeUsage[0]?.finishedProductName).toBe("Concha");
  });

  it("creates input, adds supplier relation and changes status through backend endpoints", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() => mockJsonResponse(apiInputDetail, 201));

    await createAdminInputSupply("token-1", {
      code: "HARINA-1KG",
      isActive: true,
      isInventoryTracked: true,
      isPurchasable: true,
      name: "Harina panadera",
      productClassId: "class-1",
      productKind: "RAW_MATERIAL",
      purchaseConversionFactor: "1.000",
      purchaseUom: "KG",
      standardCost: "17.75",
      supplierRelations: [{ supplierId: "supplier-1", purchaseUom: "KG" }],
      unitOfMeasure: "KG",
      usageType: "RECIPE_INPUT",
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/inputs-supplies"),
      expect.objectContaining({
        body: expect.stringContaining('"product_kind":"RAW_MATERIAL"'),
        method: "POST",
      }),
    );

    await addAdminInputSupplySupplierRelation("token-1", "product-1", {
      conversionFactor: "1.000",
      purchaseUom: "KG",
      supplierId: "supplier-1",
    });
    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining("/v1/admin/inputs-supplies/product-1/suppliers"),
      expect.objectContaining({ method: "POST" }),
    );

    await changeAdminInputSupplyStatus("token-1", "product-1", {
      isActive: false,
      notes: "Fuera de compra.",
    });
    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining("/v1/admin/inputs-supplies/product-1/status"),
      expect.objectContaining({
        body: JSON.stringify({ is_active: false, notes: "Fuera de compra." }),
        method: "POST",
      }),
    );
  });
});
