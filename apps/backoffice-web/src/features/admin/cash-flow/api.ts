import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminCashFlowBackendContract,
  AdminCashFlowFilterOption,
  AdminCashFlowListFilters,
  AdminCashFlowListResponse,
  AdminCashFlowMovementDetail,
  AdminCashFlowMovementListItem,
  AdminCashFlowTrendPoint,
} from "./types";

type ApiFilterOption = components["schemas"]["AdminCashFlowFilterOptionView"];
type ApiListItem = components["schemas"]["AdminCashFlowMovementListItemView"];
type ApiListResponse = components["schemas"]["AdminCashFlowListResponse"];
type ApiDetail = components["schemas"]["AdminCashFlowMovementDetailView"];
type ApiOverview = components["schemas"]["AdminCashFlowMovementOverviewView"];
type ApiTrendPoint = components["schemas"]["AdminCashFlowTrendPointView"];

export const adminCashFlowBackendContract: AdminCashFlowBackendContract = {
  detailEndpoint: "GET /v1/admin/cash-flow/{movement_id}",
  exportEndpoint: null,
  listEndpoint: "GET /v1/admin/cash-flow",
  trendEndpoint: null,
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

function mapOption(option: ApiFilterOption): AdminCashFlowFilterOption {
  return { id: option.id, label: option.label };
}

function mapBackendContract(
  contract: ApiListResponse["backend_contract"] | ApiDetail["backend_contract"],
): AdminCashFlowBackendContract {
  return {
    detailEndpoint: contract.detail_endpoint,
    exportEndpoint: contract.export_endpoint ?? null,
    listEndpoint: contract.list_endpoint,
    trendEndpoint: contract.trend_endpoint ?? null,
  };
}

export function mapAdminCashFlowMovementFromApi(item: ApiListItem): AdminCashFlowMovementListItem {
  return {
    amount: String(item.amount),
    branchId: item.branch_id,
    branchName: item.branch_name,
    category: item.category ?? null,
    currency: item.currency,
    direction: item.direction,
    id: item.id,
    occurredAt: item.occurred_at,
    operatorId: item.operator_id ?? null,
    operatorName: item.operator_name,
    paymentMethod: item.payment_method,
    reconciliationStatus: item.reconciliation_status,
    sourceDocumentId: item.source_document_id,
    sourceReference: item.source_reference,
    sourceType: item.source_type,
    warningState: item.warning_state,
    workstationId: item.workstation_id,
    workstationName: item.workstation_name,
  };
}

function mapTrendPoint(point: ApiTrendPoint): AdminCashFlowTrendPoint {
  return {
    date: point.date,
    inflows: String(point.inflows),
    net: String(point.net),
    outflows: String(point.outflows),
  };
}

function mapAdminCashFlowOverviewFromApi(
  overview: ApiOverview,
  reconciliationStatus: string,
): AdminCashFlowMovementListItem {
  return {
    amount: String(overview.amount),
    branchId: overview.branch_id,
    branchName: overview.branch_name,
    category: overview.category ?? null,
    currency: overview.currency,
    direction: overview.direction,
    id: overview.id,
    occurredAt: overview.occurred_at,
    operatorId: overview.operator_id ?? null,
    operatorName: overview.operator_name,
    paymentMethod: overview.payment_method,
    reconciliationStatus,
    sourceDocumentId: overview.source_document_id,
    sourceReference: overview.source_reference,
    sourceType: overview.source_type,
    warningState: overview.warning_state,
    workstationId: overview.workstation_id,
    workstationName: overview.workstation_name,
  };
}

function mapListFromApi(response: ApiListResponse): AdminCashFlowListResponse {
  return {
    backendContract: mapBackendContract(response.backend_contract),
    filterOptions: {
      branches: response.filter_options.branches.map(mapOption),
      categories: response.filter_options.categories.map(mapOption),
      directions: response.filter_options.directions.map(mapOption),
      operators: response.filter_options.operators.map(mapOption),
      paymentMethods: response.filter_options.payment_methods.map(mapOption),
      reconciliationStates: response.filter_options.reconciliation_states.map(mapOption),
      sourceTypes: response.filter_options.source_types.map(mapOption),
      workstations: response.filter_options.workstations.map(mapOption),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminCashFlowMovementFromApi),
    page: response.page,
    pageSize: response.page_size,
    summary: {
      cardTotal: String(response.summary.card_total),
      cashTotal: String(response.summary.cash_total),
      differenceTotal: String(response.summary.difference_total),
      inflowsTotal: String(response.summary.inflows_total),
      netTotal: String(response.summary.net_total),
      operationalPaymentsTotal: String(response.summary.operational_payments_total),
      outflowsTotal: String(response.summary.outflows_total),
      pendingReconciliationTotal: String(response.summary.pending_reconciliation_total),
      refundsTotal: String(response.summary.refunds_total),
    },
    total: response.total,
    trend: response.trend.map(mapTrendPoint),
  };
}

function mapDetailFromApi(response: ApiDetail): AdminCashFlowMovementDetail {
  return {
    availableActions: {
      canCopyReference: response.available_actions.can_copy_reference,
      canExport: response.available_actions.can_export,
      canOpenCashCut: response.available_actions.can_open_cash_cut,
      canOpenReconciliation: response.available_actions.can_open_reconciliation,
      canOpenSource: response.available_actions.can_open_source,
      note: response.available_actions.note ?? null,
    },
    backendContract: mapBackendContract(response.backend_contract),
    financialClassification: {
      affectsBankSettlement: response.financial_classification.affects_bank_settlement,
      affectsCashDrawer: response.financial_classification.affects_cash_drawer,
      cardImpact: String(response.financial_classification.card_impact),
      cashImpact: String(response.financial_classification.cash_impact),
      direction: response.financial_classification.direction,
      netEffect: String(response.financial_classification.net_effect),
      note: response.financial_classification.note ?? null,
      paymentMethod: response.financial_classification.payment_method,
      sourceCategory: response.financial_classification.source_category ?? null,
    },
    overview: mapAdminCashFlowOverviewFromApi(response.overview, response.reconciliation.status),
    reconciliation: {
      message: response.reconciliation.message,
      reasonLabel: response.reconciliation.reason_label ?? null,
      reconciliationFolio: response.reconciliation.reconciliation_folio ?? null,
      reconciliationId: response.reconciliation.reconciliation_id ?? null,
      routeHint: response.reconciliation.route_hint ?? null,
      status: response.reconciliation.status,
      unresolvedAmount:
        response.reconciliation.unresolved_amount == null
          ? null
          : String(response.reconciliation.unresolved_amount),
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
    sourceDocumentContext: {
      cashCutFolio: response.source_document_context.cash_cut_folio ?? null,
      cashCutId: response.source_document_context.cash_cut_id ?? null,
      cashCutRouteHint: response.source_document_context.cash_cut_route_hint ?? null,
      cashSessionId: response.source_document_context.cash_session_id ?? null,
      concept: response.source_document_context.concept ?? null,
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
      note: response.source_document_context.note ?? null,
      originalTicketFolio: response.source_document_context.original_ticket_folio ?? null,
      sourcePaymentMethod: response.source_document_context.source_payment_method ?? null,
      sourceReference: response.source_document_context.source_reference,
      sourceRouteHint: response.source_document_context.source_route_hint ?? null,
      sourceStatus: response.source_document_context.source_status ?? null,
      sourceTotalAmount:
        response.source_document_context.source_total_amount == null
          ? null
          : String(response.source_document_context.source_total_amount),
      sourceType: response.source_document_context.source_type,
    },
  };
}

export function buildAdminCashFlowListPath(filters: AdminCashFlowListFilters): string {
  const params = new URLSearchParams();

  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "amount_max", filters.amountMax);
  appendOptionalParam(params, "amount_min", filters.amountMin);
  appendOptionalParam(params, "branch_id", filters.branchId);
  appendOptionalParam(params, "category", filters.category);
  appendOptionalParam(params, "date_from", toDateTimeParam(filters.dateFrom, "start"));
  appendOptionalParam(params, "date_to", toDateTimeParam(filters.dateTo, "end"));
  appendOptionalParam(params, "direction", filters.direction);
  appendOptionalParam(params, "operator_id", filters.operatorId);
  appendOptionalParam(params, "payment_method", filters.paymentMethod);
  appendOptionalParam(params, "reconciliation_state", filters.reconciliationState);
  appendOptionalParam(params, "search", filters.search.trim());
  appendOptionalParam(params, "source_type", filters.sourceType);
  appendOptionalParam(params, "workstation_id", filters.workstationId);

  return `/v1/admin/cash-flow?${params.toString()}`;
}

export function fetchAdminCashFlowMovements(
  accessToken: string,
  filters: AdminCashFlowListFilters,
): Promise<AdminCashFlowListResponse> {
  return requestJson<ApiListResponse>({
    accessToken,
    path: buildAdminCashFlowListPath(filters),
  }).then(mapListFromApi);
}

export function fetchAdminCashFlowMovementDetail(
  accessToken: string,
  movementId: string,
): Promise<AdminCashFlowMovementDetail> {
  return requestJson<ApiDetail>({
    accessToken,
    path: `/v1/admin/cash-flow/${encodeURIComponent(movementId)}`,
  }).then(mapDetailFromApi);
}
