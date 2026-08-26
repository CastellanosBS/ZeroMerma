import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { adminInputSupplyBackendContract } from "./api";
import { AdminInputSupplyDetailPanel } from "./components/AdminInputSupplyDetailPanel";
import { AdminInputSuppliesFilters } from "./components/AdminInputSuppliesFilters";
import { AdminInputSupplyFormPanel } from "./components/AdminInputSupplyFormPanel";
import { AdminInputSuppliesTable } from "./components/AdminInputSuppliesTable";
import { AdminInputsSuppliesPage } from "./pages/AdminInputsSuppliesPage";
import type {
  AdminInputSupplyDetail,
  AdminInputSupplyFilterOptions,
  AdminInputSupplyListFilters,
  AdminInputSupplyListItem,
} from "./types";

const filterOptions: AdminInputSupplyFilterOptions = {
  classes: [{ id: "class-1", label: "Harinas" }],
  costStates: [{ id: "missing_cost", label: "Sin costo" }],
  productKinds: [
    { id: "RAW_MATERIAL", label: "Materia prima" },
    { id: "CONSUMABLE", label: "Consumible" },
  ],
  recipeUsageStates: [{ id: "used", label: "Usado en recetas" }],
  statuses: [{ id: "active", label: "Activo" }],
  stockStates: [{ id: "low_stock", label: "Stock bajo" }],
  suppliers: [{ id: "supplier-1", label: "Harinas del Centro" }],
  usageTypes: [{ id: "RECIPE_INPUT", label: "Insumo de receta" }],
  warningStates: [{ id: "with_warnings", label: "Con advertencias" }],
};

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

const inputItem: AdminInputSupplyListItem = {
  baseUom: "KG",
  categoryId: "class-1",
  categoryName: "Harinas",
  code: "HARINA-1KG",
  id: "product-1",
  isActive: true,
  isInventoryTracked: true,
  isPurchasable: true,
  lastMovementAt: "2026-05-20T10:00:00Z",
  lastPurchaseCost: "18.50",
  name: "Harina panadera",
  primarySupplierName: "Harinas del Centro",
  productKind: "RAW_MATERIAL",
  purchaseUom: "KG",
  recipeUsageCount: 1,
  standardCost: "17.75",
  stockState: "low_stock",
  supplierCount: 1,
  updatedAt: "2026-05-20T11:00:00Z",
  warningState: "warning",
  warnings: [
    {
      code: "low_stock",
      message: "Existencia por debajo del punto de reorden.",
      severity: "warning",
    },
  ],
};

const inputDetail: AdminInputSupplyDetail = {
  availableActions: {
    canAddSupplier: true,
    canDeactivate: true,
    canEdit: true,
    canOpenInventory: true,
    canOpenProduct: true,
    canOpenRecipes: true,
  },
  classification: {
    kind: "RAW_MATERIAL",
    notes: "Insumo prioritario",
    status: "active",
    storageGroup: "Harinas",
    usageType: "RECIPE_INPUT",
  },
  cost: {
    costUpdatedAt: "2026-05-20T11:00:00Z",
    currency: "MXN",
    lastPurchaseCost: "18.50",
    standardCost: "17.75",
    supplierPriceMax: "18.50",
    supplierPriceMin: "18.50",
    warnings: [],
  },
  inventoryStatus: {
    integrationAvailable: true,
    lastMovementAt: "2026-05-20T10:00:00Z",
    minimumStock: "10.000",
    preferredOrderQuantity: "25.000",
    reorderPoint: "15.000",
    stockByBranch: [
      {
        branchId: "branch-1",
        branchName: "Centro",
        lastMovementAt: "2026-05-20T10:00:00Z",
        quantityOnHand: "12.000",
        stockState: "low_stock",
      },
    ],
    stockState: "low_stock",
    totalStock: "12.000",
    unitOfMeasure: "KG",
  },
  overview: {
    ...inputItem,
    createdAt: "2026-05-20T09:00:00Z",
    readinessState: "warning",
  },
  procurementWarnings: [
    {
      code: "low_stock",
      message: "Existencia por debajo del punto de reorden.",
      severity: "warning",
    },
  ],
  recipeUsage: [
    {
      finishedProductCode: "CONCHA",
      finishedProductId: "finished-1",
      finishedProductName: "Concha",
      quantity: "0.200",
      recipeId: "recipe-1",
      recipeVersionName: "Base",
      unitOfMeasure: "KG",
    },
  ],
  relatedDocuments: [],
  suppliers: [
    {
      conversionFactor: "1.000",
      currency: "MXN",
      id: "supplier-product-1",
      isActive: true,
      lastKnownPrice: "18.50",
      leadTimeDays: 2,
      minimumOrderQty: "25.000",
      notes: null,
      purchaseUom: "KG",
      supplierId: "supplier-1",
      supplierName: "Harinas del Centro",
      supplierSku: "H-1KG",
    },
  ],
  unitsConversion: {
    baseUom: "KG",
    consumptionUom: "KG",
    conversionFactor: "1.000",
    minimumPurchaseQuantity: "25.000",
    purchaseUom: "KG",
    unitConversionSupported: true,
  },
};

