import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminSalesTicketBackendContract,
  AdminSalesTicketDetail,
  AdminSalesTicketFilterOption,
  AdminSalesTicketListFilters,
  AdminSalesTicketListItem,
  AdminSalesTicketListResponse,
  AdminSalesTicketMetrics,
  AdminSalesTicketPaymentSummary,
} from "./types";

type ApiFilterOption = components["schemas"]["AdminSalesTicketFilterOptionView"];
type ApiTicketListResponse = components["schemas"]["AdminSalesTicketsListResponse"];
type ApiTicketListItem = components["schemas"]["AdminSalesTicketListItemView"];
type ApiTicketDetail = components["schemas"]["AdminSalesTicketDetailView"];
type ApiPaymentSummary = components["schemas"]["AdminSalesTicketPaymentSummaryView"];

export const adminSalesTicketsBackendContract: AdminSalesTicketBackendContract = {
  detailEndpoint: "GET /v1/admin/sales/tickets/{ticket_id}",
  listEndpoint: "GET /v1/admin/sales/tickets",
  reprintEndpoint: "POST /v1/admin/sales/tickets/{ticket_id}/reprint",
};

function appendOptionalParam(params: URLSearchParams, key: string, value: string | null | undefined) {
  if (!value || value === "all") {
    return;
  }
  params.set(key, value);
}

function toDateTimeParam(value: string | null | undefined, boundary: "start" | "end"): string | null {
  if (!value) {
    return null;
  }
  const suffix = boundary === "start" ? "T00:00:00.000Z" : "T23:59:59.999Z";
  return `${value}${suffix}`;
}

function mapOption(option: ApiFilterOption): AdminSalesTicketFilterOption {
  return {
    id: option.id,
    label: option.label,
  };
}

function mapPaymentSummary(item: ApiPaymentSummary): AdminSalesTicketPaymentSummary {
  return {
    amount: String(item.amount),
    currencyCode: item.currency_code,
    paymentMethodCode: item.payment_method_code,
  };
}

function mapMetrics(metrics: ApiTicketListResponse["metrics"]): AdminSalesTicketMetrics {
  return {
    averageTicketAmount: String(metrics.average_ticket_amount),
    cardAmount: String(metrics.card_amount),
    cashAmount: String(metrics.cash_amount),
    ticketCount: String(metrics.ticket_count),
    ticketsWithReturns: String(metrics.tickets_with_returns),
    totalSalesAmount: String(metrics.total_sales_amount),
  };
}

export function mapAdminSalesTicketFromApi(item: ApiTicketListItem): AdminSalesTicketListItem {
  return {
    branchId: item.branch_id,
    branchName: item.branch_name,
    cashierId: item.cashier_id,
    cashierName: item.cashier_name,
    currencyCode: item.currency_code,
    folio: item.folio,
    hasReturns: item.has_returns,
    id: item.id,
    itemCount: item.item_count,
    occurredAt: item.occurred_at,
    paymentMethodsLabel: item.payment_methods_label,
    paymentSummary: item.payment_summary.map(mapPaymentSummary),
    returnCount: item.return_count,
    returnStatus: item.return_status,
    saleId: item.sale_id,
    status: item.status,
    totalAmount: String(item.total_amount),
    unitCount: String(item.unit_count),
    workstationCode: item.workstation_code,
    workstationId: item.workstation_id,
    workstationName: item.workstation_name,
  };
}

