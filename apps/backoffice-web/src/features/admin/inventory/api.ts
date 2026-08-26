import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminInventoryAdjustment,
  AdminInventoryAdjustmentPayload,
  AdminInventoryBackendContract,
  AdminInventoryDetail,
  AdminInventoryFilterOption,
  AdminInventoryListFilters,
  AdminInventoryListItem,
  AdminInventoryListResponse,
  AdminInventoryMovement,
  AdminInventoryMovementsResponse,
  AdminInventoryWarning,
} from "./types";

export const adminInventoryBackendContract: AdminInventoryBackendContract = {
  adjustmentEndpoint: "POST /v1/admin/inventory/adjustments",
  detailEndpoint: "GET /v1/admin/inventory/{balance_id}",
  listEndpoint: "GET /v1/admin/inventory",
  movementsEndpoint: "GET /v1/admin/inventory/{balance_id}/movements",
};

type AdminInventoryApiFilterOption = components["schemas"]["AdminInventoryFilterOptionView"];
type AdminInventoryApiWarning = components["schemas"]["AdminInventoryWarningView"];
type AdminInventoryApiListItem = components["schemas"]["AdminInventoryListItemView"];
type AdminInventoryApiListResponse = components["schemas"]["AdminInventoryListResponse"];
type AdminInventoryApiDetail = components["schemas"]["AdminInventoryDetailView"];
type AdminInventoryApiMovement = components["schemas"]["AdminInventoryMovementView"];
type AdminInventoryApiMovementsResponse = components["schemas"]["AdminInventoryMovementsResponse"];
type AdminInventoryApiAdjustmentPayload = components["schemas"]["AdminInventoryAdjustmentRequest"];
type AdminInventoryApiAdjustment = components["schemas"]["AdminInventoryAdjustmentView"];

