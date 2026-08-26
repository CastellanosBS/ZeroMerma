import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminInputSupplyBackendContract,
  AdminInputSupplyDetail,
  AdminInputSupplyFilterOption,
  AdminInputSupplyListFilters,
  AdminInputSupplyListItem,
  AdminInputSupplyListResponse,
  AdminInputSupplyPayload,
  AdminInputSupplyStatusPayload,
  AdminInputSupplySupplierRelationPayload,
  AdminInputSupplyWarning,
} from "./types";

export const adminInputSupplyBackendContract: AdminInputSupplyBackendContract = {
  addSupplierRelationEndpoint: "POST /v1/admin/inputs-supplies/{product_id}/suppliers",
  createEndpoint: "POST /v1/admin/inputs-supplies",
  detailEndpoint: "GET /v1/admin/inputs-supplies/{product_id}",
  listEndpoint: "GET /v1/admin/inputs-supplies",
  statusEndpoint: "POST /v1/admin/inputs-supplies/{product_id}/status",
  updateEndpoint: "PATCH /v1/admin/inputs-supplies/{product_id}",
  updateSupplierRelationEndpoint:
    "PATCH /v1/admin/inputs-supplies/{product_id}/suppliers/{relation_id}",
};

type ApiBackendContract = components["schemas"]["AdminInputSupplyBackendContractView"];
type ApiDetail = components["schemas"]["AdminInputSupplyDetailView"];
type ApiFilterOption = components["schemas"]["AdminInputSupplyFilterOptionView"];
type ApiListItem = components["schemas"]["AdminInputSupplyListItemView"];
type ApiListResponse = components["schemas"]["AdminInputSupplyListResponse"];
type ApiPayload = components["schemas"]["AdminInputSupplyCreateRequest"];
type ApiStatusPayload = components["schemas"]["AdminInputSupplyStatusRequest"];
type ApiSupplierRelationPayload = components["schemas"]["AdminInputSupplySupplierRelationRequest"];
type ApiWarning = components["schemas"]["AdminInputSupplyWarningView"];

function appendOptionalParam(
  params: URLSearchParams,
  key: string,
  value: string | null | undefined,
) {
  if (!value || value === "all") {
    return;
  }
  params.set(key, value);
}

function appendBooleanParam(
  params: URLSearchParams,
  key: string,
  value: "all" | "true" | "false" | undefined,
) {
  if (!value || value === "all") {
    return;
  }
  params.set(key, value);
}

function mapMetric(value: number | string | null | undefined): string {
  if (value === null || value === undefined) {
    return "No disponible";
  }
  return String(value);
}

function mapFilterOptions(options: ApiFilterOption[]): AdminInputSupplyFilterOption[] {
  return options.map((option) => ({ id: String(option.id), label: option.label }));
}

function mapWarning(warning: ApiWarning): AdminInputSupplyWarning {
  return {
    code: warning.code,
    message: warning.message,
    severity: warning.severity,
  };
}

function mapBackendContract(contract?: ApiBackendContract): AdminInputSupplyBackendContract {
  if (!contract) {
    return adminInputSupplyBackendContract;
  }
  return {
    addSupplierRelationEndpoint: contract.add_supplier_relation_endpoint,
    createEndpoint: contract.create_endpoint,
    detailEndpoint: contract.detail_endpoint,
    listEndpoint: contract.list_endpoint,
    statusEndpoint: contract.status_endpoint,
    updateEndpoint: contract.update_endpoint,
    updateSupplierRelationEndpoint: contract.update_supplier_relation_endpoint,
  };
}

export function mapAdminInputSupplyListItemFromApi(item: ApiListItem): AdminInputSupplyListItem {
  return {
    baseUom: item.base_uom,
    categoryId: item.category_id,
    categoryName: item.category_name,
    code: item.code,
    id: item.id,
    isActive: item.is_active,
    isInventoryTracked: item.is_inventory_tracked,
    isPurchasable: item.is_purchasable,
    lastMovementAt: item.last_movement_at ?? null,
    lastPurchaseCost: item.last_purchase_cost == null ? null : String(item.last_purchase_cost),
    name: item.name,
    primarySupplierName: item.primary_supplier_name ?? null,
    productKind: item.product_kind,
    purchaseUom: item.purchase_uom ?? null,
    recipeUsageCount: item.recipe_usage_count,
    standardCost: item.standard_cost == null ? null : String(item.standard_cost),
    stockState: item.stock_state,
    supplierCount: item.supplier_count,
    updatedAt: item.updated_at,
    warningState: item.warning_state,
    warnings: item.warnings.map(mapWarning),
  };
}

