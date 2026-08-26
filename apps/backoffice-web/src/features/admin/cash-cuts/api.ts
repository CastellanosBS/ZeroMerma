import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminCashCutBackendContract,
  AdminCashCutDetail,
  AdminCashCutFilterOption,
  AdminCashCutListFilters,
  AdminCashCutListItem,
  AdminCashCutsListResponse,
} from "./types";

type ApiCashCutFilterOption = components["schemas"]["AdminCashCutFilterOptionView"];
type ApiCashCutsListResponse = components["schemas"]["AdminCashCutsListResponse"];
type ApiCashCutListItem = components["schemas"]["AdminCashCutListItemView"];
type ApiCashCutDetail = components["schemas"]["AdminCashCutDetailView"];

export const adminCashCutsBackendContract: AdminCashCutBackendContract = {
  detailEndpoint: "GET /v1/admin/cash-cuts/{cash_session_id}",
  exportEndpoint: null,
  listEndpoint: "GET /v1/admin/cash-cuts",
  printEndpoint: null,
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

function appendOptionalBooleanParam(params: URLSearchParams, key: string, value: string) {
  if (value === "all") {
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

function mapOption(option: ApiCashCutFilterOption): AdminCashCutFilterOption {
  return {
    id: option.id,
    label: option.label,
  };
}

function mapBackendContract(
  contract: ApiCashCutsListResponse["backend_contract"] | ApiCashCutDetail["backend_contract"],
): AdminCashCutBackendContract {
  return {
    detailEndpoint: contract.detail_endpoint,
    exportEndpoint: contract.export_endpoint ?? null,
    listEndpoint: contract.list_endpoint,
    printEndpoint: contract.print_endpoint ?? null,
  };
}

export function mapAdminCashCutFromApi(item: ApiCashCutListItem): AdminCashCutListItem {
  return {
    branchId: item.branch_id,
    branchName: item.branch_name,
    cashSessionId: item.cash_session_id,
    cashierId: item.cashier_id,
    cashierName: item.cashier_name,
    closeId: item.close_id ?? null,
    closedAt: item.closed_at ?? null,
    countedCashAmount: item.counted_cash_amount == null ? null : String(item.counted_cash_amount),
    differenceAmount: item.difference_amount == null ? null : String(item.difference_amount),
    differenceState: item.difference_state,
    expectedCashAmount: String(item.expected_cash_amount),
    folio: item.folio,
    hasOperationalPayments: item.has_operational_payments,
    hasRefunds: item.has_refunds,
    id: item.id,
    openedAt: item.opened_at,
    openingAmount: String(item.opening_amount),
    paymentMethodsSummary: item.payment_methods_summary,
    status: item.status,
    totalSalesAmount: String(item.total_sales_amount),
    warningCount: item.warning_count,
    warningState: item.warning_state,
    workstationCode: item.workstation_code,
    workstationId: item.workstation_id,
    workstationName: item.workstation_name,
  };
}

function mapListFromApi(response: ApiCashCutsListResponse): AdminCashCutsListResponse {
  return {
    backendContract: mapBackendContract(response.backend_contract),
    filterOptions: {
      branches: response.filter_options.branches.map(mapOption),
      cashiers: response.filter_options.cashiers.map(mapOption),
      differenceStates: response.filter_options.difference_states.map(mapOption),
      paymentMethods: response.filter_options.payment_methods.map(mapOption),
      statuses: response.filter_options.statuses.map(mapOption),
      workstations: response.filter_options.workstations.map(mapOption),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminCashCutFromApi),
    metrics: {
      closedCutsCount: String(response.metrics.closed_cuts_count),
      countedCashAmount: String(response.metrics.counted_cash_amount),
      cutsWithDifferenceCount: String(response.metrics.cuts_with_difference_count),
      expectedCashAmount: String(response.metrics.expected_cash_amount),
      netDifferenceAmount: String(response.metrics.net_difference_amount),
      netSalesAmount: String(response.metrics.net_sales_amount),
      operationalPaymentsAmount: String(response.metrics.operational_payments_amount),
      pendingCloseCount: String(response.metrics.pending_close_count),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function mapDetailFromApi(response: ApiCashCutDetail): AdminCashCutDetail {
  return {
    auditTimeline: response.audit_timeline.map((item) => ({
      actorName: item.actor_name ?? null,
      eventCode: item.event_code,
      label: item.label,
      occurredAt: item.occurred_at,
      summary: item.summary ?? null,
    })),
    availableActions: {
      canCopyFolio: response.available_actions.can_copy_folio,
      canExportReport: response.available_actions.can_export_report,
      canOpenOperationalPayments: response.available_actions.can_open_operational_payments,
      canOpenReturns: response.available_actions.can_open_returns,
      canOpenTickets: response.available_actions.can_open_tickets,
      canPrintReport: response.available_actions.can_print_report,
      canRemoteClose: response.available_actions.can_remote_close,
      remoteCloseNote: response.available_actions.remote_close_note ?? null,
    },
    backendContract: mapBackendContract(response.backend_contract),
    correctionsAdjustments: response.corrections_adjustments.map((item) => ({
      amount: item.amount == null ? null : String(item.amount),
      documentType: item.document_type,
      folio: item.folio,
      id: item.id,
      notes: item.notes ?? null,
      occurredAt: item.occurred_at ?? null,
      operatorName: item.operator_name ?? null,
      routeHint: item.route_hint ?? null,
    })),
    denominationCount: {
      isSupported: response.denomination_count.is_supported,
      lines: response.denomination_count.lines.map((line) => ({
        denomination: String(line.denomination),
        quantity: line.quantity,
        subtotal: String(line.subtotal),
      })),
      note: response.denomination_count.note ?? null,
      totalCounted:
        response.denomination_count.total_counted == null
          ? null
          : String(response.denomination_count.total_counted),
    },
    expectedVsCounted: {
      cashAdjustmentsAmount: String(response.expected_vs_counted.cash_adjustments_amount),
      cashOperationalDiscountsAmount: String(
        response.expected_vs_counted.cash_operational_discounts_amount,
      ),
      cashOperationalPaymentsAmount: String(
        response.expected_vs_counted.cash_operational_payments_amount,
      ),
      cashRefundsAmount: String(response.expected_vs_counted.cash_refunds_amount),
      cashSalesAmount: String(response.expected_vs_counted.cash_sales_amount),
      countedCashAmount:
        response.expected_vs_counted.counted_cash_amount == null
          ? null
          : String(response.expected_vs_counted.counted_cash_amount),
      differenceAmount:
        response.expected_vs_counted.difference_amount == null
          ? null
          : String(response.expected_vs_counted.difference_amount),
      differenceState: response.expected_vs_counted.difference_state,
      expectedCashAmount: String(response.expected_vs_counted.expected_cash_amount),
      isCountedCashAvailable: response.expected_vs_counted.is_counted_cash_available,
      note: response.expected_vs_counted.note ?? null,
      openingAmount: String(response.expected_vs_counted.opening_amount),
    },
    includedTickets: response.included_tickets.map((ticket) => ({
      cashierName: ticket.cashier_name,
      currencyCode: ticket.currency_code,
      folio: ticket.folio,
      occurredAt: ticket.occurred_at,
      paymentMethodSummary: ticket.payment_method_summary,
      routeHint: ticket.route_hint,
      status: ticket.status,
      ticketId: ticket.ticket_id,
      totalAmount: String(ticket.total_amount),
    })),
    operationalPayments: response.operational_payments.map((payment) => ({
      amount: String(payment.amount),
      cashAmount: String(payment.cash_amount),
      categoryCode: payment.category_code ?? null,
      categoryName: payment.category_name ?? null,
      folio: payment.folio,
      id: payment.id,
      notes: payment.notes ?? null,
      occurredAt: payment.occurred_at,
      operatorName: payment.operator_name,
      paymentMethodCode: payment.payment_method_code,
      routeHint: payment.route_hint,
    })),
    overview: {
      branchCode: response.overview.branch_code,
      branchId: response.overview.branch_id,
      branchName: response.overview.branch_name,
      cashSessionId: response.overview.cash_session_id,
      cashierId: response.overview.cashier_id,
      cashierName: response.overview.cashier_name,
      closeId: response.overview.close_id ?? null,
      closedAt: response.overview.closed_at ?? null,
      closingNotes: response.overview.closing_notes ?? null,
      folio: response.overview.folio,
      id: response.overview.id,
      openedAt: response.overview.opened_at,
      openingAmount: String(response.overview.opening_amount),
      status: response.overview.status,
      totalDurationMinutes: response.overview.total_duration_minutes ?? null,
      warningState: response.overview.warning_state,
      workstationCode: response.overview.workstation_code,
      workstationId: response.overview.workstation_id,
      workstationName: response.overview.workstation_name,
    },
    paymentBreakdown: response.payment_breakdown.map((row) => ({
      countedAmount: row.counted_amount == null ? null : String(row.counted_amount),
      currencyCode: row.currency_code,
      expectedAmount: row.expected_amount == null ? null : String(row.expected_amount),
      isCountedSupported: row.is_counted_supported,
      netAmount: String(row.net_amount),
      operationalDiscountAmount: String(row.operational_discount_amount),
      operationalPaymentAmount: String(row.operational_payment_amount),
      paymentMethodCode: row.payment_method_code,
      refundAmount: String(row.refund_amount),
      salesAmount: String(row.sales_amount),
      varianceAmount: row.variance_amount == null ? null : String(row.variance_amount),
    })),
    reconciliationStatus: {
      note: response.reconciliation_status.note ?? null,
      reconciledAt: response.reconciliation_status.reconciled_at ?? null,
      reconciledByName: response.reconciliation_status.reconciled_by_name ?? null,
      relatedDocumentId: response.reconciliation_status.related_document_id ?? null,
      routeHint: response.reconciliation_status.route_hint ?? null,
      status: response.reconciliation_status.status,
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
    returnsRefunds: response.returns_refunds.map((refund) => ({
      amount: String(refund.amount),
      folio: refund.folio,
      id: refund.id,
      occurredAt: refund.occurred_at,
      operatorName: refund.operator_name,
      originalTicketFolio: refund.original_ticket_folio,
      paymentMethodCode: refund.payment_method_code,
      reasonName: refund.reason_name,
      routeHint: refund.route_hint,
      status: refund.status,
    })),
  };
}

export function buildAdminCashCutsListPath(filters: AdminCashCutListFilters): string {
  const params = new URLSearchParams();

  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "branch_id", filters.branchId);
  appendOptionalParam(params, "cashier_id", filters.cashierId);
  appendOptionalParam(params, "date_from", toDateTimeParam(filters.dateFrom, "start"));
  appendOptionalParam(params, "date_to", toDateTimeParam(filters.dateTo, "end"));
  appendOptionalParam(params, "difference_state", filters.differenceState);
  appendOptionalBooleanParam(params, "has_operational_payments", filters.hasOperationalPayments);
  appendOptionalBooleanParam(params, "has_refunds", filters.hasRefunds);
  appendOptionalParam(params, "payment_method", filters.paymentMethod);
  appendOptionalParam(params, "search", filters.search.trim());
  appendOptionalParam(params, "status", filters.status);
  appendOptionalParam(params, "workstation_id", filters.workstationId);

  return `/v1/admin/cash-cuts?${params.toString()}`;
}

export function fetchAdminCashCuts(
  accessToken: string,
  filters: AdminCashCutListFilters,
): Promise<AdminCashCutsListResponse> {
  return requestJson<ApiCashCutsListResponse>({
    accessToken,
    path: buildAdminCashCutsListPath(filters),
  }).then(mapListFromApi);
}

export function fetchAdminCashCutDetail(
  accessToken: string,
  cashSessionId: string,
): Promise<AdminCashCutDetail> {
  return requestJson<ApiCashCutDetail>({
    accessToken,
    path: `/v1/admin/cash-cuts/${cashSessionId}`,
  }).then(mapDetailFromApi);
}