function appendOptionalParam(params: URLSearchParams, key: string, value: string | null | undefined) {
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

function mapFilterOptions(options: AdminInventoryApiFilterOption[]): AdminInventoryFilterOption[] {
  return options.map((option) => ({
    id: String(option.id),
    label: option.label,
  }));
}

function mapWarningFromApi(warning: AdminInventoryApiWarning): AdminInventoryWarning {
  return {
    code: warning.code,
    message: warning.message,
    severity: warning.severity,
  };
}

export function mapAdminInventoryMovementFromApi(item: AdminInventoryApiMovement): AdminInventoryMovement {
  return {
    balanceAfter: item.balance_after ?? null,
    branchId: item.branch_id,
    branchName: item.branch_name,
    direction: item.direction,
    id: item.id,
    locationCode: item.location_code,
    movementType: item.movement_type,
    notes: item.notes ?? null,
    occurredAt: item.occurred_at,
    operatorName: item.operator_name ?? null,
    productId: item.product_id,
    quantity: item.quantity,
    reason: item.reason ?? null,
    sourceDocumentId: item.source_document_id ?? null,
    sourceDocumentType: item.source_document_type ?? null,
    unitOfMeasure: item.unit_of_measure,
  };
}

export function mapAdminInventoryListItemFromApi(item: AdminInventoryApiListItem): AdminInventoryListItem {
  return {
    availableQuantity: item.available_quantity ?? null,
    balanceId: item.balance_id,
    branchId: item.branch_id,
    branchIsActive: item.branch_is_active,
    branchName: item.branch_name,
    classId: item.class_id,
    className: item.class_name,
    inTransitQuantity: item.in_transit_quantity ?? null,
    lastMovementAt: item.last_movement_at ?? null,
    locationCode: item.location_code,
    locationName: item.location_name,
    productCode: item.product_code,
    productId: item.product_id,
    productIsActive: item.product_is_active,
    productKind: item.product_kind,
    productName: item.product_name,
    quantityOnHand: item.quantity_on_hand,
    reservedQuantity: item.reserved_quantity ?? null,
    stockState: item.stock_state,
    unitOfMeasure: item.unit_of_measure,
    warningState: item.warning_state ?? null,
    warnings: item.warnings.map(mapWarningFromApi),
  };
}

export function mapAdminInventoryDetailFromApi(item: AdminInventoryApiDetail): AdminInventoryDetail {
  return {
    balanceId: item.balance_id,
    branchLocation: {
      branchId: item.branch_location.branch_id,
      branchIsActive: item.branch_location.branch_is_active,
      branchName: item.branch_location.branch_name,
      locationCode: item.branch_location.location_code,
      locationModelSupported: item.branch_location.location_model_supported,
      locationName: item.branch_location.location_name,
    },
    movementSummary: {
      lastAdjustmentAt: item.movement_summary.last_adjustment_at ?? null,
      lastInboundAt: item.movement_summary.last_inbound_at ?? null,
      lastMovementAt: item.movement_summary.last_movement_at ?? null,
      lastOutboundAt: item.movement_summary.last_outbound_at ?? null,
    },
    movements: item.movements.map(mapAdminInventoryMovementFromApi),
    product: {
      classId: item.product.class_id,
      className: item.product.class_name,
      code: item.product.code,
      id: item.product.id,
      isActive: item.product.is_active,
      isSellable: item.product.is_sellable,
      name: item.product.name,
      productKind: item.product.product_kind,
      standardCost: item.product.standard_cost ?? null,
      unitOfMeasure: item.product.unit_of_measure,
    },
    relatedActions: {
      canCreateAdjustment: item.related_actions.can_create_adjustment,
      canOpenBranch: item.related_actions.can_open_branch,
      canOpenProduct: item.related_actions.can_open_product,
      canStartCount: item.related_actions.can_start_count,
      countEndpointAvailable: item.related_actions.count_endpoint_available,
    },
    stockBreakdown: {
      availableQuantity: item.stock_breakdown.available_quantity ?? null,
      estimatedValue: item.stock_breakdown.estimated_value ?? null,
      inTransitQuantity: item.stock_breakdown.in_transit_quantity ?? null,
      quantityOnHand: item.stock_breakdown.quantity_on_hand,
      reservedQuantity: item.stock_breakdown.reserved_quantity ?? null,
      unitOfMeasure: item.stock_breakdown.unit_of_measure,
    },
    stockState: item.stock_state,
    warnings: item.warnings.map(mapWarningFromApi),
  };
}

function mapAdminInventoryListFromApi(response: AdminInventoryApiListResponse): AdminInventoryListResponse {
  return {
    backendContract: adminInventoryBackendContract,
    filterOptions: {
      branches: mapFilterOptions(response.filter_options.branches),
      classes: mapFilterOptions(response.filter_options.classes),
      locations: mapFilterOptions(response.filter_options.locations),
      productKinds: mapFilterOptions(response.filter_options.product_kinds),
      products: mapFilterOptions(response.filter_options.products),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminInventoryListItemFromApi),
    metrics: {
      estimatedValue: response.metrics.estimated_value ?? null,
      negativeStock: mapMetric(response.metrics.negative_stock),
      productsWithStock: mapMetric(response.metrics.products_with_stock),
      staleStock: mapMetric(response.metrics.stale_stock),
      totalRecords: mapMetric(response.metrics.total_records),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function mapAdminInventoryAdjustmentFromApi(item: AdminInventoryApiAdjustment): AdminInventoryAdjustment {
  return {
    adjustmentType: item.adjustment_type,
    balanceId: item.balance_id,
    branchId: item.branch_id,
    createdAt: item.created_at,
    createdByUserId: item.created_by_user_id,
    id: item.id,
    locationCode: item.location_code,
    newQuantity: item.new_quantity,
    notes: item.notes ?? null,
    previousQuantity: item.previous_quantity,
    productId: item.product_id,
    quantity: item.quantity,
    reason: item.reason,
  };
}

function toAdjustmentApiPayload(payload: AdminInventoryAdjustmentPayload): AdminInventoryApiAdjustmentPayload {
  return {
    adjustment_type: payload.adjustmentType,
    branch_id: payload.branchId,
    location_code: payload.locationCode,
    notes: payload.notes ?? null,
    product_id: payload.productId,
    quantity: payload.quantity,
    reason: payload.reason,
  };
}

export function buildAdminInventoryListPath(filters: AdminInventoryListFilters): string {
  const params = new URLSearchParams();

  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "branch_id", filters.branchId);
  appendOptionalParam(params, "class_id", filters.classId);
  appendOptionalParam(params, "location_code", filters.locationCode);
  appendOptionalParam(params, "product_kind", filters.productKind);
  appendOptionalParam(params, "product_status", filters.productStatus);
  appendOptionalParam(params, "search", filters.search?.trim());
  appendOptionalParam(params, "stock_state", filters.stockState);

  return `/v1/admin/inventory?${params.toString()}`;
}

export function fetchAdminInventory(
  accessToken: string,
  filters: AdminInventoryListFilters,
): Promise<AdminInventoryListResponse> {
  return requestJson<AdminInventoryApiListResponse>({
    accessToken,
    path: buildAdminInventoryListPath(filters),
  }).then(mapAdminInventoryListFromApi);
}

export function fetchAdminInventoryDetail(
  accessToken: string,
  balanceId: string,
): Promise<AdminInventoryDetail> {
  return requestJson<AdminInventoryApiDetail>({
    accessToken,
    path: `/v1/admin/inventory/${balanceId}`,
  }).then(mapAdminInventoryDetailFromApi);
}

export function fetchAdminInventoryMovements(
  accessToken: string,
  balanceId: string,
  page = 1,
  pageSize = 25,
): Promise<AdminInventoryMovementsResponse> {
  return requestJson<AdminInventoryApiMovementsResponse>({
    accessToken,
    path: `/v1/admin/inventory/${balanceId}/movements?page=${page}&page_size=${pageSize}`,
  }).then((response) => ({
    items: response.items.map(mapAdminInventoryMovementFromApi),
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  }));
}

export function createAdminInventoryAdjustment(
  accessToken: string,
  payload: AdminInventoryAdjustmentPayload,
): Promise<AdminInventoryAdjustment> {
  return requestJson<AdminInventoryApiAdjustment>({
    accessToken,
    body: toAdjustmentApiPayload(payload),
    method: "POST",
    path: "/v1/admin/inventory/adjustments",
  }).then(mapAdminInventoryAdjustmentFromApi);
}