export function mapAdminInputSupplyDetailFromApi(item: ApiDetail): AdminInputSupplyDetail {
  const overview = item.overview;
  return {
    availableActions: {
      canAddSupplier: item.available_actions?.can_add_supplier ?? true,
      canDeactivate: item.available_actions?.can_deactivate ?? true,
      canEdit: item.available_actions?.can_edit ?? true,
      canOpenInventory: item.available_actions?.can_open_inventory ?? true,
      canOpenProduct: item.available_actions?.can_open_product ?? true,
      canOpenRecipes: item.available_actions?.can_open_recipes ?? true,
    },
    classification: {
      kind: item.classification.kind,
      notes: item.classification.notes ?? null,
      status: item.classification.status,
      storageGroup: item.classification.storage_group ?? null,
      usageType: item.classification.usage_type ?? null,
    },
    cost: {
      costUpdatedAt: item.cost.cost_updated_at ?? null,
      currency: item.cost.currency,
      lastPurchaseCost:
        item.cost.last_purchase_cost == null ? null : String(item.cost.last_purchase_cost),
      standardCost: item.cost.standard_cost == null ? null : String(item.cost.standard_cost),
      supplierPriceMax:
        item.cost.supplier_price_max == null ? null : String(item.cost.supplier_price_max),
      supplierPriceMin:
        item.cost.supplier_price_min == null ? null : String(item.cost.supplier_price_min),
      warnings: item.cost.warnings.map(mapWarning),
    },
    inventoryStatus: {
      integrationAvailable: item.inventory_status.integration_available,
      lastMovementAt: item.inventory_status.last_movement_at ?? null,
      minimumStock:
        item.inventory_status.minimum_stock == null
          ? null
          : String(item.inventory_status.minimum_stock),
      preferredOrderQuantity:
        item.inventory_status.preferred_order_quantity == null
          ? null
          : String(item.inventory_status.preferred_order_quantity),
      reorderPoint:
        item.inventory_status.reorder_point == null
          ? null
          : String(item.inventory_status.reorder_point),
      stockByBranch: item.inventory_status.stock_by_branch.map((branch) => ({
        branchId: branch.branch_id,
        branchName: branch.branch_name,
        lastMovementAt: branch.last_movement_at ?? null,
        quantityOnHand: String(branch.quantity_on_hand),
        stockState: branch.stock_state,
      })),
      stockState: item.inventory_status.stock_state,
      totalStock:
        item.inventory_status.total_stock == null
          ? null
          : String(item.inventory_status.total_stock),
      unitOfMeasure: item.inventory_status.unit_of_measure,
    },
    overview: {
      baseUom: overview.base_uom,
      categoryId: overview.category_id,
      categoryName: overview.category_name,
      code: overview.code,
      createdAt: overview.created_at,
      id: overview.id,
      isActive: overview.is_active,
      isInventoryTracked: overview.is_inventory_tracked,
      isPurchasable: overview.is_purchasable,
      lastMovementAt: null,
      lastPurchaseCost:
        overview.last_purchase_cost == null ? null : String(overview.last_purchase_cost),
      name: overview.name,
      primarySupplierName: null,
      productKind: overview.product_kind,
      purchaseUom: overview.purchase_uom ?? null,
      readinessState: overview.readiness_state,
      recipeUsageCount: item.recipe_usage.length,
      standardCost: overview.standard_cost == null ? null : String(overview.standard_cost),
      stockState: item.inventory_status.stock_state,
      supplierCount: item.suppliers.filter((relation) => relation.is_active).length,
      updatedAt: overview.updated_at,
      warningState: overview.warning_state,
      warnings: item.procurement_warnings.map(mapWarning),
    },
    procurementWarnings: item.procurement_warnings.map(mapWarning),
    recipeUsage: item.recipe_usage.map((usage) => ({
      finishedProductCode: usage.finished_product_code,
      finishedProductId: usage.finished_product_id,
      finishedProductName: usage.finished_product_name,
      quantity: String(usage.quantity),
      recipeId: usage.recipe_id,
      recipeVersionName: usage.recipe_version_name ?? null,
      unitOfMeasure: usage.unit_of_measure,
    })),
    relatedDocuments: item.related_documents.map((document) => ({
      documentId: String(document.document_id),
      documentType: document.document_type,
      folio: document.folio,
      status: document.status,
    })),
    suppliers: item.suppliers.map((relation) => ({
      conversionFactor:
        relation.conversion_factor == null ? null : String(relation.conversion_factor),
      currency: relation.currency,
      id: relation.id,
      isActive: relation.is_active,
      lastKnownPrice: relation.last_known_price == null ? null : String(relation.last_known_price),
      leadTimeDays: relation.lead_time_days,
      minimumOrderQty:
        relation.minimum_order_qty == null ? null : String(relation.minimum_order_qty),
      notes: relation.notes ?? null,
      purchaseUom: relation.purchase_uom ?? null,
      supplierId: relation.supplier_id,
      supplierName: relation.supplier_name,
      supplierSku: relation.supplier_sku ?? null,
    })),
    unitsConversion: {
      baseUom: item.units_conversion.base_uom,
      consumptionUom: item.units_conversion.consumption_uom,
      conversionFactor:
        item.units_conversion.conversion_factor == null
          ? null
          : String(item.units_conversion.conversion_factor),
      minimumPurchaseQuantity:
        item.units_conversion.minimum_purchase_quantity == null
          ? null
          : String(item.units_conversion.minimum_purchase_quantity),
      purchaseUom: item.units_conversion.purchase_uom ?? null,
      unitConversionSupported: item.units_conversion.unit_conversion_supported,
    },
  };
}

