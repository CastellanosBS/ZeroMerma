import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminTransferBackendContract,
  AdminTransferBranch,
  AdminTransferCreatePayload,
  AdminTransferDetail,
  AdminTransferFilterOption,
  AdminTransferListFilters,
  AdminTransferListItem,
  AdminTransferListResponse,
  AdminTransferReceivePayload,
  AdminTransferUpdatePayload,
  AdminTransferWarning,
} from "./types";

export const adminTransferBackendContract: AdminTransferBackendContract = {
  cancelEndpoint: "POST /v1/admin/transfers/{transfer_id}/cancel",
  createEndpoint: "POST /v1/admin/transfers",
  detailEndpoint: "GET /v1/admin/transfers/{transfer_id}",
  dispatchEndpoint: "POST /v1/admin/transfers/{transfer_id}/dispatch",
  listEndpoint: "GET /v1/admin/transfers",
  receiveEndpoint: "POST /v1/admin/transfers/{transfer_id}/receive",
  updateEndpoint: "PATCH /v1/admin/transfers/{transfer_id}",
};

type ApiTransferBackendContract = components["schemas"]["AdminTransferBackendContractView"];
type ApiTransferFilterOption = components["schemas"]["AdminTransferFilterOptionView"];
type ApiTransferWarning = components["schemas"]["AdminTransferWarningView"];
type ApiTransferListItem = components["schemas"]["AdminTransferListItemView"];
type ApiTransferListResponse = components["schemas"]["AdminTransferListResponse"];
type ApiTransferDetail = components["schemas"]["AdminTransferDetailView"];
type ApiTransferCreatePayload = components["schemas"]["AdminTransferCreateRequest"];
type ApiTransferUpdatePayload = components["schemas"]["AdminTransferUpdateRequest"];
type ApiTransferReceivePayload = components["schemas"]["AdminTransferReceiveRequest"];

function appendOptionalParam(params: URLSearchParams, key: string, value: string | null | undefined) {
  if (!value || value === "all") {
    return;
  }

  params.set(key, value);
}

function mapFilterOptions(options: ApiTransferFilterOption[]): AdminTransferFilterOption[] {
  return options.map((option) => ({
    id: String(option.id),
    label: option.label,
  }));
}

function mapMetric(value: number | string | null | undefined): string {
  if (value === null || value === undefined) {
    return "No disponible";
  }

  return String(value);
}

function mapBackendContract(contract?: ApiTransferBackendContract): AdminTransferBackendContract {
  if (!contract) {
    return adminTransferBackendContract;
  }

  return {
    cancelEndpoint: contract.cancel_endpoint,
    createEndpoint: contract.create_endpoint,
    detailEndpoint: contract.detail_endpoint,
    dispatchEndpoint: contract.dispatch_endpoint,
    listEndpoint: contract.list_endpoint,
    receiveEndpoint: contract.receive_endpoint,
    updateEndpoint: contract.update_endpoint,
  };
}

function mapWarningFromApi(warning: ApiTransferWarning): AdminTransferWarning {
  return {
    code: warning.code,
    message: warning.message,
    severity: warning.severity,
  };
}

function mapBranchFromApi(branch: ApiTransferDetail["origin"]): AdminTransferBranch {
  return {
    branchCode: branch.branch_code,
    branchId: branch.branch_id,
    branchIsActive: branch.branch_is_active,
    branchName: branch.branch_name,
    timezone: branch.timezone,
  };
}

export function mapAdminTransferListItemFromApi(item: ApiTransferListItem): AdminTransferListItem {
  return {
    createdAt: item.created_at,
    destinationBranchCode: item.destination_branch_code,
    destinationBranchId: item.destination_branch_id,
    destinationBranchName: item.destination_branch_name,
    dispatchedAt: item.dispatched_at ?? null,
    folio: item.folio,
    hasDiscrepancy: item.has_discrepancy,
    id: item.id,
    lineCount: item.line_count,
    operatorName: item.operator_name,
    originBranchCode: item.origin_branch_code,
    originBranchId: item.origin_branch_id,
    originBranchName: item.origin_branch_name,
    receivedAt: item.received_at ?? null,
    receivedUnitCount: item.received_unit_count ?? null,
    requestedUnitCount: item.requested_unit_count,
    sentUnitCount: item.sent_unit_count,
    status: item.status,
    warningState: item.warning_state ?? null,
    warnings: item.warnings.map(mapWarningFromApi),
  };
}

