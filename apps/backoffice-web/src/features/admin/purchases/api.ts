import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminDirectEntryPayload,
  AdminPurchaseBackendContract,
  AdminPurchaseCancelPayload,
  AdminPurchaseDetail,
  AdminPurchaseFilterOption,
  AdminPurchaseListFilters,
  AdminPurchaseListItem,
  AdminPurchaseListResponse,
  AdminPurchasePayload,
  AdminPurchaseReceiptPayload,
  AdminPurchaseWarning,
} from "./types";

export const adminPurchaseBackendContract: AdminPurchaseBackendContract = {
  cancelEndpoint: "POST /v1/admin/purchases/{purchase_id}/cancel",
  confirmEndpoint: "POST /v1/admin/purchases/{purchase_id}/confirm",
  createDirectEntryEndpoint: "POST /v1/admin/purchases/direct-entry",
  createEndpoint: "POST /v1/admin/purchases",
  detailEndpoint: "GET /v1/admin/purchases/{purchase_id}",
  listEndpoint: "GET /v1/admin/purchases",
  receiveEndpoint: "POST /v1/admin/purchases/{purchase_id}/receive",
  updateEndpoint: "PATCH /v1/admin/purchases/{purchase_id}",
};

type ApiBackendContract = components["schemas"]["AdminPurchaseBackendContractView"];
type ApiDirectEntryPayload = components["schemas"]["AdminPurchaseDirectEntryRequest"];
type ApiPurchaseCancelPayload = components["schemas"]["AdminPurchaseCancelRequest"];
type ApiPurchaseCreatePayload = components["schemas"]["AdminPurchaseCreateRequest"];
type ApiPurchaseDetail = components["schemas"]["AdminPurchaseDetailView"];
type ApiPurchaseFilterOption = components["schemas"]["AdminPurchaseFilterOptionView"];
type ApiPurchaseListItem = components["schemas"]["AdminPurchaseListItemView"];
type ApiPurchaseListResponse = components["schemas"]["AdminPurchaseListResponse"];
type ApiPurchaseReceiptPayload = components["schemas"]["AdminPurchaseReceiveRequest"];
type ApiPurchaseWarning = components["schemas"]["AdminPurchaseWarningView"];

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

function mapFilterOptions(options: ApiPurchaseFilterOption[]): AdminPurchaseFilterOption[] {
  return options.map((option) => ({ id: String(option.id), label: option.label }));
}

function mapWarning(warning: ApiPurchaseWarning): AdminPurchaseWarning {
  return {
    code: warning.code,
    message: warning.message,
    severity: warning.severity,
  };
}

function mapBackendContract(contract?: ApiBackendContract): AdminPurchaseBackendContract {
  if (!contract) {
    return adminPurchaseBackendContract;
  }
  return {
    cancelEndpoint: contract.cancel_endpoint,
    confirmEndpoint: contract.confirm_endpoint,
    createDirectEntryEndpoint: contract.create_direct_entry_endpoint,
    createEndpoint: contract.create_endpoint,
    detailEndpoint: contract.detail_endpoint,
    listEndpoint: contract.list_endpoint,
    receiveEndpoint: contract.receive_endpoint,
    updateEndpoint: contract.update_endpoint,
  };
}

export function mapAdminPurchaseListItemFromApi(item: ApiPurchaseListItem): AdminPurchaseListItem {
  return {
    branchId: item.branch_id,
    branchName: item.branch_name,
    createdAt: item.created_at,
    documentDate: item.document_date,
    documentType: item.document_type,
    externalDocumentNumber: item.external_document_number ?? null,
    folio: item.folio,
    hasDiscrepancy: item.has_discrepancy,
    id: item.id,
    lineCount: item.line_count,
    operatorName: item.operator_name,
    receivedAt: item.received_at ?? null,
    receivedUnitCount: String(item.received_unit_count),
    status: item.status,
    supplierId: item.supplier_id,
    supplierName: item.supplier_name,
    totalAmount: String(item.total_amount),
    warningState: item.warning_state ?? null,
    warnings: item.warnings.map(mapWarning),
  };
}

