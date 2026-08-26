import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminDiscount,
  AdminDiscountBackendContract,
  AdminDiscountDuplicatePayload,
  AdminDiscountFilterOption,
  AdminDiscountListFilters,
  AdminDiscountListResponse,
  AdminDiscountSavePayload,
} from "./types";

export const adminDiscountsBackendContract: AdminDiscountBackendContract = {
  createEndpoint: "POST /v1/admin/discounts",
  detailEndpoint: "GET /v1/admin/discounts/{id}",
  duplicateEndpoint: "POST /v1/admin/discounts/{id}/duplicate",
  listEndpoint: "GET /v1/admin/discounts",
  updateEndpoint: "PATCH /v1/admin/discounts/{id}",
};

type ApiDiscount = components["schemas"]["AdminCommercialDiscountView"];
type ApiDiscountListResponse = components["schemas"]["AdminCommercialDiscountsListResponse"];
type ApiDiscountFilterOption = components["schemas"]["AdminCommercialDiscountFilterOptionView"];
type ApiDiscountCreatePayload = components["schemas"]["AdminCommercialDiscountCreateRequest"];
type ApiDiscountUpdatePayload = components["schemas"]["AdminCommercialDiscountUpdateRequest"];
type ApiDiscountDuplicatePayload = components["schemas"]["AdminCommercialDiscountDuplicateRequest"];

function appendOptionalParam(params: URLSearchParams, key: string, value: string | null | undefined) {
  if (!value || value === "all") {
    return;
  }

  params.set(key, value);
}

function mapOption(option: ApiDiscountFilterOption): AdminDiscountFilterOption {
  return {
    id: option.id,
    label: option.label,
  };
}

function mapMetric(value: number): string {
  return String(value);
}

export function mapAdminDiscountFromApi(item: ApiDiscount): AdminDiscount {
  return {
    basePrice: item.base_price == null ? null : String(item.base_price),
    brandId: item.brand_id ?? null,
    brandName: item.brand_name ?? null,
    code: item.code ?? null,
    createdAt: item.created_at,
    currencyCode: item.currency_code,
    description: item.description ?? null,
    discountType: item.discount_type,
    health: item.health,
    id: item.id,
    isPosEligible: item.is_pos_eligible,
    name: item.name,
    previewPrice: item.preview_price == null ? null : String(item.preview_price),
    priority: item.priority,
    status: item.status,
    targetClassId: item.target_class_id ?? null,
    targetClassName: item.target_class_name ?? null,
    targetCode: item.target_code ?? null,
    targetId: item.target_id ?? null,
    targetName: item.target_name ?? null,
    targetScope: item.target_scope,
    targetStatus: item.target_status ?? null,
    updatedAt: item.updated_at,
    validFromUtc: item.valid_from_utc ?? null,
    validToUtc: item.valid_to_utc ?? null,
    validityStatus: item.validity_status,
    value: String(item.value),
    warnings: {
      codes: item.warnings.codes,
      messages: item.warnings.messages,
    },
  };
}

function mapListFromApi(response: ApiDiscountListResponse): AdminDiscountListResponse {
  return {
    backendContract: adminDiscountsBackendContract,
    filterOptions: {
      brands: response.filter_options.brands.map(mapOption),
      classes: response.filter_options.classes.map(mapOption),
      products: response.filter_options.products.map(mapOption),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminDiscountFromApi),
    metrics: {
      activeDiscounts: mapMetric(response.metrics.active_discounts),
      classScoped: mapMetric(response.metrics.class_scoped),
      expiredDiscounts: mapMetric(response.metrics.expired_discounts),
      productScoped: mapMetric(response.metrics.product_scoped),
      totalDiscounts: mapMetric(response.metrics.total_discounts),
      upcomingDiscounts: mapMetric(response.metrics.upcoming_discounts),
      withWarnings: mapMetric(response.metrics.with_warnings),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function toSaveApiPayload(payload: AdminDiscountSavePayload): ApiDiscountCreatePayload {
  return {
    brand_id: payload.brandId ?? null,
    code: payload.code ?? null,
    currency_code: payload.currencyCode,
    description: payload.description ?? null,
    discount_type: payload.discountType,
    is_pos_eligible: payload.isPosEligible,
    name: payload.name,
    priority: payload.priority,
    status: payload.status,
    target_id: payload.targetId ?? null,
    target_scope: payload.targetScope,
    valid_from_utc: payload.validFromUtc ?? null,
    valid_to_utc: payload.validToUtc ?? null,
    value: payload.value,
  };
}

function toUpdateApiPayload(payload: AdminDiscountSavePayload): ApiDiscountUpdatePayload {
  return toSaveApiPayload(payload);
}

function toDuplicateApiPayload(payload: AdminDiscountDuplicatePayload): ApiDiscountDuplicatePayload {
  return {
    code: payload.code ?? null,
    name: payload.name ?? null,
  };
}

export function buildAdminDiscountsListPath(filters: AdminDiscountListFilters): string {
  const params = new URLSearchParams();

  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "brand_id", filters.brandId);
  appendOptionalParam(params, "class_id", filters.classId);
  appendOptionalParam(params, "discount_type", filters.discountType);
  appendOptionalParam(params, "search", filters.search?.trim());
  appendOptionalParam(params, "status", filters.status);
  appendOptionalParam(params, "target_scope", filters.targetScope);
  appendOptionalParam(params, "validity", filters.validity);
  appendOptionalParam(params, "warning_state", filters.warningState);

  return `/v1/admin/discounts?${params.toString()}`;
}

export function fetchAdminDiscounts(
  accessToken: string,
  filters: AdminDiscountListFilters,
): Promise<AdminDiscountListResponse> {
  return requestJson<ApiDiscountListResponse>({
    accessToken,
    path: buildAdminDiscountsListPath(filters),
  }).then(mapListFromApi);
}

export function fetchAdminDiscountDetail(accessToken: string, discountId: string): Promise<AdminDiscount> {
  return requestJson<ApiDiscount>({
    accessToken,
    path: `/v1/admin/discounts/${discountId}`,
  }).then(mapAdminDiscountFromApi);
}

export function createAdminDiscount(
  accessToken: string,
  payload: AdminDiscountSavePayload,
): Promise<AdminDiscount> {
  return requestJson<ApiDiscount>({
    accessToken,
    body: toSaveApiPayload(payload),
    method: "POST",
    path: "/v1/admin/discounts",
  }).then(mapAdminDiscountFromApi);
}

export function updateAdminDiscount(
  accessToken: string,
  discountId: string,
  payload: AdminDiscountSavePayload,
): Promise<AdminDiscount> {
  return requestJson<ApiDiscount>({
    accessToken,
    body: toUpdateApiPayload(payload),
    method: "PATCH",
    path: `/v1/admin/discounts/${discountId}`,
  }).then(mapAdminDiscountFromApi);
}

export function duplicateAdminDiscount(
  accessToken: string,
  discountId: string,
  payload: AdminDiscountDuplicatePayload,
): Promise<AdminDiscount> {
  return requestJson<ApiDiscount>({
    accessToken,
    body: toDuplicateApiPayload(payload),
    method: "POST",
    path: `/v1/admin/discounts/${discountId}/duplicate`,
  }).then(mapAdminDiscountFromApi);
}
