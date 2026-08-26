import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminPendingDiscrepancyItem,
  AdminReconciliationBackendContract,
  AdminReconciliationCreatePayload,
  AdminReconciliationDetail,
  AdminReconciliationFilterOption,
  AdminReconciliationListFilters,
  AdminReconciliationListItem,
  AdminReconciliationListResponse,
  AdminReconciliationResolvePayload,
} from "./types";

type ApiFilterOption = components["schemas"]["AdminReconciliationFilterOptionView"];
type ApiListItem = components["schemas"]["AdminReconciliationListItemView"];
type ApiPendingItem = components["schemas"]["AdminPendingDiscrepancyItemView"];
type ApiListResponse = components["schemas"]["AdminReconciliationListResponse"];
type ApiDetail = components["schemas"]["AdminReconciliationDetailView"];
type ApiCreateRequest = components["schemas"]["AdminReconciliationCreateRequest"];
type ApiResolveRequest = components["schemas"]["AdminReconciliationResolveRequest"];

export const adminReconciliationBackendContract: AdminReconciliationBackendContract = {
  createEndpoint: "POST /v1/admin/reconciliation",
  detailEndpoint: "GET /v1/admin/reconciliation/{reconciliation_id}",
  evidenceEndpoint: null,
  exportEndpoint: null,
  listEndpoint: "GET /v1/admin/reconciliation",
  pendingEndpoint: "GET /v1/admin/reconciliation/pending",
  resolveEndpoint: "POST /v1/admin/reconciliation/{reconciliation_id}/resolve",
};

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

function toDateTimeParam(
  value: string | null | undefined,
  boundary: "start" | "end",
): string | null {
  if (!value) {
    return null;
  }
  const suffix = boundary === "start" ? "T00:00:00.000Z" : "T23:59:59.999Z";
  return `${value}${suffix}`;
}

function mapOption(option: ApiFilterOption): AdminReconciliationFilterOption {
  return { id: option.id, label: option.label };
}

function mapBackendContract(
  contract: ApiListResponse["backend_contract"] | ApiDetail["backend_contract"],
): AdminReconciliationBackendContract {
  return {
    createEndpoint: contract.create_endpoint,
    detailEndpoint: contract.detail_endpoint,
    evidenceEndpoint: contract.evidence_endpoint ?? null,
    exportEndpoint: contract.export_endpoint ?? null,
    listEndpoint: contract.list_endpoint,
    pendingEndpoint: contract.pending_endpoint,
    resolveEndpoint: contract.resolve_endpoint,
  };
}

export function mapAdminReconciliationItemFromApi(item: ApiListItem): AdminReconciliationListItem {
  return {
    actualAmount: String(item.actual_amount),
    branchId: item.branch_id,
    branchName: item.branch_name,
    differenceAmount: String(item.difference_amount),
    differenceDirection: item.difference_direction,
    expectedAmount: String(item.expected_amount),
    folio: item.folio,
    hasEvidence: item.has_evidence,
    id: item.id,
    occurredAt: item.occurred_at,
    operatorId: item.operator_id ?? null,
    operatorName: item.operator_name,
    paymentMethod: item.payment_method,
    reasonCode: item.reason_code ?? null,
    sourceDocumentId: item.source_document_id,
    sourceReference: item.source_reference,
    sourceType: item.source_type,
    status: item.status,
    updatedAt: item.updated_at,
    warningState: item.warning_state,
    workstationId: item.workstation_id,
    workstationName: item.workstation_name,
  };
}

export function mapAdminPendingDiscrepancyFromApi(
  item: ApiPendingItem,
): AdminPendingDiscrepancyItem {
  return {
    actualAmount: String(item.actual_amount),
    branchId: item.branch_id,
    branchName: item.branch_name,
    differenceAmount: String(item.difference_amount),
    differenceDirection: item.difference_direction,
    expectedAmount: String(item.expected_amount),
    occurredAt: item.occurred_at,
    operatorId: item.operator_id ?? null,
    operatorName: item.operator_name,
    paymentMethod: item.payment_method,
    sourceDocumentId: item.source_document_id,
    sourceReference: item.source_reference,
    sourceType: item.source_type,
    suggestedWarningState: item.suggested_warning_state,
    workstationId: item.workstation_id,
    workstationName: item.workstation_name,
  };
}

