import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminCorrectionDetail,
  AdminCorrectionFilterOptions,
  AdminCorrectionListFilters,
  AdminCorrectionListItem,
  AdminCorrectionsBackendContract,
  AdminCorrectionsListResponse,
  AdminReturnDetail,
  AdminReturnFilterOptions,
  AdminReturnListFilters,
  AdminReturnListItem,
  AdminReturnsBackendContract,
  AdminReturnsListResponse,
} from "./types";

type ApiReturnsListResponse = components["schemas"]["AdminReturnsListResponse"];
type ApiReturnListItem = components["schemas"]["AdminReturnListItemView"];
type ApiReturnDetail = components["schemas"]["AdminReturnDetailView"];
type ApiCorrectionsListResponse = components["schemas"]["AdminCorrectionsListResponse"];
type ApiCorrectionListItem = components["schemas"]["AdminCorrectionListItemView"];
type ApiCorrectionDetail = components["schemas"]["AdminCorrectionDetailView"];
type ApiFilterOption = components["schemas"]["AdminReturnCorrectionFilterOptionView"];

export const adminReturnsBackendContract: AdminReturnsBackendContract = {
  createEndpoint: null,
  detailEndpoint: "GET /v1/admin/returns-corrections/returns/{return_id}",
  listEndpoint: "GET /v1/admin/returns-corrections/returns",
  reprintEndpoint: null,
};

export const adminCorrectionsBackendContract: AdminCorrectionsBackendContract = {
  createEndpoint: null,
  detailEndpoint: "GET /v1/admin/returns-corrections/corrections/{correction_id}",
  listEndpoint: "GET /v1/admin/returns-corrections/corrections",
  printEndpoint: null,
};

function appendOptionalParam(params: URLSearchParams, key: string, value: string | null | undefined) {
  if (!value || value === "all") {
    return;
  }
  params.set(key, value);
}

function mapOption(option: ApiFilterOption) {
  return { id: option.id, label: option.label };
}

function mapReturnsContract(
  contract: ApiReturnsListResponse["backend_contract"] | ApiReturnDetail["backend_contract"],
): AdminReturnsBackendContract {
  return {
    createEndpoint: contract.create_endpoint ?? null,
    detailEndpoint: contract.detail_endpoint,
    listEndpoint: contract.list_endpoint,
    reprintEndpoint: contract.reprint_endpoint ?? null,
  };
}

function mapCorrectionsContract(
  contract: ApiCorrectionsListResponse["backend_contract"] | ApiCorrectionDetail["backend_contract"],
): AdminCorrectionsBackendContract {
  return {
    createEndpoint: contract.create_endpoint ?? null,
    detailEndpoint: contract.detail_endpoint,
    listEndpoint: contract.list_endpoint,
    printEndpoint: contract.print_endpoint ?? null,
  };
}

function mapReturnFilterOptions(options: ApiReturnsListResponse["filter_options"]): AdminReturnFilterOptions {
  return {
    branches: options.branches.map(mapOption),
    operators: options.operators.map(mapOption),
    refundMethods: options.refund_methods.map(mapOption),
    statuses: options.statuses.map(mapOption),
  };
}

function mapCorrectionFilterOptions(
  options: ApiCorrectionsListResponse["filter_options"],
): AdminCorrectionFilterOptions {
  return {
    branches: options.branches.map(mapOption),
    correctionTypes: options.correction_types.map(mapOption),
    operators: options.operators.map(mapOption),
    reasons: options.reasons.map(mapOption),
    statuses: options.statuses.map(mapOption),
    targetDocumentTypes: options.target_document_types.map(mapOption),
  };
}

