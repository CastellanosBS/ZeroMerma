import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminProductionBackendContract,
  AdminProductionCompletePayload,
  AdminProductionCreatePayload,
  AdminProductionDetail,
  AdminProductionFilterOption,
  AdminProductionListFilters,
  AdminProductionListItem,
  AdminProductionListResponse,
  AdminProductionUpdatePayload,
  AdminProductionWarning,
} from "./types";

export const adminProductionBackendContract: AdminProductionBackendContract = {
  cancelEndpoint: "POST /v1/admin/production/{production_id}/cancel",
  completeEndpoint: "POST /v1/admin/production/{production_id}/complete",
  createEndpoint: "POST /v1/admin/production",
  detailEndpoint: "GET /v1/admin/production/{production_id}",
  listEndpoint: "GET /v1/admin/production",
  startEndpoint: "POST /v1/admin/production/{production_id}/start",
  updateEndpoint: "PATCH /v1/admin/production/{production_id}",
};

type ApiProductionBackendContract = components["schemas"]["AdminProductionBackendContractView"];
type ApiProductionCompletePayload = components["schemas"]["AdminProductionCompleteRequest"];
type ApiProductionCreatePayload = components["schemas"]["AdminProductionCreateRequest"];
type ApiProductionDetail = components["schemas"]["AdminProductionDetailView"];
type ApiProductionFilterOption = components["schemas"]["AdminProductionFilterOptionView"];
type ApiProductionListItem = components["schemas"]["AdminProductionListItemView"];
type ApiProductionListResponse = components["schemas"]["AdminProductionListResponse"];
type ApiProductionUpdatePayload = components["schemas"]["AdminProductionUpdateRequest"];
type ApiProductionWarning = components["schemas"]["AdminProductionWarningView"];

function appendOptionalParam(params: URLSearchParams, key: string, value: string | null | undefined) {
  if (!value || value === "all") {
    return;
  }
  params.set(key, value);
}

function mapFilterOptions(options: ApiProductionFilterOption[]): AdminProductionFilterOption[] {
  return options.map((option) => ({ id: String(option.id), label: option.label }));
}

function mapMetric(value: number | string | null | undefined): string {
  if (value === null || value === undefined) {
    return "No disponible";
  }
  return String(value);
}

function mapBackendContract(contract?: ApiProductionBackendContract): AdminProductionBackendContract {
  if (!contract) {
    return adminProductionBackendContract;
  }

  return {
    cancelEndpoint: contract.cancel_endpoint,
    completeEndpoint: contract.complete_endpoint,
    createEndpoint: contract.create_endpoint,
    detailEndpoint: contract.detail_endpoint,
    listEndpoint: contract.list_endpoint,
    startEndpoint: contract.start_endpoint,
    updateEndpoint: contract.update_endpoint,
  };
}

function mapWarningFromApi(warning: ApiProductionWarning): AdminProductionWarning {
  return {
    code: warning.code,
    message: warning.message,
    severity: warning.severity,
  };
}

export function mapAdminProductionListItemFromApi(item: ApiProductionListItem): AdminProductionListItem {
  return {
    actualOutputQty: item.actual_output_qty ?? null,
    branchId: item.branch_id,
    branchName: item.branch_name,
    completedAt: item.completed_at ?? null,
    folio: item.folio,
    id: item.id,
    operatorName: item.operator_name,
    plannedAt: item.planned_at ?? null,
    plannedOutputQty: item.planned_output_qty,
    productCode: item.product_code,
    productId: item.product_id,
    productName: item.product_name,
    recipeId: item.recipe_id,
    recipeName: item.recipe_name,
    startedAt: item.started_at ?? null,
    status: item.status,
    variancePercent: item.variance_percent ?? null,
    varianceQty: item.variance_qty ?? null,
    warningState: item.warning_state ?? null,
    warnings: item.warnings.map(mapWarningFromApi),
  };
}

