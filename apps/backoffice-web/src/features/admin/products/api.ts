import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminProduct,
  AdminProductBackendContract,
  AdminProductBranchAvailability,
  AdminProductCreatePayload,
  AdminProductFilterOption,
  AdminProductListFilters,
  AdminProductListResponse,
  AdminProductUpdatePayload,
} from "./types";

export const adminProductsBackendContract: AdminProductBackendContract = {
  availabilityEndpoint: "POST /v1/admin/products/{id}/availability",
  createEndpoint: "POST /v1/admin/products",
  detailEndpoint: "GET /v1/admin/products/{id}",
  expectedListFields: [
    "id",
    "name",
    "code",
    "classId",
    "className",
    "captureMode",
    "status",
    "availability",
    "readiness",
    "updatedAt",
  ],
  listEndpoint: "GET /v1/admin/products",
  updateEndpoint: "PATCH /v1/admin/products/{id}",
};

type AdminProductApiFilterOption = components["schemas"]["AdminProductFilterOptionView"];
type AdminProductApiBranchAvailability = components["schemas"]["AdminProductBranchAvailabilityView"];
type AdminProductApiView = components["schemas"]["AdminProductView"];
type AdminProductsListApiResponse = components["schemas"]["AdminProductsListResponse"];
type AdminProductCreateApiPayload = components["schemas"]["AdminProductCreateRequest"];
type AdminProductUpdateApiPayload = components["schemas"]["AdminProductUpdateRequest"];

function appendOptionalParam(params: URLSearchParams, key: string, value: string | null | undefined) {
  if (!value || value === "all") {
    return;
  }

  params.set(key, value);
}

function mapFilterOptions(options: AdminProductApiFilterOption[]): AdminProductFilterOption[] {
  return options.map((option) => ({
    id: option.id,
    label: option.label,
  }));
}

function mapBranchAvailability(item: AdminProductApiBranchAvailability): AdminProductBranchAvailability {
  return {
    branchId: item.branch_id,
    branchName: item.branch_name,
    brandId: item.brand_id ?? null,
    brandName: item.brand_name ?? null,
    state: item.state,
    updatedAt: item.updated_at ?? null,
    visibleInPos: item.visible_in_pos,
  };
}

function mapMetric(value: number | null | undefined): string | null {
  return value == null ? null : String(value);
}

export function mapAdminProductFromApi(item: AdminProductApiView): AdminProduct {
  return {
    availability: {
      configuredBranchesCount: item.availability.configured_branches_count ?? null,
      state: item.availability.state,
      totalBranchesCount: item.availability.total_branches_count ?? null,
    },
    branchAvailability: item.branch_availability.map(mapBranchAvailability),
    brandId: item.brand_id ?? null,
    brandName: item.brand_name ?? null,
    captureMode: item.capture_mode,
    classId: item.class_id ?? null,
    className: item.class_name ?? null,
    code: item.code ?? null,
    currencyCode: item.currency_code,
    description: item.description ?? null,
    id: item.id,
    name: item.name,
    readiness: {
      missingRequirements: item.readiness.missing_requirements,
      related: {
        auditTrail: item.readiness.related.audit_trail,
        branchAvailability: item.readiness.related.branch_availability,
        inventory: item.readiness.related.inventory,
        posVisibility: item.readiness.related.pos_visibility,
        price: item.readiness.related.price,
        recipe: item.readiness.related.recipe,
      },
      status: item.readiness.status,
    },
    sku: item.sku ?? null,
    status: item.status,
    unitOfMeasure: null,
    unitPrice: String(item.unit_price),
    updatedAt: item.updated_at ?? null,
    visibleInPos: item.visible_in_pos,
  };
}

function mapAdminProductsListFromApi(response: AdminProductsListApiResponse): AdminProductListResponse {
  return {
    backendContract: adminProductsBackendContract,
    filterOptions: {
      branches: mapFilterOptions(response.filter_options.branches),
      brands: mapFilterOptions(response.filter_options.brands),
      classes: mapFilterOptions(response.filter_options.classes),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminProductFromApi),
    metrics: {
      activeProducts: mapMetric(response.metrics.active_products),
      classCapture: mapMetric(response.metrics.class_capture),
      productDirect: mapMetric(response.metrics.product_direct),
      requireAttention: mapMetric(response.metrics.require_attention),
      withoutBranchAvailability: mapMetric(response.metrics.without_branch_availability),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function toCreateApiPayload(payload: AdminProductCreatePayload): AdminProductCreateApiPayload {
  return {
    capture_mode: payload.captureMode,
    code: payload.code,
    name: payload.name,
    product_class_id: payload.productClassId,
    quick_name: payload.quickName ?? null,
    search_aliases: payload.searchAliases ?? null,
    status: payload.status,
    unit_price: payload.unitPrice,
  };
}

function toUpdateApiPayload(payload: AdminProductUpdatePayload): AdminProductUpdateApiPayload {
  return {
    capture_mode: payload.captureMode,
    code: payload.code,
    name: payload.name,
    product_class_id: payload.productClassId,
    quick_name: payload.quickName,
    search_aliases: payload.searchAliases,
    status: payload.status,
    unit_price: payload.unitPrice,
  };
}

export function buildAdminProductsListPath(filters: AdminProductListFilters): string {
  const params = new URLSearchParams();

  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "brand_id", filters.brandId);
  appendOptionalParam(params, "branch_id", filters.branchId);
  appendOptionalParam(params, "class_id", filters.classId);
  appendOptionalParam(params, "capture_mode", filters.captureMode);
  appendOptionalParam(params, "readiness", filters.readiness);
  appendOptionalParam(params, "search", filters.search?.trim());
  appendOptionalParam(params, "status", filters.status);

  return `/v1/admin/products?${params.toString()}`;
}

export function fetchAdminProducts(
  accessToken: string,
  filters: AdminProductListFilters,
): Promise<AdminProductListResponse> {
  return requestJson<AdminProductsListApiResponse>({
    accessToken,
    path: buildAdminProductsListPath(filters),
  }).then(mapAdminProductsListFromApi);
}

export function fetchAdminProductDetail(accessToken: string, productId: string): Promise<AdminProduct> {
  return requestJson<AdminProductApiView>({
    accessToken,
    path: `/v1/admin/products/${productId}`,
  }).then(mapAdminProductFromApi);
}

export function createAdminProduct(
  accessToken: string,
  payload: AdminProductCreatePayload,
): Promise<AdminProduct> {
  return requestJson<AdminProductApiView>({
    accessToken,
    body: toCreateApiPayload(payload),
    method: "POST",
    path: "/v1/admin/products",
  }).then(mapAdminProductFromApi);
}

export function updateAdminProduct(
  accessToken: string,
  productId: string,
  payload: AdminProductUpdatePayload,
): Promise<AdminProduct> {
  return requestJson<AdminProductApiView>({
    accessToken,
    body: toUpdateApiPayload(payload),
    method: "PATCH",
    path: `/v1/admin/products/${productId}`,
  }).then(mapAdminProductFromApi);
}