function mapDetailFromApi(response: ApiDetail): AdminReconciliationDetail {
  return {
    availableActions: {
      canAttachEvidence: response.available_actions.can_attach_evidence,
      canCopyFolio: response.available_actions.can_copy_folio,
      canExportReport: response.available_actions.can_export_report,
      canOpenSource: response.available_actions.can_open_source,
      canResolve: response.available_actions.can_resolve,
      canSaveNotes: response.available_actions.can_save_notes,
      canVoid: response.available_actions.can_void,
      note: response.available_actions.note ?? null,
    },
    backendContract: mapBackendContract(response.backend_contract),
    differenceBreakdown: {
      actualAmount: String(response.difference_breakdown.actual_amount),
      differenceAmount: String(response.difference_breakdown.difference_amount),
      direction: response.difference_breakdown.direction,
      expectedAmount: String(response.difference_breakdown.expected_amount),
      paymentMethod: response.difference_breakdown.payment_method,
      toleranceNote: response.difference_breakdown.tolerance_note ?? null,
      toleranceStatus: response.difference_breakdown.tolerance_status,
    },
    evidence: {
      emptyState: response.evidence.empty_state,
      evidenceNote: response.evidence.evidence_note ?? null,
      files: response.evidence.files,
      hasEvidence: response.evidence.has_evidence,
      isSupported: response.evidence.is_supported,
    },
    explanationReason: {
      notes: response.explanation_reason.notes ?? null,
      reasonCode: response.explanation_reason.reason_code ?? null,
      reasonLabel: response.explanation_reason.reason_label ?? null,
      responsibleUserId: response.explanation_reason.responsible_user_id ?? null,
      responsibleUserName: response.explanation_reason.responsible_user_name ?? null,
      timestamp: response.explanation_reason.timestamp ?? null,
    },
    overview: {
      actualAmount: String(response.overview.actual_amount),
      branchId: response.overview.branch_id,
      branchName: response.overview.branch_name,
      createdAt: response.overview.created_at,
      differenceAmount: String(response.overview.difference_amount),
      differenceDirection: response.overview.difference_direction,
      expectedAmount: String(response.overview.expected_amount),
      folio: response.overview.folio,
      hasEvidence: response.evidence.has_evidence,
      id: response.overview.id,
      occurredAt: response.overview.created_at,
      operatorId: response.overview.operator_id ?? null,
      operatorName: response.overview.operator_name,
      paymentMethod: response.overview.payment_method,
      reasonCode: response.explanation_reason.reason_code ?? null,
      resolvedAt: response.overview.resolved_at ?? null,
      sourceDocumentId: response.overview.source_document_id,
      sourceReference: response.overview.source_reference,
      sourceType: response.overview.source_type,
      status: response.overview.status,
      updatedAt: response.overview.updated_at,
      warningState: response.overview.warning_state,
      workstationId: response.overview.workstation_id,
      workstationName: response.overview.workstation_name,
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
    resolution: {
      canResolve: response.resolution.can_resolve,
      evidenceSummary: response.resolution.evidence_summary ?? null,
      finalNotes: response.resolution.final_notes ?? null,
      requiredFields: response.resolution.required_fields,
      resolutionReason: response.resolution.resolution_reason ?? null,
      resolvedAt: response.resolution.resolved_at ?? null,
      resolvedByUserId: response.resolution.resolved_by_user_id ?? null,
      resolvedByUserName: response.resolution.resolved_by_user_name ?? null,
      status: response.resolution.status,
    },
    sourceDocumentContext: {
      closedAt: response.source_document_context.closed_at ?? null,
      countedCashAmount:
        response.source_document_context.counted_cash_amount == null
          ? null
          : String(response.source_document_context.counted_cash_amount),
      differenceAmount:
        response.source_document_context.difference_amount == null
          ? null
          : String(response.source_document_context.difference_amount),
      expectedCashAmount:
        response.source_document_context.expected_cash_amount == null
          ? null
          : String(response.source_document_context.expected_cash_amount),
      externalReportedAmount:
        response.source_document_context.external_reported_amount == null
          ? null
          : String(response.source_document_context.external_reported_amount),
      note: response.source_document_context.note ?? null,
      openedAt: response.source_document_context.opened_at ?? null,
      operationalPaymentCategory:
        response.source_document_context.operational_payment_category ?? null,
      paymentMethod: response.source_document_context.payment_method ?? null,
      refundOriginalTicket: response.source_document_context.refund_original_ticket ?? null,
      sourceReference: response.source_document_context.source_reference,
      sourceRouteHint: response.source_document_context.source_route_hint ?? null,
      sourceType: response.source_document_context.source_type,
      terminalReference: response.source_document_context.terminal_reference ?? null,
    },
  };
}

function mapListFromApi(response: ApiListResponse): AdminReconciliationListResponse {
  return {
    backendContract: mapBackendContract(response.backend_contract),
    filterOptions: {
      branches: response.filter_options.branches.map(mapOption),
      cashiers: response.filter_options.cashiers.map(mapOption),
      discrepancyTypes: response.filter_options.discrepancy_types.map(mapOption),
      evidenceStates: response.filter_options.evidence_states.map(mapOption),
      paymentMethods: response.filter_options.payment_methods.map(mapOption),
      reasonCodes: response.filter_options.reason_codes.map(mapOption),
      sourceTypes: response.filter_options.source_types.map(mapOption),
      statuses: response.filter_options.statuses.map(mapOption),
      workstations: response.filter_options.workstations.map(mapOption),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminReconciliationItemFromApi),
    metrics: {
      cardTerminalPendingCount: String(response.metrics.card_terminal_pending_count),
      cashPendingCount: String(response.metrics.cash_pending_count),
      netDifferenceAmount: String(response.metrics.net_difference_amount),
      overageAmount: String(response.metrics.overage_amount),
      pendingCount: String(response.metrics.pending_count),
      reconciledCount: String(response.metrics.reconciled_count),
      shortageAmount: String(response.metrics.shortage_amount),
      withEvidenceCount: String(response.metrics.with_evidence_count),
    },
    page: response.page,
    pageSize: response.page_size,
    pendingDiscrepancies: response.pending_discrepancies.map(mapAdminPendingDiscrepancyFromApi),
    total: response.total,
  };
}

export function buildAdminReconciliationListPath(filters: AdminReconciliationListFilters): string {
  const params = new URLSearchParams();

  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "amount_max", filters.amountMax);
  appendOptionalParam(params, "amount_min", filters.amountMin);
  appendOptionalParam(params, "branch_id", filters.branchId);
  appendOptionalParam(params, "cashier_id", filters.cashierId);
  appendOptionalParam(params, "date_from", toDateTimeParam(filters.dateFrom, "start"));
  appendOptionalParam(params, "date_to", toDateTimeParam(filters.dateTo, "end"));
  appendOptionalParam(params, "discrepancy_type", filters.discrepancyType);
  appendOptionalParam(params, "evidence_state", filters.evidenceState);
  appendOptionalParam(params, "payment_method", filters.paymentMethod);
  appendOptionalParam(params, "search", filters.search.trim());
  appendOptionalParam(params, "source_type", filters.sourceType);
  appendOptionalParam(params, "status", filters.status);
  appendOptionalParam(params, "workstation_id", filters.workstationId);

  return `/v1/admin/reconciliation?${params.toString()}`;
}