export function mapAdminProductionDetailFromApi(item: ApiProductionDetail): AdminProductionDetail {
  return {
    actualConsumption: item.actual_consumption.map((line) => ({
      consumedQty: line.consumed_qty ?? null,
      differenceQty: line.difference_qty ?? null,
      expectedQty: line.expected_qty,
      inputProductCode: line.input_product_code,
      inputProductId: line.input_product_id,
      inputProductName: line.input_product_name,
      uom: line.uom,
    })),
    availableActions: {
      canCancel: item.available_actions.can_cancel,
      canComplete: item.available_actions.can_complete,
      canEdit: item.available_actions.can_edit,
      canStart: item.available_actions.can_start,
      canViewMovements: item.available_actions.can_view_movements,
    },
    inventoryImpact: {
      integrationAvailable: item.inventory_impact.integration_available,
      movements: item.inventory_impact.movements.map((movement) => ({
        balanceAfter: movement.balance_after ?? null,
        branchId: movement.branch_id,
        direction: movement.direction,
        id: movement.id,
        locationCode: movement.location_code,
        movementType: movement.movement_type,
        productId: movement.product_id,
        quantity: movement.quantity,
        sourceDocumentId: movement.source_document_id ?? null,
        sourceDocumentType: movement.source_document_type ?? null,
        unitOfMeasure: movement.unit_of_measure,
      })),
      notes: item.inventory_impact.notes ?? null,
    },
    outputYield: {
      actualOutputQty: item.output_yield.actual_output_qty ?? null,
      plannedOutputQty: item.output_yield.planned_output_qty,
      uom: item.output_yield.uom,
      variancePercent: item.output_yield.variance_percent ?? null,
      varianceQty: item.output_yield.variance_qty ?? null,
      varianceReason: item.output_yield.variance_reason ?? null,
    },
    overview: {
      actualOutputQty: item.overview.actual_output_qty ?? null,
      branchId: item.overview.branch_id,
      branchName: item.overview.branch_name,
      cancelledAt: item.overview.cancelled_at ?? null,
      completedAt: item.overview.completed_at ?? null,
      completedByUserId: item.overview.completed_by_user_id ?? null,
      completedByUserName: item.overview.completed_by_user_name ?? null,
      createdAt: item.overview.created_at,
      createdByUserId: item.overview.created_by_user_id,
      createdByUserName: item.overview.created_by_user_name,
      folio: item.overview.folio,
      id: item.overview.id,
      notes: item.overview.notes ?? null,
      plannedAt: item.overview.planned_at ?? null,
      plannedOutputQty: item.overview.planned_output_qty,
      startedAt: item.overview.started_at ?? null,
      startedByUserId: item.overview.started_by_user_id ?? null,
      startedByUserName: item.overview.started_by_user_name ?? null,
      status: item.overview.status,
      variancePercent: item.overview.variance_percent ?? null,
      varianceQty: item.overview.variance_qty ?? null,
      varianceReason: item.overview.variance_reason ?? null,
      warningState: item.overview.warning_state ?? null,
    },
    plannedInputs: item.planned_inputs.map((line) => ({
      availableQty: line.available_qty ?? null,
      inputProductCode: line.input_product_code,
      inputProductId: line.input_product_id,
      inputProductName: line.input_product_name,
      requiredQty: line.required_qty,
      shortageQty: line.shortage_qty ?? null,
      standardCost: line.standard_cost ?? null,
      status: line.status,
      uom: line.uom,
    })),
    productRecipe: {
      productCode: item.product_recipe.product_code,
      productId: item.product_recipe.product_id,
      productIsActive: item.product_recipe.product_is_active,
      productKind: item.product_recipe.product_kind,
      productName: item.product_recipe.product_name,
      productUnitOfMeasure: item.product_recipe.product_unit_of_measure,
      recipeId: item.product_recipe.recipe_id,
      recipeIsActive: item.product_recipe.recipe_is_active,
      recipeName: item.product_recipe.recipe_name,
      recipeYieldQty: item.product_recipe.recipe_yield_qty,
      recipeYieldUom: item.product_recipe.recipe_yield_uom,
    },
    relatedDocuments: item.related_documents.map((document) => ({
      documentId: document.document_id,
      documentType: document.document_type,
      folio: document.folio,
      status: document.status,
    })),
    warnings: item.warnings.map(mapWarningFromApi),
    wasteScrap: {
      integrationAvailable: item.waste_scrap.integration_available,
      notes: item.waste_scrap.notes,
      records: item.waste_scrap.records ?? [],
    },
  };
}