function mapListFromApi(response: ApiTicketListResponse): AdminSalesTicketListResponse {
  return {
    backendContract: {
      detailEndpoint: response.backend_contract.detail_endpoint,
      listEndpoint: response.backend_contract.list_endpoint,
      reprintEndpoint: response.backend_contract.reprint_endpoint ?? null,
    },
    filterOptions: {
      branches: response.filter_options.branches.map(mapOption),
      cashiers: response.filter_options.cashiers.map(mapOption),
      paymentMethods: response.filter_options.payment_methods.map(mapOption),
      statuses: response.filter_options.statuses.map(mapOption),
      workstations: response.filter_options.workstations.map(mapOption),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminSalesTicketFromApi),
    metrics: mapMetrics(response.metrics),
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function mapDetailFromApi(response: ApiTicketDetail): AdminSalesTicketDetail {
  return {
    lines: response.lines.map((line) => ({
      captureMode: line.capture_mode,
      catalogCode: line.catalog_code,
      catalogName: line.catalog_name,
      discountAmount: String(line.discount_amount),
      id: line.id,
      lineTotalAmount: String(line.line_total_amount),
      physicalAttributionStatus: line.physical_attribution_status,
      productClassId: line.product_class_id ?? null,
      productId: line.product_id ?? null,
      quantity: String(line.quantity),
      sequence: line.sequence,
      unitPrice: String(line.unit_price),
    })),
    operationalContext: {
      branchId: response.operational_context.branch_id,
      branchName: response.operational_context.branch_name,
      cashSessionId: response.operational_context.cash_session_id,
      cashierEmail: response.operational_context.cashier_email,
      cashierId: response.operational_context.cashier_id,
      cashierName: response.operational_context.cashier_name,
      confirmedAt: response.operational_context.confirmed_at,
      createdAt: response.operational_context.created_at,
      saleId: response.operational_context.sale_id,
      workstationCode: response.operational_context.workstation_code,
      workstationId: response.operational_context.workstation_id,
      workstationName: response.operational_context.workstation_name,
    },
    overview: {
      changeAmount: String(response.overview.change_amount),
      confirmedAt: response.overview.confirmed_at,
      currencyCode: response.overview.currency_code,
      folio: response.overview.folio,
      id: response.overview.id,
      itemCount: response.overview.item_count,
      paidAmount: String(response.overview.paid_amount),
      returnCount: response.overview.return_count,
      returnStatus: response.overview.return_status,
      returnedAmount: String(response.overview.returned_amount),
      status: response.overview.status,
      subtotalAmount: String(response.overview.subtotal_amount),
      totalAmount: String(response.overview.total_amount),
      unitCount: String(response.overview.unit_count),
    },
    payments: response.payments.map((payment) => ({
      appliedAmount: String(payment.applied_amount),
      changeAmount: String(payment.change_amount),
      currencyCode: payment.currency_code,
      id: payment.id,
      paymentMethodCode: payment.payment_method_code,
      receivedAt: payment.received_at,
      sequence: payment.sequence,
      tenderedAmount: String(payment.tendered_amount),
    })),
    printableTicket: {
      canReprint: response.printable_ticket.can_reprint,
      note: response.printable_ticket.note ?? null,
      previewAvailable: response.printable_ticket.preview_available,
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
  };
}

export function buildAdminSalesTicketsListPath(filters: AdminSalesTicketListFilters): string {
  const params = new URLSearchParams();

  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "branch_id", filters.branchId);
  appendOptionalParam(params, "cashier_id", filters.cashierId);
  appendOptionalParam(params, "date_from", toDateTimeParam(filters.dateFrom, "start"));
  appendOptionalParam(params, "date_to", toDateTimeParam(filters.dateTo, "end"));
  appendOptionalParam(params, "max_amount", filters.maxAmount?.trim());
  appendOptionalParam(params, "min_amount", filters.minAmount?.trim());
  appendOptionalParam(params, "payment_method", filters.paymentMethod);
  appendOptionalParam(params, "search", filters.search?.trim());
  appendOptionalParam(params, "status", filters.status);
  appendOptionalParam(params, "workstation_id", filters.workstationId);

  return `/v1/admin/sales/tickets?${params.toString()}`;
}

export function fetchAdminSalesTickets(
  accessToken: string,
  filters: AdminSalesTicketListFilters,
): Promise<AdminSalesTicketListResponse> {
  return requestJson<ApiTicketListResponse>({
    accessToken,
    path: buildAdminSalesTicketsListPath(filters),
  }).then(mapListFromApi);
}

export function fetchAdminSalesTicketDetail(
  accessToken: string,
  ticketId: string,
): Promise<AdminSalesTicketDetail> {
  return requestJson<ApiTicketDetail>({
    accessToken,
    path: `/v1/admin/sales/tickets/${ticketId}`,
  }).then(mapDetailFromApi);
}

export function reprintAdminSalesTicket(
  accessToken: string,
  ticketId: string,
): Promise<AdminSalesTicketDetail> {
  return requestJson<ApiTicketDetail>({
    accessToken,
    method: "POST",
    path: `/v1/admin/sales/tickets/${ticketId}/reprint`,
  }).then(mapDetailFromApi);
}
