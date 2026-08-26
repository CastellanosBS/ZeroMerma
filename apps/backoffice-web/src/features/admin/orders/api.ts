import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminOrderBackendContract,
  AdminOrderDetail,
  AdminOrderFilterOption,
  AdminOrderListFilters,
  AdminOrderListItem,
  AdminOrderMetrics,
  AdminOrdersListResponse,
  AdminOrderOperationalContext,
} from "./types";

type ApiOrderListResponse = components["schemas"]["AdminOrdersListResponse"];
type ApiOrderListItem = components["schemas"]["AdminOrderListItemView"];
type ApiOrderDetail = components["schemas"]["AdminOrderDetailView"];
type ApiOrderFilterOption = components["schemas"]["AdminOrderFilterOptionView"];

export const adminOrdersBackendContract: AdminOrderBackendContract = {
  cancelEndpoint: "POST /v1/admin/orders/{order_id}/cancel",
  createEndpoint: null,
  deliverEndpoint: "POST /v1/admin/orders/{order_id}/deliver",
  detailEndpoint: "GET /v1/admin/orders/{order_id}",
  financialCaptureEndpoint: null,
  listEndpoint: "GET /v1/admin/orders",
  markReadyEndpoint: "POST /v1/admin/orders/{order_id}/mark-ready",
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
  return `${value}${boundary === "start" ? "T00:00:00.000Z" : "T23:59:59.999Z"}`;
}

function mapOption(option: ApiOrderFilterOption): AdminOrderFilterOption {
  return {
    id: option.id,
    label: option.label,
  };
}

function mapBackendContract(contract: ApiOrderListResponse["backend_contract"]): AdminOrderBackendContract {
  return {
    cancelEndpoint: contract.cancel_endpoint,
    createEndpoint: contract.create_endpoint ?? null,
    deliverEndpoint: contract.deliver_endpoint,
    detailEndpoint: contract.detail_endpoint,
    financialCaptureEndpoint: contract.financial_capture_endpoint ?? null,
    listEndpoint: contract.list_endpoint,
    markReadyEndpoint: contract.mark_ready_endpoint,
  };
}

function mapMetrics(metrics: ApiOrderListResponse["metrics"]): AdminOrderMetrics {
  return {
    activeOrders: metrics.active_orders,
    canceledOrders: metrics.canceled_orders,
    depositsReceivedAmount: String(metrics.deposits_received_amount),
    dueToday: metrics.due_today,
    outstandingBalanceAmount: String(metrics.outstanding_balance_amount),
    readyOrders: metrics.ready_orders,
  };
}

export function mapAdminOrderFromApi(item: ApiOrderListItem): AdminOrderListItem {
  return {
    advanceAmount: String(item.advance_amount),
    branchId: item.branch_id,
    branchName: item.branch_name,
    cancellationRefundAmount: String(item.cancellation_refund_amount),
    cancellationRefundEligible: item.cancellation_refund_eligible,
    createdAtUtc: item.created_at_utc,
    createdByUserFullName: item.created_by_user_full_name,
    createdByUserId: item.created_by_user_id,
    currencyCode: item.currency_code,
    customerName: item.customer_name,
    customerPhone: item.customer_phone ?? null,
    folio: item.folio,
    id: item.id,
    lineCount: item.line_count,
    paymentState: item.payment_state,
    remainingBalanceAmount: String(item.remaining_balance_amount),
    requestedForAt: item.requested_for_at ?? null,
    status: item.status,
    totalAmount: String(item.total_amount),
    totalUnits: String(item.total_units),
    updatedAtUtc: item.updated_at_utc,
    warningState: item.warning_state ?? null,
    workstationCode: item.workstation_code,
    workstationId: item.workstation_id,
    workstationName: item.workstation_name,
  };
}