export function fetchAdminReconciliations(
  accessToken: string,
  filters: AdminReconciliationListFilters,
): Promise<AdminReconciliationListResponse> {
  return requestJson<ApiListResponse>({
    accessToken,
    path: buildAdminReconciliationListPath(filters),
  }).then(mapListFromApi);
}

export function fetchAdminReconciliationDetail(
  accessToken: string,
  reconciliationId: string,
): Promise<AdminReconciliationDetail> {
  return requestJson<ApiDetail>({
    accessToken,
    path: `/v1/admin/reconciliation/${reconciliationId}`,
  }).then(mapDetailFromApi);
}

export function createAdminReconciliation(
  accessToken: string,
  payload: AdminReconciliationCreatePayload,
): Promise<AdminReconciliationDetail> {
  const body: ApiCreateRequest = {
    evidence_note: payload.evidenceNote,
    final_status: payload.finalStatus,
    notes: payload.notes,
    reason_code: payload.reasonCode,
    source_document_id: payload.sourceDocumentId,
    source_type: payload.sourceType,
  };

  return requestJson<ApiDetail>({
    accessToken,
    body,
    method: "POST",
    path: "/v1/admin/reconciliation",
  }).then(mapDetailFromApi);
}

export function resolveAdminReconciliation(
  accessToken: string,
  reconciliationId: string,
  payload: AdminReconciliationResolvePayload,
): Promise<AdminReconciliationDetail> {
  const body: ApiResolveRequest = {
    evidence_note: payload.evidenceNote,
    notes: payload.notes,
    reason_code: payload.reasonCode,
  };

  return requestJson<ApiDetail>({
    accessToken,
    body,
    method: "POST",
    path: `/v1/admin/reconciliation/${reconciliationId}/resolve`,
  }).then(mapDetailFromApi);
}