export function mapAdminPurchaseDetailFromApi(item: ApiPurchaseDetail): AdminPurchaseDetail {
  return {
    availableActions: {
      canCancel: item.available_actions.can_cancel,
      canConfirm: item.available_actions.can_confirm,
      canEdit: item.available_actions.can_edit,
      canReceive: item.available_actions.can_receive,
      canViewMovements: item.available_actions.can_view_movements,
    },
    costSummary: {
      currency: item.cost_summary.currency,
      receivedTotal: String(item.cost_summary.received_total),
      subtotal: String(item.cost_summary.subtotal),
      taxes: item.cost_summary.taxes == null ? null : String(item.cost_summary.taxes),
      total: String(item.cost_summary.total),
    },
    inventoryImpact: {
      integrationAvailable: item.inventory_impact.integration_available,
      movements: item.inventory_impact.movements.map((movement) => ({
        balanceAfter: movement.balance_after == null ? null : String(movement.balance_after),
        branchId: movement.branch_id,
        direction: movement.direction,
        id: movement.id,
        locationCode: movement.location_code,
        movementType: movement.movement_type,
        productId: movement.product_id,
        quantity: String(movement.quantity),
        sourceDocumentId: movement.source_document_id ?? null,
        sourceDocumentType: movement.source_document_type ?? null,
        unitOfMeasure: movement.unit_of_measure,
      })),
      notes: item.inventory_impact.notes ?? null,
    },
    lines: item.lines.map((line) => ({
      discrepancy: String(line.discrepancy),
      discrepancyReason: line.discrepancy_reason ?? null,
      lineStatus: line.line_status,
      lineTotal: String(line.line_total),
      notes: line.notes ?? null,
      orderedQuantity: String(line.ordered_quantity),
      pendingQuantity: String(line.pending_quantity),
      productCode: line.product_code,
      productId: line.product_id,
      productKind: line.product_kind,
      productName: line.product_name,
      purchaseLineId: line.purchase_line_id,
      receivedQuantity: String(line.received_quantity),
      standardCost: line.standard_cost == null ? null : String(line.standard_cost),
      supplierLastKnownPrice:
        line.supplier_last_known_price == null ? null : String(line.supplier_last_known_price),
      unitCost: String(line.unit_cost),
      unitOfMeasure: line.unit_of_measure,
    })),
    overview: {
      branchId: item.overview.branch_id,
      branchName: item.overview.branch_name,
      confirmedAt: item.overview.confirmed_at ?? null,
      createdAt: item.overview.created_at,
      createdByUserId: item.overview.created_by_user_id,
      createdByUserName: item.overview.created_by_user_name,
      documentDate: item.overview.document_date,
      documentType: item.overview.document_type,
      externalDocumentNumber: item.overview.external_document_number ?? null,
      externalDocumentType: item.overview.external_document_type ?? null,
      folio: item.overview.folio,
      hasDiscrepancy: item.overview.has_discrepancy,
      id: item.overview.id,
      lineCount: item.overview.line_count,
      notes: item.overview.notes ?? null,
      receivedAt: item.overview.received_at ?? null,
      receivedUnitCount: String(item.overview.received_unit_count),
      status: item.overview.status,
      supplierId: item.overview.supplier_id,
      supplierName: item.overview.supplier_name,
      totalAmount: String(item.overview.total_amount),
      warningState: item.overview.warning_state ?? null,
    },
    receipt: {
      expectedQuantity: String(item.receipt.expected_quantity),
      hasDiscrepancy: item.receipt.has_discrepancy,
      pendingQuantity: String(item.receipt.pending_quantity),
      receiptCount: item.receipt.receipt_count,
      receivedQuantity: String(item.receipt.received_quantity),
      state: item.receipt.state,
    },
    receivingBranch: {
      branchCode: item.receiving_branch.branch_code,
      branchId: item.receiving_branch.branch_id,
      branchIsActive: item.receiving_branch.branch_is_active,
      branchName: item.receiving_branch.branch_name,
      timezone: item.receiving_branch.timezone,
    },
    relatedDocuments: item.related_documents.map((document) => ({
      documentId: document.document_id,
      documentType: document.document_type,
      folio: document.folio,
      status: document.status,
    })),
    supplierContext: {
      commercialName: item.supplier_context.commercial_name ?? null,
      leadTimeDays: item.supplier_context.lead_time_days,
      paymentTermsSummary: item.supplier_context.payment_terms_summary,
      primaryContact: item.supplier_context.primary_contact ?? null,
      status: item.supplier_context.status,
      supplierId: item.supplier_context.supplier_id,
      supplierName: item.supplier_context.supplier_name,
    },
    warnings: item.warnings.map(mapWarning),
  };
}