function mapListFromApi(response: ApiOrderListResponse): AdminOrdersListResponse {
  return {
    backendContract: mapBackendContract(response.backend_contract),
    filterOptions: {
      branches: response.filter_options.branches.map(mapOption),
      cashiers: response.filter_options.cashiers.map(mapOption),
      paymentStates: response.filter_options.payment_states.map(mapOption),
      statuses: response.filter_options.statuses.map(mapOption),
      workstations: response.filter_options.workstations.map(mapOption),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminOrderFromApi),
    metrics: mapMetrics(response.metrics),
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function readContextValue(
  context: ApiOrderDetail["operational_context"],
  key: keyof AdminOrderOperationalContext,
): string | null {
  const snakeKey = key.replace(/[A-Z]/g, (match) => `_${match.toLowerCase()}`);
  return context[snakeKey] ?? null;
}

function mapDetailFromApi(response: ApiOrderDetail): AdminOrderDetail {
  return {
    availableActions: {
      canCancel: response.available_actions.can_cancel,
      canCaptureBalance: response.available_actions.can_capture_balance,
      canCreateFromBackoffice: response.available_actions.can_create_from_backoffice,
      canDeliver: response.available_actions.can_deliver,
      canMarkReady: response.available_actions.can_mark_ready,
      financialActionNote: response.available_actions.financial_action_note ?? null,
      requiresCashSessionForFinancialAction:
        response.available_actions.requires_cash_session_for_financial_action,
      requiresSettlementOnDelivery: response.available_actions.requires_settlement_on_delivery,
    },
    backendContract: {
      cancelEndpoint: response.backend_contract.cancel_endpoint,
      createEndpoint: response.backend_contract.create_endpoint ?? null,
      deliverEndpoint: response.backend_contract.deliver_endpoint,
      detailEndpoint: response.backend_contract.detail_endpoint,
      financialCaptureEndpoint: response.backend_contract.financial_capture_endpoint ?? null,
      listEndpoint: response.backend_contract.list_endpoint,
      markReadyEndpoint: response.backend_contract.mark_ready_endpoint,
    },
    customer: {
      name: response.customer.name,
      notes: response.customer.notes ?? null,
      phone: response.customer.phone ?? null,
    },
    lines: response.lines.map((line) => ({
      id: line.id,
      lineNumber: line.line_number,
      lineTotalAmount: String(line.line_total_amount),
      productClassCode: line.product_class_code,
      productClassId: line.product_class_id,
      productClassName: line.product_class_name,
      productCode: line.product_code,
      productId: line.product_id,
      productName: line.product_name,
      quantity: String(line.quantity),
      unitPrice: String(line.unit_price),
    })),
    operationalContext: {
      activeCashSessionId: readContextValue(response.operational_context, "activeCashSessionId"),
      branchId: readContextValue(response.operational_context, "branchId"),
      branchName: readContextValue(response.operational_context, "branchName"),
      canceledByUserFullName: readContextValue(response.operational_context, "canceledByUserFullName"),
      createdByUserFullName: readContextValue(response.operational_context, "createdByUserFullName"),
      createdByUserId: readContextValue(response.operational_context, "createdByUserId"),
      deliveredByUserFullName: readContextValue(response.operational_context, "deliveredByUserFullName"),
      workstationCode: readContextValue(response.operational_context, "workstationCode"),
      workstationId: readContextValue(response.operational_context, "workstationId"),
      workstationName: readContextValue(response.operational_context, "workstationName"),
    },
    overview: {
      advanceAmount: String(response.overview.advance_amount),
      branchId: response.overview.branch_id,
      branchName: response.overview.branch_name,
      canceledAt: response.overview.canceled_at ?? null,
      cancellationReason: response.overview.cancellation_reason ?? null,
      cancellationRefundAmount: String(response.overview.cancellation_refund_amount),
      cancellationRefundEligible: response.overview.cancellation_refund_eligible,
      createdAtUtc: response.overview.created_at_utc,
      currencyCode: response.overview.currency_code,
      customerName: response.overview.customer_name,
      customerPhone: response.overview.customer_phone ?? null,
      deliveredAt: response.overview.delivered_at ?? null,
      folio: response.overview.folio,
      id: response.overview.id,
      paymentState: response.overview.payment_state,
      remainingBalanceAmount: String(response.overview.remaining_balance_amount),
      requestedForAt: response.overview.requested_for_at ?? null,
      status: response.overview.status,
      totalAmount: String(response.overview.total_amount),
      updatedAtUtc: response.overview.updated_at_utc,
    },
    payments: response.payments.map((payment) => ({
      amount: String(payment.amount),
      currencyCode: payment.currency_code,
      id: payment.id,
      paymentMethodCode: payment.payment_method_code,
      paymentType: payment.payment_type,
      recordedAtUtc: payment.recorded_at_utc,
      recordedByUserFullName: payment.recorded_by_user_full_name,
      recordedByUserId: payment.recorded_by_user_id,
      sequence: payment.sequence,
    })),
    relatedDocuments: response.related_documents.map((document) => ({
      amount: document.amount == null ? null : String(document.amount),
      documentType: document.document_type,
      folio: document.folio,
      id: document.id,
      occurredAt: document.occurred_at ?? null,
      routeHint: document.route_hint ?? null,
      status: document.status,
    })),
    timeline: response.timeline.map((event) => ({
      description: event.description ?? null,
      key: event.key,
      label: event.label,
      occurredAt: event.occurred_at,
    })),
  };
}

export function buildAdminOrdersListPath(filters: AdminOrderListFilters): string {
  const params = new URLSearchParams();
  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "branch_id", filters.branchId);
  appendOptionalParam(params, "cashier_id", filters.cashierId);
  appendOptionalParam(params, "date_from", toDateTimeParam(filters.dateFrom, "start"));
  appendOptionalParam(params, "date_to", toDateTimeParam(filters.dateTo, "end"));
  appendOptionalParam(params, "payment_state", filters.paymentState);
  appendOptionalParam(params, "search", filters.search?.trim());
  appendOptionalParam(params, "status", filters.status);
  appendOptionalParam(params, "workstation_id", filters.workstationId);
  return `/v1/admin/orders?${params.toString()}`;
}

export function fetchAdminOrders(
  accessToken: string,
  filters: AdminOrderListFilters,
): Promise<AdminOrdersListResponse> {
  return requestJson<ApiOrderListResponse>({
    accessToken,
    path: buildAdminOrdersListPath(filters),
  }).then(mapListFromApi);
}

export function fetchAdminOrderDetail(accessToken: string, orderId: string): Promise<AdminOrderDetail> {
  return requestJson<ApiOrderDetail>({
    accessToken,
    path: `/v1/admin/orders/${orderId}`,
  }).then(mapDetailFromApi);
}

export function markAdminOrderReady(accessToken: string, orderId: string): Promise<AdminOrderDetail> {
  return requestJson<ApiOrderDetail>({
    accessToken,
    body: {},
    method: "POST",
    path: `/v1/admin/orders/${orderId}/mark-ready`,
  }).then(mapDetailFromApi);
}

export function deliverAdminOrder(accessToken: string, orderId: string): Promise<AdminOrderDetail> {
  return requestJson<ApiOrderDetail>({
    accessToken,
    body: {},
    method: "POST",
    path: `/v1/admin/orders/${orderId}/deliver`,
  }).then(mapDetailFromApi);
}

export function cancelAdminOrder(accessToken: string, orderId: string): Promise<AdminOrderDetail> {
  return requestJson<ApiOrderDetail>({
    accessToken,
    body: {},
    method: "POST",
    path: `/v1/admin/orders/${orderId}/cancel`,
  }).then(mapDetailFromApi);
}
