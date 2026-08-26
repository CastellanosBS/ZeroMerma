import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminWasteBackendContract,
  AdminWasteCreatePayload,
  AdminWasteDetail,
  AdminWasteFilterOption,
  AdminWasteListFilters,
  AdminWasteListItem,
  AdminWasteListResponse,
  AdminWasteReason,
  AdminWasteWarning,
} from "./types";

export const adminWasteBackendContract: AdminWasteBackendContract = {
  createEndpoint: "POST /v1/admin/waste",
  detailEndpoint: "GET /v1/admin/waste/{waste_id}",
  inventoryMovementContract: "Confirmed waste creates WASTE_RECORD inventory movement.",
  listEndpoint: "GET /v1/admin/waste",
  reasonsEndpoint: "GET /v1/admin/waste/reasons",
};

type ApiWasteBackendContract = components["schemas"]["AdminWasteBackendContractView"];
type ApiWasteCreatePayload = components["schemas"]["AdminWasteCreateRequest"];
type ApiWasteDetail = components["schemas"]["AdminWasteDetailView"];
type ApiWasteFilterOption = components["schemas"]["AdminWasteFilterOptionView"];
type ApiWasteListItem = components["schemas"]["AdminWasteListItemView"];
type ApiWasteListResponse = components["schemas"]["AdminWasteListResponse"];
type ApiWasteReason = components["schemas"]["AdminWasteReasonView"];
type ApiWasteWarning = components["schemas"]["AdminWasteWarningView"];

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

function mapFilterOptions(options: ApiWasteFilterOption[]): AdminWasteFilterOption[] {
  return options.map((option) => ({ id: String(option.id), label: option.label }));
}

function mapReason(reason: ApiWasteReason): AdminWasteReason {
  return {
    code: reason.code,
    displayOrder: reason.display_order,
    highImpactDefault: reason.high_impact_default,
    label: reason.label,
    requiresEvidence: reason.requires_evidence,
    requiresNote: reason.requires_note,
  };
}

function mapWarning(warning: ApiWasteWarning): AdminWasteWarning {
  return {
    code: warning.code,
    message: warning.message,
    severity: warning.severity,
  };
}

function mapBackendContract(contract?: ApiWasteBackendContract): AdminWasteBackendContract {
  if (!contract) {
    return adminWasteBackendContract;
  }
  return {
    createEndpoint: contract.create_endpoint,
    detailEndpoint: contract.detail_endpoint,
    inventoryMovementContract: contract.inventory_movement_contract,
    listEndpoint: contract.list_endpoint,
    reasonsEndpoint: contract.reasons_endpoint,
  };
}

export function mapAdminWasteListItemFromApi(item: ApiWasteListItem): AdminWasteListItem {
  return {
    branchId: item.branch_id,
    branchName: item.branch_name,
    createdAt: item.created_at,
    estimatedValue: item.estimated_value ?? null,
    folio: item.folio,
    hasEvidence: item.has_evidence,
    id: item.id,
    impactLevel: item.impact_level,
    lineCount: item.line_count,
    locationCode: item.location_code,
    locationName: item.location_name,
    operatorName: item.operator_name,
    productCode: item.product_code,
    productId: item.product_id,
    productKind: item.product_kind,
    productName: item.product_name,
    quantity: item.quantity,
    reasonCode: item.reason_code,
    reasonLabel: item.reason_label,
    status: item.status,
    uom: item.uom,
    warningState: item.warning_state ?? null,
    warnings: item.warnings.map(mapWarning),
  };
}