function mapProductionListFromApi(response: ApiProductionListResponse): AdminProductionListResponse {
  return {
    backendContract: mapBackendContract(response.backend_contract),
    filterOptions: {
      branches: mapFilterOptions(response.filter_options.branches),
      operators: mapFilterOptions(response.filter_options.operators),
      products: mapFilterOptions(response.filter_options.products),
      recipes: mapFilterOptions(response.filter_options.recipes),
      statuses: mapFilterOptions(response.filter_options.statuses),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminProductionListItemFromApi),
    metrics: {
      completedBatches: mapMetric(response.metrics.completed_batches),
      inProgressBatches: mapMetric(response.metrics.in_progress_batches),
      pendingBatches: mapMetric(response.metrics.pending_batches),
      producedUnits: mapMetric(response.metrics.produced_units),
      totalBatches: mapMetric(response.metrics.total_batches),
      withShortages: mapMetric(response.metrics.with_shortages),
      withVariance: mapMetric(response.metrics.with_variance),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function toCreateApiPayload(payload: AdminProductionCreatePayload): ApiProductionCreatePayload {
  return {
    branch_id: payload.branchId,
    notes: payload.notes ?? null,
    planned_at: payload.plannedAt ?? null,
    planned_output_qty: payload.plannedOutputQty,
    product_id: payload.productId,
    recipe_id: payload.recipeId ?? null,
  };
}

function toUpdateApiPayload(payload: AdminProductionUpdatePayload): ApiProductionUpdatePayload {
  return {
    notes: payload.notes ?? null,
    planned_at: payload.plannedAt ?? null,
    planned_output_qty: payload.plannedOutputQty ?? null,
    product_id: payload.productId ?? null,
    recipe_id: payload.recipeId ?? null,
  };
}

function toCompleteApiPayload(payload: AdminProductionCompletePayload): ApiProductionCompletePayload {
  return {
    actual_output_qty: payload.actualOutputQty,
    notes: payload.notes ?? null,
    variance_reason: payload.varianceReason ?? null,
  };
}

export function buildAdminProductionListPath(filters: AdminProductionListFilters): string {
  const params = new URLSearchParams();

  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "branch_id", filters.branchId);
  appendOptionalParam(params, "date_from", filters.dateFrom);
  appendOptionalParam(params, "date_to", filters.dateTo);
  appendOptionalParam(params, "operator_user_id", filters.operatorUserId);
  appendOptionalParam(params, "product_id", filters.productId);
  appendOptionalParam(params, "recipe_id", filters.recipeId);
  appendOptionalParam(params, "search", filters.search?.trim());
  appendOptionalParam(params, "status", filters.status);
  appendOptionalParam(params, "variance_state", filters.varianceState);
  appendOptionalParam(params, "warning_state", filters.warningState);

  return `/v1/admin/production?${params.toString()}`;
}

export function fetchAdminProduction(
  accessToken: string,
  filters: AdminProductionListFilters,
): Promise<AdminProductionListResponse> {
  return requestJson<ApiProductionListResponse>({
    accessToken,
    path: buildAdminProductionListPath(filters),
  }).then(mapProductionListFromApi);
}

export function fetchAdminProductionDetail(accessToken: string, productionId: string): Promise<AdminProductionDetail> {
  return requestJson<ApiProductionDetail>({
    accessToken,
    path: `/v1/admin/production/${productionId}`,
  }).then(mapAdminProductionDetailFromApi);
}

export function createAdminProduction(
  accessToken: string,
  payload: AdminProductionCreatePayload,
): Promise<AdminProductionDetail> {
  return requestJson<ApiProductionDetail>({
    accessToken,
    body: toCreateApiPayload(payload),
    method: "POST",
    path: "/v1/admin/production",
  }).then(mapAdminProductionDetailFromApi);
}

export function updateAdminProduction(
  accessToken: string,
  productionId: string,
  payload: AdminProductionUpdatePayload,
): Promise<AdminProductionDetail> {
  return requestJson<ApiProductionDetail>({
    accessToken,
    body: toUpdateApiPayload(payload),
    method: "PATCH",
    path: `/v1/admin/production/${productionId}`,
  }).then(mapAdminProductionDetailFromApi);
}

export function startAdminProduction(
  accessToken: string,
  productionId: string,
  notes?: string | null,
): Promise<AdminProductionDetail> {
  return requestJson<ApiProductionDetail>({
    accessToken,
    body: { notes: notes ?? null },
    method: "POST",
    path: `/v1/admin/production/${productionId}/start`,
  }).then(mapAdminProductionDetailFromApi);
}

export function completeAdminProduction(
  accessToken: string,
  productionId: string,
  payload: AdminProductionCompletePayload,
): Promise<AdminProductionDetail> {
  return requestJson<ApiProductionDetail>({
    accessToken,
    body: toCompleteApiPayload(payload),
    method: "POST",
    path: `/v1/admin/production/${productionId}/complete`,
  }).then(mapAdminProductionDetailFromApi);
}

export function cancelAdminProduction(
  accessToken: string,
  productionId: string,
  reason?: string | null,
): Promise<AdminProductionDetail> {
  return requestJson<ApiProductionDetail>({
    accessToken,
    body: { reason: reason ?? null },
    method: "POST",
    path: `/v1/admin/production/${productionId}/cancel`,
  }).then(mapAdminProductionDetailFromApi);
}