export function mapAdminReturnFromApi(item: ApiReturnListItem): AdminReturnListItem {
  return {
    branchId: item.branch_id,
    branchName: item.branch_name,
    createdAt: item.created_at,
    folio: item.folio,
    id: item.id,
    operatorId: item.operator_id,
    operatorName: item.operator_name,
    originalSaleId: item.original_sale_id,
    originalTicketFolio: item.original_ticket_folio,
    refundedAmount: String(item.refunded_amount),
    refundMethod: item.refund_method,
    returnedLineCount: item.returned_line_count,
    status: item.status,
    warningState: item.warning_state ?? null,
    workstationCode: item.workstation_code,
    workstationId: item.workstation_id,
    workstationName: item.workstation_name,
  };
}

export function mapAdminCorrectionFromApi(item: ApiCorrectionListItem): AdminCorrectionListItem {
  return {
    branchId: item.branch_id,
    branchName: item.branch_name,
    correctionType: item.correction_type,
    createdAt: item.created_at,
    folio: item.folio,
    id: item.id,
    lineCount: item.line_count,
    netEffect: item.net_effect,
    netEffectQuantity: String(item.net_effect_quantity),
    operatorId: item.operator_id,
    operatorName: item.operator_name,
    originalDocumentFolio: item.original_document_folio,
    originalDocumentId: item.original_document_id,
    originalDocumentType: item.original_document_type,
    reasonCode: item.reason_code,
    reasonName: item.reason_name,
    status: item.status,
    totalUnitsAffected: String(item.total_units_affected),
    warningState: item.warning_state ?? null,
    workstationCode: item.workstation_code,
    workstationId: item.workstation_id,
    workstationName: item.workstation_name,
  };
}