function render(element: ReactElement) {
  return renderToString(element);
}

describe("admin inputs and supplies UI components", () => {
  it("renders the module page shell", () => {
    const queryClient = new QueryClient();

    const html = render(
      <QueryClientProvider client={queryClient}>
        <AdminInputsSuppliesPage />
      </QueryClientProvider>,
    );

    expect(html).toContain("Insumos y consumibles");
    expect(html).toContain("Nuevo insumo");
    expect(html).toContain(
      "Selecciona un insumo para revisar proveedores, costos, inventario y uso operativo.",
    );
  });

  it("renders filters, summary-ready controls and quick filters", () => {
    const html = render(
      <AdminInputSuppliesFilters
        filters={filters}
        isBackendConnected={true}
        options={filterOptions}
        onChange={() => undefined}
      />,
    );

    expect(html).toContain("Busqueda");
    expect(html).toContain("Tipo");
    expect(html).toContain("Materia prima");
    expect(html).toContain("Sin proveedor");
    expect(html).toContain("Datos conectados");
  });

  it("renders empty and populated table states with safe actions", () => {
    const emptyHtml = render(
      <AdminInputSuppliesTable
        backendContract={adminInputSupplyBackendContract}
        inputs={[]}
        isLoading={false}
        page={1}
        pageSize={25}
        total={0}
        onChangeStatus={() => undefined}
        onOpenInventory={() => undefined}
        onOpenProduct={() => undefined}
        onOpenSuppliers={() => undefined}
        onPageChange={() => undefined}
        onSelectInput={() => undefined}
      />,
    );
    expect(emptyHtml).toContain(
      "No hay insumos o consumibles registrados para los filtros seleccionados.",
    );

    const tableHtml = render(
      <AdminInputSuppliesTable
        backendContract={adminInputSupplyBackendContract}
        inputs={[inputItem]}
        isLoading={false}
        page={1}
        pageSize={25}
        total={1}
        onChangeStatus={() => undefined}
        onOpenInventory={() => undefined}
        onOpenProduct={() => undefined}
        onOpenSuppliers={() => undefined}
        onPageChange={() => undefined}
        onSelectInput={() => undefined}
      />,
    );

    expect(tableHtml).toContain("Codigo / tipo");
    expect(tableHtml).toContain("Harina panadera");
    expect(tableHtml).toContain("Copiar codigo");
    expect(tableHtml).toContain("Desactivar");
    expect(tableHtml).not.toContain("Editar existencia");
  });

  it("renders detail sections, supplier context, inventory, recipe usage and warning state", () => {
    const detailHtml = render(
      <AdminInputSupplyDetailPanel
        inputDetail={inputDetail}
        inputPreview={inputItem}
        isLoading={false}
        onOpenInventory={() => undefined}
        onOpenProduct={() => undefined}
        onOpenRecipes={() => undefined}
        onOpenSupplier={() => undefined}
      />,
    );

    expect(detailHtml).toContain("Clasificacion");
    expect(detailHtml).toContain("Unidades y conversion");
    expect(detailHtml).toContain("Proveedores");
    expect(detailHtml).toContain("Costos");
    expect(detailHtml).toContain("Inventario");
    expect(detailHtml).toContain("Uso en recetas");
    expect(detailHtml).toContain("Preparacion y advertencias");
    expect(detailHtml).toContain("Este insumo no tiene documentos relacionados.");
  });

  it("renders create and edit form sections with validation surface and supplier relations", () => {
    const createHtml = render(
      <AdminInputSupplyFormPanel
        classOptions={filterOptions.classes}
        errorMessage="El nombre del insumo es requerido."
        isSubmitting={false}
        supplierOptions={filterOptions.suppliers}
        usageTypeOptions={filterOptions.usageTypes}
        onClose={() => undefined}
        onSubmit={() => undefined}
      />,
    );

    expect(createHtml).toContain("Nuevo insumo");
    expect(createHtml).toContain("Catalogo comprable e inventariable");
    expect(createHtml).toContain("Proveedores asociados");
    expect(createHtml).toContain("El nombre del insumo es requerido.");
    expect(createHtml).not.toContain("Cantidad en stock");

    const editHtml = render(
      <AdminInputSupplyFormPanel
        classOptions={filterOptions.classes}
        initialInput={inputDetail}
        isSubmitting={false}
        supplierOptions={filterOptions.suppliers}
        usageTypeOptions={filterOptions.usageTypes}
        onClose={() => undefined}
        onSubmit={() => undefined}
      />,
    );

    expect(editHtml).toContain("Editar insumo");
    expect(editHtml).toContain("Harina panadera");
    expect(editHtml).toContain("Harinas del Centro");
    expect(editHtml).toContain("Precio proveedor");
  });
});
