import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminProductClass,
  AdminProductClassBackendContract,
  AdminProductClassCreatePayload,
  AdminProductClassFilterOption,
  AdminProductClassListFilters,
  AdminProductClassListResponse,
  AdminProductClassProductSummary,
  AdminProductClassUpdatePayload,
} from "./types";

export const adminProductClassesBackendContract: AdminProductClassBackendContract = {
  createEndpoint: "POST /v1/admin/product-classes",
  detailEndpoint: "GET /v1/admin/product-classes/{id}",
  listEndpoint: "GET /v1/admin/product-classes",
  updateEndpoint: "PATCH /v1/admin/product-classes/{id}",
};

type AdminProductClassApiFilterOption = components["schemas"]["AdminProductFilterOptionView"];
type AdminProductClassApiProductSummary = components["schemas"]["AdminProductClassProductSummaryView"];
type AdminProductClassApiView = components["schemas"]["AdminProductClassView"];
type AdminProductClassesListApiResponse = components["schemas"]["AdminProductClassesListResponse"];
type AdminProductClassCreateApiPayload = components["schemas"]["AdminProductClassCreateRequest"];
type AdminProductClassUpdateApiPayload = components["schemas"]["AdminProductClassUpdateRequest"];

function appendOptionalParam(params: URLSearchParams, key: string, value: string | null | undefined) {
  if (!value || value === "all") {
    return;
  }

  params.set(key, value);
}

function mapFilterOptions(
  options: AdminProductClassApiFilterOption[],
): AdminProductClassFilterOption[] {
  return options.map((option) => ({
    id: option.id,
    label: option.label,
  }));
}

function mapProductSummaryFromApi(
  item: AdminProductClassApiProductSummary,
): AdminProductClassProductSummary {
  return {
    code: item.code,
    id: item.id,
    name: item.name,
    status: item.status,
    unitPrice: String(item.unit_price),
    updatedAt: item.updated_at ?? null,
  };
}

function mapMetric(value: number): string {
  return String(value);
}

export function mapAdminProductClassFromApi(item: AdminProductClassApiView): AdminProductClass {
  return {
    activeProductCount: item.active_product_count,
    brandId: item.brand_id,
    brandName: item.brand_name,
    captureModeDefault: item.capture_mode_default,
    classCaptureUnitPrice: item.class_capture_unit_price ?? null,
    code: item.code,
    currencyCode: item.currency_code,
    displayOrder: item.display_order,
    id: item.id,
    inactiveProductCount: item.inactive_product_count,
    isSellable: item.is_sellable,
    linkedProducts: item.linked_products.map(mapProductSummaryFromApi),
    name: item.name,
    productCount: item.product_count,
    quickName: item.quick_name ?? null,
    readiness: item.readiness,
    searchAliases: item.search_aliases ?? null,
    status: item.status,
    updatedAt: item.updated_at ?? null,
    warnings: {
      codes: item.warnings.codes,
      messages: item.warnings.messages,
    },
  };
}

function mapAdminProductClassesListFromApi(
  response: AdminProductClassesListApiResponse,
): AdminProductClassListResponse {
  return {
    backendContract: adminProductClassesBackendContract,
    filterOptions: {
      brands: mapFilterOptions(response.filter_options.brands),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminProductClassFromApi),
    metrics: {
      activeClasses: mapMetric(response.metrics.active_classes),
      classCapture: mapMetric(response.metrics.class_capture),
      productDirect: mapMetric(response.metrics.product_direct),
      totalClasses: mapMetric(response.metrics.total_classes),
      withWarnings: mapMetric(response.metrics.with_warnings),
      withoutProducts: mapMetric(response.metrics.without_products),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function toCreateApiPayload(payload: AdminProductClassCreatePayload): AdminProductClassCreateApiPayload {
  return {
    brand_id: payload.brandId,
    capture_mode_default: payload.captureModeDefault,
    class_capture_unit_price: payload.classCaptureUnitPrice ?? null,
    code: payload.code,
    currency_code: payload.currencyCode,
    display_order: payload.displayOrder,
    is_sellable: payload.isSellable,
    name: payload.name,
    quick_name: payload.quickName ?? null,
    search_aliases: payload.searchAliases ?? null,
    status: payload.status,
  };
}

function toUpdateApiPayload(payload: AdminProductClassUpdatePayload): AdminProductClassUpdateApiPayload {
  return {
    brand_id: payload.brandId,
    capture_mode_default: payload.captureModeDefault,
    class_capture_unit_price: payload.classCaptureUnitPrice,
    code: payload.code,
    currency_code: payload.currencyCode,
    display_order: payload.displayOrder,
    is_sellable: payload.isSellable,
    name: payload.name,
    quick_name: payload.quickName,
    search_aliases: payload.searchAliases,
    status: payload.status,
  };
}

export function buildAdminProductClassesListPath(filters: AdminProductClassListFilters): string {
  const params = new URLSearchParams();

  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "brand_id", filters.brandId);
  appendOptionalParam(params, "capture_mode", filters.captureMode);
  appendOptionalParam(params, "product_presence", filters.productPresence);
  appendOptionalParam(params, "search", filters.search?.trim());
  appendOptionalParam(params, "status", filters.status);

  return `/v1/admin/product-classes?${params.toString()}`;
}

export function fetchAdminProductClasses(
  accessToken: string,
  filters: AdminProductClassListFilters,
): Promise<AdminProductClassListResponse> {
  return requestJson<AdminProductClassesListApiResponse>({
    accessToken,
    path: buildAdminProductClassesListPath(filters),
  }).then(mapAdminProductClassesListFromApi);
}

export function fetchAdminProductClassDetail(
  accessToken: string,
  classId: string,
): Promise<AdminProductClass> {
  return requestJson<AdminProductClassApiView>({
    accessToken,
    path: `/v1/admin/product-classes/${classId}`,
  }).then(mapAdminProductClassFromApi);
}

export function createAdminProductClass(
  accessToken: string,
  payload: AdminProductClassCreatePayload,
): Promise<AdminProductClass> {
  return requestJson<AdminProductClassApiView>({
    accessToken,
    body: toCreateApiPayload(payload),
    method: "POST",
    path: "/v1/admin/product-classes",
  }).then(mapAdminProductClassFromApi);
}

export function updateAdminProductClass(
  accessToken: string,
  classId: string,
  payload: AdminProductClassUpdatePayload,
): Promise<AdminProductClass> {
  return requestJson<AdminProductClassApiView>({
    accessToken,
    body: toUpdateApiPayload(payload),
    method: "PATCH",
    path: `/v1/admin/product-classes/${classId}`,
  }).then(mapAdminProductClassFromApi);
}