function mapReturnsListFromApi(response: ApiReturnsListResponse): AdminReturnsListResponse {
  return {
    backendContract: mapReturnsContract(response.backend_contract),
    filterOptions: mapReturnFilterOptions(response.filter_options),
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminReturnFromApi),
    metrics: {
      cashRefundedAmount: String(response.metrics.cash_refunded_amount),
      pendingReviewCount: response.metrics.pending_review_count,
      refundedAmount: String(response.metrics.refunded_amount),
      returnedLineCount: response.metrics.returned_line_count,
      returnsCount: response.metrics.returns_count,
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function mapCorrectionsListFromApi(response: ApiCorrectionsListResponse): AdminCorrectionsListResponse {
  return {
    backendContract: mapCorrectionsContract(response.backend_contract),
    filterOptions: mapCorrectionFilterOptions(response.filter_options),
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminCorrectionFromApi),
    metrics: {
      correctionsCount: response.metrics.corrections_count,
      negativeEffectCount: response.metrics.negative_effect_count,
      pendingReviewCount: response.metrics.pending_review_count,
      positiveEffectCount: response.metrics.positive_effect_count,
      totalUnitsAffected: String(response.metrics.total_units_affected),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function mapReturnDetailFromApi(response: ApiReturnDetail): AdminReturnDetail {
  return {
    auditSummary: response.audit_summary ?? null,
    availableActions: {
      canCreateFromBackoffice: response.available_actions.can_create_from_backoffice,
      canOpenOriginalTicket: response.available_actions.can_open_original_ticket,
      canReprint: response.available_actions.can_reprint,
      creationNote: response.available_actions.creation_note,
    },
    backendContract: mapReturnsContract(response.backend_contract),
    originalTicket: {
      branchName: response.original_ticket.branch_name,
      cashSessionId: response.original_ticket.cash_session_id,
      cashierName: response.original_ticket.cashier_name,
      folio: response.original_ticket.folio,
      paymentMethodsLabel: response.original_ticket.payment_methods_label,
      saleDate: response.original_ticket.sale_date,
      saleId: response.original_ticket.sale_id,
      status: response.original_ticket.status,
      totalAmount: String(response.original_ticket.total_amount),
      workstationName: response.original_ticket.workstation_name,
    },
    overview: {
      branchId: response.overview.branch_id,
      branchName: response.overview.branch_name,
      createdAt: response.overview.created_at,
      folio: response.overview.folio,
      id: response.overview.id,
      isPartialReturn: response.overview.is_partial_return,
      notes: response.overview.notes ?? null,
      operatorId: response.overview.operator_id,
      operatorName: response.overview.operator_name,
      reasonCode: response.overview.reason_code,
      reasonName: response.overview.reason_name,
      refundMethod: response.overview.refund_method,
      status: response.overview.status,
      totalRefundAmount: String(response.overview.total_refund_amount),
      workstationCode: response.overview.workstation_code,
      workstationId: response.overview.workstation_id,
      workstationName: response.overview.workstation_name,
    },
    refundImpact: {
      cashImpactAmount: String(response.refund_impact.cash_impact_amount),
      cashSessionId: response.refund_impact.cash_session_id,
      currencyCode: response.refund_impact.currency_code,
      linkedCashMovementId: response.refund_impact.linked_cash_movement_id ?? null,
      refundAmount: String(response.refund_impact.refund_amount),
      refundMethod: response.refund_impact.refund_method,
    },
    relatedDocuments: response.related_documents.map((document) => ({
      amount: document.amount == null ? null : String(document.amount),
      documentType: document.document_type,
      folio: document.folio,
      id: document.id,
      occurredAt: document.occurred_at ?? null,
      routeHint: document.route_hint ?? null,
      status: document.status,
    })),
    returnedLines: response.returned_lines.map((line) => ({
      dispositionCode: line.disposition_code,
      id: line.id,
      lineStatus: line.line_status,
      originalQuantity: String(line.original_quantity),
      originalSaleLineId: line.original_sale_line_id,
      productClassCode: line.product_class_code,
      productClassName: line.product_class_name,
      productCode: line.product_code,
      productName: line.product_name,
      refundAmount: String(line.refund_amount),
      returnedQuantity: String(line.returned_quantity),
      unitPrice: String(line.unit_price),
    })),
  };
}

function mapCorrectionDetailFromApi(response: ApiCorrectionDetail): AdminCorrectionDetail {
  return {
    affectedLines: response.affected_lines.map((line) => ({
      correctedQuantity: line.corrected_quantity == null ? null : String(line.corrected_quantity),
      differenceQuantity: String(line.difference_quantity),
      id: line.id,
      notes: line.notes ?? null,
      originalQuantity: line.original_quantity == null ? null : String(line.original_quantity),
      productClassCode: line.product_class_code,
      productClassName: line.product_class_name,
      productCode: line.product_code,
      productName: line.product_name,
      targetLineId: line.target_line_id ?? null,
      unitOfMeasureCode: line.unit_of_measure_code,
    })),
    availableActions: {
      canCreateFromBackoffice: response.available_actions.can_create_from_backoffice,
      canOpenOriginalDocument: response.available_actions.can_open_original_document,
      canPrint: response.available_actions.can_print,
      creationNote: response.available_actions.creation_note,
    },
    backendContract: mapCorrectionsContract(response.backend_contract),
    netEffect: {
      cashEffect: response.net_effect.cash_effect,
      inventoryEffect: response.net_effect.inventory_effect,
      netEffect: response.net_effect.net_effect,
      totalAmountAffected:
        response.net_effect.total_amount_affected == null ? null : String(response.net_effect.total_amount_affected),
      totalUnitsAffected: String(response.net_effect.total_units_affected),
    },
    originalDocument: {
      branchName: response.original_document.branch_name,
      documentType: response.original_document.document_type,
      folio: response.original_document.folio,
      id: response.original_document.id,
      occurredAt: response.original_document.occurred_at ?? null,
      operatorName: response.original_document.operator_name,
      routeHint: response.original_document.route_hint ?? null,
      status: response.original_document.status,
      workstationName: response.original_document.workstation_name,
    },
    overview: {
      branchId: response.overview.branch_id,
      branchName: response.overview.branch_name,
      committedAt: response.overview.committed_at ?? null,
      correctionType: response.overview.correction_type,
      createdAt: response.overview.created_at,
      folio: response.overview.folio,
      id: response.overview.id,
      netEffect: response.overview.net_effect,
      netEffectQuantity: String(response.overview.net_effect_quantity),
      operatorId: response.overview.operator_id,
      operatorName: response.overview.operator_name,
      originalDocumentFolio: response.overview.original_document_folio,
      originalDocumentId: response.overview.original_document_id,
      originalDocumentType: response.overview.original_document_type,
      status: response.overview.status,
      totalUnitsAffected: String(response.overview.total_units_affected),
      workstationCode: response.overview.workstation_code,
      workstationId: response.overview.workstation_id,
      workstationName: response.overview.workstation_name,
    },
    reasonNotes: {
      auditSummary: response.reason_notes.audit_summary ?? null,
      notes: response.reason_notes.notes ?? null,
      reasonCode: response.reason_notes.reason_code,
      reasonName: response.reason_notes.reason_name,
    },
    relatedDocuments: response.related_documents.map((document) => ({
      documentType: document.document_type,
      folio: document.folio,
      id: document.id,
      occurredAt: document.occurred_at ?? null,
      routeHint: document.route_hint ?? null,
      status: document.status,
    })),
  };
}

export function buildAdminReturnsListPath(filters: AdminReturnListFilters): string {
  const params = new URLSearchParams();
  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "branch_id", filters.branchId);
  appendOptionalParam(params, "date_from", filters.dateFrom);
  appendOptionalParam(params, "date_to", filters.dateTo);
  appendOptionalParam(params, "max_amount", filters.maxAmount);
  appendOptionalParam(params, "min_amount", filters.minAmount);
  appendOptionalParam(params, "operator_id", filters.operatorId);
  appendOptionalParam(params, "refund_method", filters.refundMethod);
  appendOptionalParam(params, "search", filters.search?.trim());
  appendOptionalParam(params, "status", filters.status);
  return `/v1/admin/returns-corrections/returns?${params.toString()}`;
}

export function buildAdminCorrectionsListPath(filters: AdminCorrectionListFilters): string {
  const params = new URLSearchParams();
  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "branch_id", filters.branchId);
  appendOptionalParam(params, "correction_type", filters.correctionType);
  appendOptionalParam(params, "date_from", filters.dateFrom);
  appendOptionalParam(params, "date_to", filters.dateTo);
  appendOptionalParam(params, "net_effect", filters.netEffect);
  appendOptionalParam(params, "operator_id", filters.operatorId);
  appendOptionalParam(params, "reason_code", filters.reasonCode);
  appendOptionalParam(params, "search", filters.search?.trim());
  appendOptionalParam(params, "status", filters.status);
  appendOptionalParam(params, "target_document_type", filters.targetDocumentType);
  return `/v1/admin/returns-corrections/corrections?${params.toString()}`;
}

export function fetchAdminReturns(
  accessToken: string,
  filters: AdminReturnListFilters,
): Promise<AdminReturnsListResponse> {
  return requestJson<ApiReturnsListResponse>({
    accessToken,
    path: buildAdminReturnsListPath(filters),
  }).then(mapReturnsListFromApi);
}

export function fetchAdminCorrections(
  accessToken: string,
  filters: AdminCorrectionListFilters,
): Promise<AdminCorrectionsListResponse> {
  return requestJson<ApiCorrectionsListResponse>({
    accessToken,
    path: buildAdminCorrectionsListPath(filters),
  }).then(mapCorrectionsListFromApi);
}

export function fetchAdminReturnDetail(accessToken: string, returnId: string): Promise<AdminReturnDetail> {
  return requestJson<ApiReturnDetail>({
    accessToken,
    path: `/v1/admin/returns-corrections/returns/${returnId}`,
  }).then(mapReturnDetailFromApi);
}

export function fetchAdminCorrectionDetail(
  accessToken: string,
  correctionId: string,
): Promise<AdminCorrectionDetail> {
  return requestJson<ApiCorrectionDetail>({
    accessToken,
    path: `/v1/admin/returns-corrections/corrections/${correctionId}`,
  }).then(mapCorrectionDetailFromApi);
}
