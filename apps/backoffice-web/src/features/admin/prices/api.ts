import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminPriceBackendContract,
  AdminPriceDetail,
  AdminPriceFilterOption,
  AdminPriceListFilters,
  AdminPriceListResponse,
  AdminPriceRow,
  AdminPriceUpdatePayload,
} from "./types";

export const adminPricesBackendContract: AdminPriceBackendContract = {
  detailEndpoint: "GET /v1/admin/prices/{entityType}/{entityId}",
  listEndpoint: "GET /v1/admin/prices",
  updateEndpoint: "PATCH /v1/admin/prices/{entityType}/{entityId}",
};

type ApiFilterOption = components["schemas"]["AdminProductFilterOptionView"];
type ApiPriceRow = components["schemas"]["AdminPriceRowView"];
type ApiPricesListResponse = components["schemas"]["AdminPricesListResponse"];
type ApiPriceDetail = components["schemas"]["AdminPriceDetailView"];
type ApiPriceUpdatePayload = components["schemas"]["AdminPriceUpdateRequest"];

function appendOptionalParam(params: URLSearchParams, key: string, value: string | null | undefined) {
  if (!value || value === "all") {
    return;
  }

  params.set(key, value);
}

function mapOption(option: ApiFilterOption): AdminPriceFilterOption {
  return {
    id: option.id,
    label: option.label,
  };
}

function mapMetric(value: number): string {
  return String(value);
}

export function mapAdminPriceRowFromApi(item: ApiPriceRow): AdminPriceRow {
  return {
    brandId: item.brand_id,
    brandName: item.brand_name,
    captureMode: item.capture_mode,
    classId: item.class_id,
    className: item.class_name,
    currencyCode: item.currency_code,
    currentPrice: item.current_price == null ? null : String(item.current_price),
    entityCode: item.entity_code,
    entityId: item.entity_id,
    entityName: item.entity_name,
    entityType: item.entity_type,
    health: item.health,
    marginPercent: item.margin_percent == null ? null : String(item.margin_percent),
    priceCostDelta: item.price_cost_delta == null ? null : String(item.price_cost_delta),
    priceOwner: item.price_owner,
    relatedClassId: item.related_class_id,
    relatedProductId: item.related_product_id ?? null,
    standardCost: item.standard_cost == null ? null : String(item.standard_cost),
    status: item.status,
    updatedAt: item.updated_at ?? null,
    warnings: {
      codes: item.warnings.codes,
      messages: item.warnings.messages,
    },
  };
}

function mapListFromApi(response: ApiPricesListResponse): AdminPriceListResponse {
  return {
    backendContract: adminPricesBackendContract,
    filterOptions: {
      brands: response.filter_options.brands.map(mapOption),
      classes: response.filter_options.classes.map(mapOption),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminPriceRowFromApi),
    metrics: {
      classCapture: mapMetric(response.metrics.class_capture),
      highVariance: mapMetric(response.metrics.high_variance),
      missingOrInvalid: mapMetric(response.metrics.missing_or_invalid),
      productDirect: mapMetric(response.metrics.product_direct),
      recentlyChanged: mapMetric(response.metrics.recently_changed),
      totalEntities: mapMetric(response.metrics.total_entities),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function mapDetailFromApi(response: ApiPriceDetail): AdminPriceDetail {
  return {
    historyNote: response.history_note ?? null,
    price: mapAdminPriceRowFromApi(response.price),
  };
}

function toUpdateApiPayload(payload: AdminPriceUpdatePayload): ApiPriceUpdatePayload {
  return {
    price: payload.price,
  };
}

export function buildAdminPricesListPath(filters: AdminPriceListFilters): string {
  const params = new URLSearchParams();

  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "brand_id", filters.brandId);
  appendOptionalParam(params, "capture_mode", filters.captureMode);
  appendOptionalParam(params, "class_id", filters.classId);
  appendOptionalParam(params, "entity_type", filters.entityType);
  appendOptionalParam(params, "price_health", filters.priceHealth);
  appendOptionalParam(params, "search", filters.search?.trim());
  appendOptionalParam(params, "status", filters.status);
  appendOptionalParam(params, "updated_from", filters.updatedFrom);
  appendOptionalParam(params, "updated_to", filters.updatedTo);

  return `/v1/admin/prices?${params.toString()}`;
}

export function fetchAdminPrices(
  accessToken: string,
  filters: AdminPriceListFilters,
): Promise<AdminPriceListResponse> {
  return requestJson<ApiPricesListResponse>({
    accessToken,
    path: buildAdminPricesListPath(filters),
  }).then(mapListFromApi);
}

export function fetchAdminPriceDetail(
  accessToken: string,
  entityType: string,
  entityId: string,
): Promise<AdminPriceDetail> {
  return requestJson<ApiPriceDetail>({
    accessToken,
    path: `/v1/admin/prices/${entityType}/${entityId}`,
  }).then(mapDetailFromApi);
}

export function updateAdminPrice(
  accessToken: string,
  row: AdminPriceRow,
  payload: AdminPriceUpdatePayload,
): Promise<AdminPriceDetail> {
  return requestJson<ApiPriceDetail>({
    accessToken,
    body: toUpdateApiPayload(payload),
    method: "PATCH",
    path: `/v1/admin/prices/${row.entityType}/${row.entityId}`,
  }).then(mapDetailFromApi);
}