export function mapAdminTransferDetailFromApi(item: ApiTransferDetail): AdminTransferDetail {
  return {
    availableActions: {
      canCancel: item.available_actions.can_cancel,
      canDispatch: item.available_actions.can_dispatch,
      canEdit: item.available_actions.can_edit,
      canReceive: item.available_actions.can_receive,
      canViewMovements: item.available_actions.can_view_movements,
    },
    destination: mapBranchFromApi(item.destination),
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
    lines: item.lines.map((line) => ({
      difference: line.difference ?? null,
      lineStatus: line.line_status,
      notes: line.notes ?? null,
      productCode: line.product_code,
      productId: line.product_id,
      productKind: line.product_kind,
      productName: line.product_name,
      receivedQuantity: line.received_quantity ?? null,
      requestedQuantity: line.requested_quantity,
      sentQuantity: line.sent_quantity,
      shipmentLineId: line.shipment_line_id,
      unitOfMeasure: line.unit_of_measure,
      varianceReason: line.variance_reason ?? null,
    })),
    origin: mapBranchFromApi(item.origin),
    overview: {
      createdAt: item.overview.created_at,
      createdByUserId: item.overview.created_by_user_id,
      createdByUserName: item.overview.created_by_user_name,
      dispatchedAt: item.overview.dispatched_at ?? null,
      folio: item.overview.folio,
      hasDiscrepancy: item.overview.has_discrepancy,
      id: item.overview.id,
      lineCount: item.overview.line_count,
      notes: item.overview.notes ?? null,
      receivedAt: item.overview.received_at ?? null,
      receivedByUserId: item.overview.received_by_user_id ?? null,
      receivedByUserName: item.overview.received_by_user_name ?? null,
      receivedUnitCount: item.overview.received_unit_count ?? null,
      requestedUnitCount: item.overview.requested_unit_count,
      sentUnitCount: item.overview.sent_unit_count,
      status: item.overview.status,
    },
    receipt: {
      difference: item.receipt.difference ?? null,
      discrepancyReasonRequired: item.receipt.discrepancy_reason_required,
      expectedTotalQuantity: item.receipt.expected_total_quantity,
      hasDiscrepancy: item.receipt.has_discrepancy,
      receiptDocumentId: item.receipt.receipt_document_id ?? null,
      receivedTotalQuantity: item.receipt.received_total_quantity ?? null,
      state: item.receipt.state,
    },
    relatedDocuments: item.related_documents.map((document) => ({
      documentId: document.document_id,
      documentType: document.document_type,
      folio: document.folio,
      status: document.status,
    })),
    warnings: item.warnings.map(mapWarningFromApi),
  };
}

