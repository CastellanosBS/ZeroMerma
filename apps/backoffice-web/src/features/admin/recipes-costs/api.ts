import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminRecipe,
  AdminRecipeCostBackendContract,
  AdminRecipeCostDetail,
  AdminRecipeCostFilterOptions,
  AdminRecipeCostListFilters,
  AdminRecipeCostListResponse,
  AdminRecipeCostProduct,
  AdminRecipeCreatePayload,
  AdminRecipeDuplicatePayload,
  AdminRecipeFilterOption,
  AdminRecipeInput,
} from "./types";

export const adminRecipeCostsBackendContract: AdminRecipeCostBackendContract = {
  applyStandardCostEndpoint: "POST /v1/admin/recipes-costs/recipes/{id}/apply-standard-cost",
  createEndpoint: "POST /v1/admin/recipes-costs/recipes",
  detailEndpoint: "GET /v1/admin/recipes-costs/products/{id}",
  duplicateEndpoint: "POST /v1/admin/recipes-costs/recipes/{id}/duplicate",
  listEndpoint: "GET /v1/admin/recipes-costs/products",
};

type ApiFilterOption = components["schemas"]["AdminProductFilterOptionView"];
type ApiRecipeCostProduct = components["schemas"]["AdminRecipeCostProductSummaryView"];
type ApiRecipeCostListResponse = components["schemas"]["AdminRecipeCostsListResponse"];
type ApiRecipeCostDetail = components["schemas"]["AdminRecipeCostDetailView"];
type ApiRecipe = components["schemas"]["AdminRecipeView"];
type ApiRecipeInput = components["schemas"]["AdminRecipeInputView"];
type ApiRecipeCreatePayload = components["schemas"]["AdminRecipeCreateRequest"];
type ApiRecipeDuplicatePayload = components["schemas"]["AdminRecipeDuplicateRequest"];

function appendOptionalParam(params: URLSearchParams, key: string, value: string | null | undefined) {
  if (!value || value === "all") {
    return;
  }

  params.set(key, value);
}

function mapOption(option: ApiFilterOption): AdminRecipeFilterOption {
  return {
    id: option.id,
    label: option.label,
  };
}

function mapOptions(options: ApiFilterOption[]): AdminRecipeFilterOption[] {
  return options.map(mapOption);
}

function mapMetric(value: number): string {
  return String(value);
}

function mapRecipeInputFromApi(item: ApiRecipeInput): AdminRecipeInput {
  return {
    extendedCost: item.extended_cost == null ? null : String(item.extended_cost),
    id: item.id,
    inputProductCode: item.input_product_code,
    inputProductId: item.input_product_id,
    inputProductName: item.input_product_name,
    quantity: String(item.quantity),
    standardCost: item.standard_cost == null ? null : String(item.standard_cost),
    status: item.status,
    unitOfMeasure: item.unit_of_measure,
  };
}

function mapRecipeFromApi(item: ApiRecipe): AdminRecipe {
  return {
    calculatedUnitCost: item.calculated_unit_cost == null ? null : String(item.calculated_unit_cost),
    createdAt: item.created_at,
    id: item.id,
    inputCount: item.input_count,
    inputs: item.inputs.map(mapRecipeInputFromApi),
    isActive: item.is_active,
    productId: item.product_id,
    totalBatchCost: item.total_batch_cost == null ? null : String(item.total_batch_cost),
    updatedAt: item.updated_at,
    versionName: item.version_name ?? null,
    yieldQty: String(item.yield_qty),
    yieldUom: item.yield_uom,
  };
}

export function mapRecipeCostProductFromApi(item: ApiRecipeCostProduct): AdminRecipeCostProduct {
  return {
    activeRecipeId: item.active_recipe_id ?? null,
    activeRecipeUpdatedAt: item.active_recipe_updated_at ?? null,
    activeRecipeVersionName: item.active_recipe_version_name ?? null,
    brandId: item.brand_id,
    brandName: item.brand_name,
    calculatedUnitCost: item.calculated_unit_cost == null ? null : String(item.calculated_unit_cost),
    classId: item.class_id,
    className: item.class_name,
    costVariance: item.cost_variance == null ? null : String(item.cost_variance),
    costVariancePercent: item.cost_variance_percent == null ? null : String(item.cost_variance_percent),
    currencyCode: item.currency_code,
    healthStatus: item.health_status,
    productCode: item.product_code,
    productId: item.product_id,
    productName: item.product_name,
    productStandardCost: item.product_standard_cost == null ? null : String(item.product_standard_cost),
    productStatus: item.product_status,
    productUnitPrice: String(item.product_unit_price),
    recipeInputCount: item.recipe_input_count,
    totalBatchCost: item.total_batch_cost == null ? null : String(item.total_batch_cost),
    unitOfMeasure: item.unit_of_measure,
    updatedAt: item.updated_at ?? null,
    warnings: {
      codes: item.warnings.codes,
      messages: item.warnings.messages,
    },
    yieldQty: item.yield_qty == null ? null : String(item.yield_qty),
    yieldUom: item.yield_uom ?? null,
  };
}