function mapPurchaseListFromApi(response: ApiPurchaseListResponse): AdminPurchaseListResponse {
  return {
    backendContract: mapBackendContract(response.backend_contract),
    filterOptions: {
      branches: mapFilterOptions(response.filter_options.branches),
      operators: mapFilterOptions(response.filter_options.operators),
      productKinds: mapFilterOptions(response.filter_options.product_kinds),
      products: mapFilterOptions(response.filter_options.products),
      statuses: mapFilterOptions(response.filter_options.statuses),
      suppliers: mapFilterOptions(response.filter_options.suppliers),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminPurchaseListItemFromApi),
    metrics: {
      activeSuppliersUsed: mapMetric(response.metrics.active_suppliers_used),
      confirmedEntries: mapMetric(response.metrics.confirmed_entries),
      partiallyReceived: mapMetric(response.metrics.partially_received),
      pendingReceipt: mapMetric(response.metrics.pending_receipt),
      totalAmount: mapMetric(response.metrics.total_amount),
      totalDocuments: mapMetric(response.metrics.total_documents),
      withDiscrepancies: mapMetric(response.metrics.with_discrepancies),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function toPurchaseApiPayload(payload: AdminPurchasePayload): ApiPurchaseCreatePayload {
  return {
    branch_id: payload.branchId,
    confirm_now: payload.confirmNow ?? false,
    document_date: payload.documentDate ?? null,
    external_document_date: payload.externalDocumentDate ?? null,
    external_document_number: payload.externalDocumentNumber ?? null,
    external_document_type: payload.externalDocumentType ?? null,
    lines: payload.lines.map((line) => ({
      notes: line.notes ?? null,
      ordered_quantity: line.orderedQuantity,
      product_id: line.productId,
      unit_cost: line.unitCost,
    })),
    notes: payload.notes ?? null,
    supplier_id: payload.supplierId,
  };
}

function toDirectEntryApiPayload(payload: AdminDirectEntryPayload): ApiDirectEntryPayload {
  return {
    branch_id: payload.branchId,
    document_date: payload.documentDate ?? null,
    external_document_date: payload.externalDocumentDate ?? null,
    external_document_number: payload.externalDocumentNumber ?? null,
    external_document_type: payload.externalDocumentType ?? null,
    lines: payload.lines.map((line) => ({
      notes: line.notes ?? null,
      product_id: line.productId,
      received_quantity: line.receivedQuantity,
      unit_cost: line.unitCost,
    })),
    notes: payload.notes ?? null,
    supplier_id: payload.supplierId,
  };
}

function toReceiptApiPayload(payload: AdminPurchaseReceiptPayload): ApiPurchaseReceiptPayload {
  return {
    lines: payload.lines.map((line) => ({
      discrepancy_reason: line.discrepancyReason ?? null,
      notes: line.notes ?? null,
      purchase_line_id: line.purchaseLineId,
      received_quantity: line.receivedQuantity,
      unit_cost: line.unitCost ?? null,
    })),
    notes: payload.notes ?? null,
  };
}

export function buildAdminPurchasesListPath(filters: AdminPurchaseListFilters): string {
  const params = new URLSearchParams();
  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "amount_max", filters.amountMax);
  appendOptionalParam(params, "amount_min", filters.amountMin);
  appendOptionalParam(params, "branch_id", filters.branchId);
  appendOptionalParam(params, "date_from", filters.dateFrom);
  appendOptionalParam(params, "date_to", filters.dateTo);
  appendOptionalParam(params, "discrepancy_state", filters.discrepancyState);
  appendOptionalParam(params, "operator_user_id", filters.operatorUserId);
  appendOptionalParam(params, "product_id", filters.productId);
  appendOptionalParam(params, "product_kind", filters.productKind);
  appendOptionalParam(params, "search", filters.search?.trim());
  appendOptionalParam(params, "status", filters.status);
  appendOptionalParam(params, "supplier_id", filters.supplierId);
  appendOptionalParam(params, "warning_state", filters.warningState);
  return `/v1/admin/purchases?${params.toString()}`;
}

export function fetchAdminPurchases(
  accessToken: string,
  filters: AdminPurchaseListFilters,
): Promise<AdminPurchaseListResponse> {
  return requestJson<ApiPurchaseListResponse>({
    accessToken,
    path: buildAdminPurchasesListPath(filters),
  }).then(mapPurchaseListFromApi);
}

export function fetchAdminPurchaseDetail(
  accessToken: string,
  purchaseId: string,
): Promise<AdminPurchaseDetail> {
  return requestJson<ApiPurchaseDetail>({
    accessToken,
    path: `/v1/admin/purchases/${purchaseId}`,
  }).then(mapAdminPurchaseDetailFromApi);
}

export function createAdminPurchase(
  accessToken: string,
  payload: AdminPurchasePayload,
): Promise<AdminPurchaseDetail> {
  return requestJson<ApiPurchaseDetail>({
    accessToken,
    body: toPurchaseApiPayload(payload),
    method: "POST",
    path: "/v1/admin/purchases",
  }).then(mapAdminPurchaseDetailFromApi);
}

export function createAdminDirectEntry(
  accessToken: string,
  payload: AdminDirectEntryPayload,
): Promise<AdminPurchaseDetail> {
  return requestJson<ApiPurchaseDetail>({
    accessToken,
    body: toDirectEntryApiPayload(payload),
    method: "POST",
    path: "/v1/admin/purchases/direct-entry",
  }).then(mapAdminPurchaseDetailFromApi);
}

export function confirmAdminPurchase(
  accessToken: string,
  purchaseId: string,
): Promise<AdminPurchaseDetail> {
  return requestJson<ApiPurchaseDetail>({
    accessToken,
    method: "POST",
    path: `/v1/admin/purchases/${purchaseId}/confirm`,
  }).then(mapAdminPurchaseDetailFromApi);
}

export function receiveAdminPurchase(
  accessToken: string,
  purchaseId: string,
  payload: AdminPurchaseReceiptPayload,
): Promise<AdminPurchaseDetail> {
  return requestJson<ApiPurchaseDetail>({
    accessToken,
    body: toReceiptApiPayload(payload),
    method: "POST",
    path: `/v1/admin/purchases/${purchaseId}/receive`,
  }).then(mapAdminPurchaseDetailFromApi);
}

export function cancelAdminPurchase(
  accessToken: string,
  purchaseId: string,
  payload: AdminPurchaseCancelPayload,
): Promise<AdminPurchaseDetail> {
  const body: ApiPurchaseCancelPayload = { reason: payload.reason ?? null };
  return requestJson<ApiPurchaseDetail>({
    accessToken,
    body,
    method: "POST",
    path: `/v1/admin/purchases/${purchaseId}/cancel`,
  }).then(mapAdminPurchaseDetailFromApi);
}