function mapTransferListFromApi(response: ApiTransferListResponse): AdminTransferListResponse {
  return {
    backendContract: mapBackendContract(response.backend_contract),
    filterOptions: {
      branches: mapFilterOptions(response.filter_options.branches),
      operators: mapFilterOptions(response.filter_options.operators),
      products: mapFilterOptions(response.filter_options.products),
      statuses: mapFilterOptions(response.filter_options.statuses),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminTransferListItemFromApi),
    metrics: {
      cancelledTransfers: mapMetric(response.metrics.cancelled_transfers),
      inTransitTransfers: mapMetric(response.metrics.in_transit_transfers),
      pendingReceiptTransfers: mapMetric(response.metrics.pending_receipt_transfers),
      receivedTransfers: mapMetric(response.metrics.received_transfers),
      totalTransfers: mapMetric(response.metrics.total_transfers),
      unitsInTransit: mapMetric(response.metrics.units_in_transit),
      withDiscrepancies: mapMetric(response.metrics.with_discrepancies),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function toCreateApiPayload(payload: AdminTransferCreatePayload): ApiTransferCreatePayload {
  return {
    destination_branch_id: payload.destinationBranchId,
    lines: payload.lines.map((line) => ({
      notes: line.notes ?? null,
      product_id: line.productId,
      quantity: line.quantity,
    })),
    notes: payload.notes ?? null,
    origin_branch_id: payload.originBranchId,
  };
}

function toUpdateApiPayload(payload: AdminTransferUpdatePayload): ApiTransferUpdatePayload {
  return {
    destination_branch_id: payload.destinationBranchId ?? null,
    lines: payload.lines?.map((line) => ({
      notes: line.notes ?? null,
      product_id: line.productId,
      quantity: line.quantity,
    })) ?? null,
    notes: payload.notes ?? null,
    origin_branch_id: payload.originBranchId ?? null,
  };
}

function toReceiveApiPayload(payload: AdminTransferReceivePayload): ApiTransferReceivePayload {
  return {
    lines: payload.lines.map((line) => ({
      notes: line.notes ?? null,
      received_quantity: line.receivedQuantity,
      shipment_line_id: line.shipmentLineId,
      variance_reason: line.varianceReason ?? null,
    })),
    notes: payload.notes ?? null,
  };
}

export function buildAdminTransferListPath(filters: AdminTransferListFilters): string {
  const params = new URLSearchParams();

  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "date_from", filters.dateFrom);
  appendOptionalParam(params, "date_to", filters.dateTo);
  appendOptionalParam(params, "destination_branch_id", filters.destinationBranchId);
  appendOptionalParam(params, "discrepancy_state", filters.discrepancyState);
  appendOptionalParam(params, "operator_user_id", filters.operatorUserId);
  appendOptionalParam(params, "origin_branch_id", filters.originBranchId);
  appendOptionalParam(params, "product_id", filters.productId);
  appendOptionalParam(params, "search", filters.search?.trim());
  appendOptionalParam(params, "status", filters.status);

  return `/v1/admin/transfers?${params.toString()}`;
}

export function fetchAdminTransfers(
  accessToken: string,
  filters: AdminTransferListFilters,
): Promise<AdminTransferListResponse> {
  return requestJson<ApiTransferListResponse>({
    accessToken,
    path: buildAdminTransferListPath(filters),
  }).then(mapTransferListFromApi);
}

export function fetchAdminTransferDetail(accessToken: string, transferId: string): Promise<AdminTransferDetail> {
  return requestJson<ApiTransferDetail>({
    accessToken,
    path: `/v1/admin/transfers/${transferId}`,
  }).then(mapAdminTransferDetailFromApi);
}

export function createAdminTransfer(
  accessToken: string,
  payload: AdminTransferCreatePayload,
): Promise<AdminTransferDetail> {
  return requestJson<ApiTransferDetail>({
    accessToken,
    body: toCreateApiPayload(payload),
    method: "POST",
    path: "/v1/admin/transfers",
  }).then(mapAdminTransferDetailFromApi);
}

export function updateAdminTransfer(
  accessToken: string,
  transferId: string,
  payload: AdminTransferUpdatePayload,
): Promise<AdminTransferDetail> {
  return requestJson<ApiTransferDetail>({
    accessToken,
    body: toUpdateApiPayload(payload),
    method: "PATCH",
    path: `/v1/admin/transfers/${transferId}`,
  }).then(mapAdminTransferDetailFromApi);
}

export function dispatchAdminTransfer(
  accessToken: string,
  transferId: string,
  notes?: string | null,
): Promise<AdminTransferDetail> {
  return requestJson<ApiTransferDetail>({
    accessToken,
    body: { notes: notes ?? null },
    method: "POST",
    path: `/v1/admin/transfers/${transferId}/dispatch`,
  }).then(mapAdminTransferDetailFromApi);
}

export function receiveAdminTransfer(
  accessToken: string,
  transferId: string,
  payload: AdminTransferReceivePayload,
): Promise<AdminTransferDetail> {
  return requestJson<ApiTransferDetail>({
    accessToken,
    body: toReceiveApiPayload(payload),
    method: "POST",
    path: `/v1/admin/transfers/${transferId}/receive`,
  }).then(mapAdminTransferDetailFromApi);
}

export function cancelAdminTransfer(
  accessToken: string,
  transferId: string,
  reason?: string | null,
): Promise<AdminTransferDetail> {
  return requestJson<ApiTransferDetail>({
    accessToken,
    body: { reason: reason ?? null },
    method: "POST",
    path: `/v1/admin/transfers/${transferId}/cancel`,
  }).then(mapAdminTransferDetailFromApi);
}