function mapFilterOptions(response: ApiRecipeCostListResponse): AdminRecipeCostFilterOptions {
  return {
    brands: mapOptions(response.filter_options.brands),
    classes: mapOptions(response.filter_options.classes),
    rawMaterials: mapOptions(response.filter_options.raw_materials),
  };
}

function mapListFromApi(response: ApiRecipeCostListResponse): AdminRecipeCostListResponse {
  return {
    backendContract: adminRecipeCostsBackendContract,
    filterOptions: mapFilterOptions(response),
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapRecipeCostProductFromApi),
    metrics: {
      highVariance: mapMetric(response.metrics.high_variance),
      recentlyUpdated: mapMetric(response.metrics.recently_updated),
      withActiveRecipe: mapMetric(response.metrics.with_active_recipe),
      withoutRecipe: mapMetric(response.metrics.without_recipe),
      withWarnings: mapMetric(response.metrics.with_warnings),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function mapDetailFromApi(response: ApiRecipeCostDetail): AdminRecipeCostDetail {
  return {
    activeRecipe: response.active_recipe ? mapRecipeFromApi(response.active_recipe) : null,
    product: mapRecipeCostProductFromApi(response.product),
    recipeVersions: response.recipe_versions.map(mapRecipeFromApi),
  };
}

function toCreatePayload(payload: AdminRecipeCreatePayload): ApiRecipeCreatePayload {
  return {
    activate: payload.activate,
    inputs: payload.inputs.map((input) => ({
      input_product_id: input.inputProductId,
      quantity: input.quantity,
    })),
    product_id: payload.productId,
    version_name: payload.versionName ?? null,
    yield_qty: payload.yieldQty,
    yield_uom: payload.yieldUom,
  };
}

function toDuplicatePayload(payload: AdminRecipeDuplicatePayload): ApiRecipeDuplicatePayload {
  return {
    activate: payload.activate,
    version_name: payload.versionName ?? null,
  };
}

export function buildAdminRecipeCostsListPath(filters: AdminRecipeCostListFilters): string {
  const params = new URLSearchParams();

  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "brand_id", filters.brandId);
  appendOptionalParam(params, "class_id", filters.classId);
  appendOptionalParam(params, "recipe_state", filters.recipeState);
  appendOptionalParam(params, "search", filters.search?.trim());

  return `/v1/admin/recipes-costs/products?${params.toString()}`;
}

export function fetchAdminRecipeCosts(
  accessToken: string,
  filters: AdminRecipeCostListFilters,
): Promise<AdminRecipeCostListResponse> {
  return requestJson<ApiRecipeCostListResponse>({
    accessToken,
    path: buildAdminRecipeCostsListPath(filters),
  }).then(mapListFromApi);
}

export function fetchAdminRecipeCostDetail(
  accessToken: string,
  productId: string,
): Promise<AdminRecipeCostDetail> {
  return requestJson<ApiRecipeCostDetail>({
    accessToken,
    path: `/v1/admin/recipes-costs/products/${productId}`,
  }).then(mapDetailFromApi);
}

export function createAdminRecipe(
  accessToken: string,
  payload: AdminRecipeCreatePayload,
): Promise<AdminRecipeCostDetail> {
  return requestJson<ApiRecipeCostDetail>({
    accessToken,
    body: toCreatePayload(payload),
    method: "POST",
    path: "/v1/admin/recipes-costs/recipes",
  }).then(mapDetailFromApi);
}

export function duplicateAdminRecipe(
  accessToken: string,
  recipeId: string,
  payload: AdminRecipeDuplicatePayload,
): Promise<AdminRecipeCostDetail> {
  return requestJson<ApiRecipeCostDetail>({
    accessToken,
    body: toDuplicatePayload(payload),
    method: "POST",
    path: `/v1/admin/recipes-costs/recipes/${recipeId}/duplicate`,
  }).then(mapDetailFromApi);
}

export function activateAdminRecipe(accessToken: string, recipeId: string): Promise<AdminRecipeCostDetail> {
  return requestJson<ApiRecipeCostDetail>({
    accessToken,
    method: "POST",
    path: `/v1/admin/recipes-costs/recipes/${recipeId}/activate`,
  }).then(mapDetailFromApi);
}

export function applyAdminRecipeStandardCost(
  accessToken: string,
  recipeId: string,
): Promise<AdminRecipeCostDetail> {
  return requestJson<ApiRecipeCostDetail>({
    accessToken,
    method: "POST",
    path: `/v1/admin/recipes-costs/recipes/${recipeId}/apply-standard-cost`,
  }).then(mapDetailFromApi);
}