export function mapAdminWasteDetailFromApi(item: ApiWasteDetail): AdminWasteDetail {
  return {
    availableActions: {
      canCreateCorrection: item.available_actions.can_create_correction,
      canEdit: item.available_actions.can_edit,
      canOpenInventoryMovement: item.available_actions.can_open_inventory_movement,
      canPrint: item.available_actions.can_print,
    },
    evidence: {
      attachmentSupported: item.evidence.attachment_supported,
      evidenceItems: item.evidence.evidence_items ?? [],
      notes: item.evidence.notes ?? null,
    },
    inventoryImpact: {
      integrationAvailable: item.inventory_impact.integration_available,
      movements: item.inventory_impact.movements.map((movement) => ({
        balanceAfter: movement.balance_after ?? null,
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
    lines: item.lines.map((line) => ({
      estimatedValue: line.estimated_value ?? null,
      lineNumber: line.line_number,
      productCode: line.product_code,
      productId: line.product_id,
      productKind: line.product_kind,
      productName: line.product_name,
      quantity: line.quantity,
      uom: line.uom,
    })),
    overview: {
      branchId: item.overview.branch_id,
      branchName: item.overview.branch_name,
      confirmedAt: item.overview.confirmed_at ?? null,
      createdAt: item.overview.created_at,
      folio: item.overview.folio,
      hasEvidence: item.overview.has_evidence,
      id: item.overview.id,
      impactLevel: item.overview.impact_level,
      locationCode: item.overview.location_code,
      locationName: item.overview.location_name,
      notes: item.overview.notes ?? null,
      operatorId: item.overview.operator_id,
      operatorName: item.overview.operator_name,
      quantity: item.overview.quantity,
      reasonCode: item.overview.reason_code,
      reasonLabel: item.overview.reason_label,
      status: item.overview.status,
      uom: item.overview.uom,
      warningState: item.overview.warning_state ?? null,
      workstationCode: item.overview.workstation_code ?? null,
      workstationName: item.overview.workstation_name ?? null,
    },
    productInventoryContext: {
      branchId: item.product_inventory_context.branch_id,
      branchName: item.product_inventory_context.branch_name,
      classId: item.product_inventory_context.class_id,
      className: item.product_inventory_context.class_name,
      currentStock: item.product_inventory_context.current_stock ?? null,
      productCode: item.product_inventory_context.product_code,
      productId: item.product_inventory_context.product_id,
      productIsActive: item.product_inventory_context.product_is_active,
      productKind: item.product_inventory_context.product_kind,
      productName: item.product_inventory_context.product_name,
      stockAfter: item.product_inventory_context.stock_after ?? null,
      stockBefore: item.product_inventory_context.stock_before ?? null,
      uom: item.product_inventory_context.uom,
    },
    reasonClassification: {
      category: item.reason_classification.category,
      description: item.reason_classification.description ?? null,
      label: item.reason_classification.label,
      requiresEvidence: item.reason_classification.requires_evidence,
      requiresNote: item.reason_classification.requires_note,
    },
    relatedDocuments: item.related_documents.map((document) => ({
      documentId: document.document_id,
      documentType: document.document_type,
      folio: document.folio,
      status: document.status,
    })),
    warnings: item.warnings.map(mapWarning),
  };
}

function mapWasteListFromApi(response: ApiWasteListResponse): AdminWasteListResponse {
  return {
    backendContract: mapBackendContract(response.backend_contract),
    filterOptions: {
      branches: mapFilterOptions(response.filter_options.branches),
      classes: mapFilterOptions(response.filter_options.classes),
      evidenceStates: mapFilterOptions(response.filter_options.evidence_states),
      impactLevels: mapFilterOptions(response.filter_options.impact_levels),
      locations: mapFilterOptions(response.filter_options.locations),
      operators: mapFilterOptions(response.filter_options.operators),
      productKinds: mapFilterOptions(response.filter_options.product_kinds),
      products: mapFilterOptions(response.filter_options.products),
      reasons: response.filter_options.reasons.map(mapReason),
      statuses: mapFilterOptions(response.filter_options.statuses),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminWasteListItemFromApi),
    metrics: {
      contaminatedOrDamaged: mapMetric(response.metrics.contaminated_or_damaged),
      evidenceRecords: mapMetric(response.metrics.evidence_records),
      estimatedValue: mapMetric(response.metrics.estimated_value),
      expiredRecords: mapMetric(response.metrics.expired_records),
      highImpactRecords: mapMetric(response.metrics.high_impact_records),
      totalQuantity: mapMetric(response.metrics.total_quantity),
      totalRecords: mapMetric(response.metrics.total_records),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function toCreateApiPayload(payload: AdminWasteCreatePayload): ApiWasteCreatePayload {
  return {
    branch_id: payload.branchId,
    location_code: payload.locationCode,
    notes: payload.notes ?? null,
    product_id: payload.productId,
    quantity: payload.quantity,
    reason_code: payload.reasonCode,
  };
}

export function buildAdminWasteListPath(filters: AdminWasteListFilters): string {
  const params = new URLSearchParams();

  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "branch_id", filters.branchId);
  appendOptionalParam(params, "class_id", filters.classId);
  appendOptionalParam(params, "date_from", filters.dateFrom);
  appendOptionalParam(params, "date_to", filters.dateTo);
  appendOptionalParam(params, "evidence_state", filters.evidenceState);
  appendOptionalParam(params, "impact_level", filters.impactLevel);
  appendOptionalParam(params, "location_code", filters.locationCode);
  appendOptionalParam(params, "operator_user_id", filters.operatorUserId);
  appendOptionalParam(params, "product_id", filters.productId);
  appendOptionalParam(params, "product_kind", filters.productKind);
  appendOptionalParam(params, "reason_code", filters.reasonCode);
  appendOptionalParam(params, "search", filters.search?.trim());
  appendOptionalParam(params, "status", filters.status);
  appendOptionalParam(params, "warning_state", filters.warningState);

  return `/v1/admin/waste?${params.toString()}`;
}

export function fetchAdminWaste(accessToken: string, filters: AdminWasteListFilters): Promise<AdminWasteListResponse> {
  return requestJson<ApiWasteListResponse>({
    accessToken,
    path: buildAdminWasteListPath(filters),
  }).then(mapWasteListFromApi);
}

export function fetchAdminWasteDetail(accessToken: string, wasteId: string): Promise<AdminWasteDetail> {
  return requestJson<ApiWasteDetail>({
    accessToken,
    path: `/v1/admin/waste/${wasteId}`,
  }).then(mapAdminWasteDetailFromApi);
}

export function createAdminWaste(accessToken: string, payload: AdminWasteCreatePayload): Promise<AdminWasteDetail> {
  return requestJson<ApiWasteDetail>({
    accessToken,
    body: toCreateApiPayload(payload),
    method: "POST",
    path: "/v1/admin/waste",
  }).then(mapAdminWasteDetailFromApi);
}