function mapListResponseFromApi(response: ApiListResponse): AdminInputSupplyListResponse {
  return {
    backendContract: mapBackendContract(response.backend_contract),
    filterOptions: {
      classes: mapFilterOptions(response.filter_options.classes),
      costStates: mapFilterOptions(response.filter_options.cost_states),
      productKinds: mapFilterOptions(response.filter_options.product_kinds),
      recipeUsageStates: mapFilterOptions(response.filter_options.recipe_usage_states),
      statuses: mapFilterOptions(response.filter_options.statuses),
      stockStates: mapFilterOptions(response.filter_options.stock_states),
      suppliers: mapFilterOptions(response.filter_options.suppliers),
      usageTypes: mapFilterOptions(response.filter_options.usage_types),
      warningStates: mapFilterOptions(response.filter_options.warning_states),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminInputSupplyListItemFromApi),
    metrics: {
      activeConsumables: mapMetric(response.metrics.active_consumables),
      activeDisposables: mapMetric(response.metrics.active_disposables),
      activeRawMaterials: mapMetric(response.metrics.active_raw_materials),
      lowStock: mapMetric(response.metrics.low_stock),
      missingCost: mapMetric(response.metrics.missing_cost),
      usedInRecipes: mapMetric(response.metrics.used_in_recipes),
      withoutSupplier: mapMetric(response.metrics.without_supplier),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function toSupplierRelationPayload(
  payload: AdminInputSupplySupplierRelationPayload,
): ApiSupplierRelationPayload {
  return {
    conversion_factor: payload.conversionFactor ?? null,
    currency: payload.currency ?? "MXN",
    is_active: payload.isActive ?? true,
    last_known_price: payload.lastKnownPrice ?? null,
    lead_time_days: payload.leadTimeDays ?? 0,
    minimum_order_qty: payload.minimumOrderQty ?? null,
    notes: payload.notes ?? null,
    purchase_uom: payload.purchaseUom ?? null,
    supplier_id: payload.supplierId,
    supplier_sku: payload.supplierSku ?? null,
  };
}

function toInputSupplyPayload(payload: AdminInputSupplyPayload): ApiPayload {
  return {
    code: payload.code,
    is_active: payload.isActive,
    is_inventory_tracked: payload.isInventoryTracked,
    is_purchasable: payload.isPurchasable,
    minimum_stock: payload.minimumStock ?? null,
    name: payload.name,
    preferred_order_quantity: payload.preferredOrderQuantity ?? null,
    procurement_notes: payload.procurementNotes ?? null,
    product_class_id: payload.productClassId,
    product_kind: payload.productKind,
    purchase_conversion_factor: payload.purchaseConversionFactor ?? null,
    purchase_uom: payload.purchaseUom ?? null,
    reorder_point: payload.reorderPoint ?? null,
    standard_cost: payload.standardCost ?? null,
    supplier_relations: payload.supplierRelations.map(toSupplierRelationPayload),
    unit_of_measure: payload.unitOfMeasure,
    usage_type: payload.usageType ?? null,
  };
}

export function buildAdminInputSuppliesListPath(filters: AdminInputSupplyListFilters): string {
  const params = new URLSearchParams();
  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "class_id", filters.classId);
  appendOptionalParam(params, "cost_state", filters.costState);
  appendBooleanParam(params, "inventory_tracked", filters.inventoryTracked);
  appendOptionalParam(params, "product_kind", filters.productKind);
  appendBooleanParam(params, "purchasable", filters.purchasable);
  appendOptionalParam(params, "recipe_usage", filters.recipeUsage);
  appendOptionalParam(params, "search", filters.search?.trim());
  appendOptionalParam(params, "status", filters.status);
  appendOptionalParam(params, "stock_state", filters.stockState);
  appendOptionalParam(params, "supplier_id", filters.supplierId);
  appendOptionalParam(params, "usage_type", filters.usageType);
  appendOptionalParam(params, "warning_state", filters.warningState);
  appendBooleanParam(params, "without_supplier", filters.withoutSupplier);
  return `/v1/admin/inputs-supplies?${params.toString()}`;
}

export function fetchAdminInputSupplies(
  accessToken: string,
  filters: AdminInputSupplyListFilters,
): Promise<AdminInputSupplyListResponse> {
  return requestJson<ApiListResponse>({
    accessToken,
    path: buildAdminInputSuppliesListPath(filters),
  }).then(mapListResponseFromApi);
}

export function fetchAdminInputSupplyDetail(
  accessToken: string,
  productId: string,
): Promise<AdminInputSupplyDetail> {
  return requestJson<ApiDetail>({
    accessToken,
    path: `/v1/admin/inputs-supplies/${productId}`,
  }).then(mapAdminInputSupplyDetailFromApi);
}

export function createAdminInputSupply(
  accessToken: string,
  payload: AdminInputSupplyPayload,
): Promise<AdminInputSupplyDetail> {
  return requestJson<ApiDetail>({
    accessToken,
    body: toInputSupplyPayload(payload),
    method: "POST",
    path: "/v1/admin/inputs-supplies",
  }).then(mapAdminInputSupplyDetailFromApi);
}

export function updateAdminInputSupply(
  accessToken: string,
  productId: string,
  payload: AdminInputSupplyPayload,
): Promise<AdminInputSupplyDetail> {
  return requestJson<ApiDetail>({
    accessToken,
    body: toInputSupplyPayload(payload),
    method: "PATCH",
    path: `/v1/admin/inputs-supplies/${productId}`,
  }).then(mapAdminInputSupplyDetailFromApi);
}

export function changeAdminInputSupplyStatus(
  accessToken: string,
  productId: string,
  payload: AdminInputSupplyStatusPayload,
): Promise<AdminInputSupplyDetail> {
  const body: ApiStatusPayload = {
    is_active: payload.isActive,
    notes: payload.notes ?? null,
  };
  return requestJson<ApiDetail>({
    accessToken,
    body,
    method: "POST",
    path: `/v1/admin/inputs-supplies/${productId}/status`,
  }).then(mapAdminInputSupplyDetailFromApi);
}

export function addAdminInputSupplySupplierRelation(
  accessToken: string,
  productId: string,
  payload: AdminInputSupplySupplierRelationPayload,
): Promise<AdminInputSupplyDetail> {
  return requestJson<ApiDetail>({
    accessToken,
    body: toSupplierRelationPayload(payload),
    method: "POST",
    path: `/v1/admin/inputs-supplies/${productId}/suppliers`,
  }).then(mapAdminInputSupplyDetailFromApi);
}
