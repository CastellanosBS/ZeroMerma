export type AdminTransferStatus = "DRAFT" | "IN_TRANSIT" | "RECEIVED" | "RECEIVED_WITH_VARIANCE" | "CANCELLED";
export type AdminTransferWarningSeverity = "info" | "warning" | "critical";
export type AdminTransferDiscrepancyState = "with_discrepancy" | "without_discrepancy";
export type AdminTransferProductKind = "FINISHED_GOOD" | "RAW_MATERIAL" | "CONSUMABLE" | "DISPOSABLE" | string;

export interface AdminTransferFilterOption {
  id: string;
  label: string;
}

export interface AdminTransferWarning {
  code: string;
  message: string;
  severity: AdminTransferWarningSeverity;
}

export interface AdminTransferBackendContract {
  cancelEndpoint: string;
  createEndpoint: string;
  detailEndpoint: string;
  dispatchEndpoint: string;
  listEndpoint: string;
  receiveEndpoint: string;
  updateEndpoint: string;
}

export interface AdminTransferMetrics {
  cancelledTransfers: string;
  inTransitTransfers: string;
  pendingReceiptTransfers: string;
  receivedTransfers: string;
  totalTransfers: string;
  unitsInTransit: string;
  withDiscrepancies: string;
}

export interface AdminTransferFilterOptions {
  branches: AdminTransferFilterOption[];
  operators: AdminTransferFilterOption[];
  products: AdminTransferFilterOption[];
  statuses: AdminTransferFilterOption[];
}

export interface AdminTransferListItem {
  createdAt: string;
  destinationBranchCode: string;
  destinationBranchId: string;
  destinationBranchName: string;
  dispatchedAt?: string | null;
  folio: string;
  hasDiscrepancy: boolean;
  id: string;
  lineCount: number;
  operatorName: string;
  originBranchCode: string;
  originBranchId: string;
  originBranchName: string;
  receivedAt?: string | null;
  receivedUnitCount?: string | null;
  requestedUnitCount: string;
  sentUnitCount: string;
  status: AdminTransferStatus;
  warningState?: AdminTransferWarningSeverity | null;
  warnings: AdminTransferWarning[];
}

export interface AdminTransferListFilters {
  dateFrom?: string | null;
  dateTo?: string | null;
  destinationBranchId?: string | null;
  discrepancyState?: AdminTransferDiscrepancyState | "all";
  operatorUserId?: string | null;
  originBranchId?: string | null;
  page: number;
  pageSize: number;
  productId?: string | null;
  search?: string;
  status?: AdminTransferStatus | "all";
}

export interface AdminTransferListResponse {
  backendContract: AdminTransferBackendContract;
  filterOptions: AdminTransferFilterOptions;
  isBackendConnected: boolean;
  items: AdminTransferListItem[];
  metrics: AdminTransferMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminTransferBranch {
  branchCode: string;
  branchId: string;
  branchIsActive: boolean;
  branchName: string;
  timezone: string;
}

export interface AdminTransferLine {
  difference?: string | null;
  lineStatus: string;
  notes?: string | null;
  productCode: string;
  productId: string;
  productKind: AdminTransferProductKind;
  productName: string;
  receivedQuantity?: string | null;
  requestedQuantity: string;
  sentQuantity: string;
  shipmentLineId: string;
  unitOfMeasure: string;
  varianceReason?: string | null;
}

export interface AdminTransferInventoryMovement {
  balanceAfter?: string | null;
  branchId: string;
  direction: string;
  id: string;
  locationCode: string;
  movementType: string;
  productId: string;
  quantity: string;
  sourceDocumentId?: string | null;
  sourceDocumentType?: string | null;
  unitOfMeasure: string;
}

export interface AdminTransferInventoryImpact {
  integrationAvailable: boolean;
  movements: AdminTransferInventoryMovement[];
  notes?: string | null;
}

export interface AdminTransferOverview {
  createdAt: string;
  createdByUserId: string;
  createdByUserName: string;
  dispatchedAt?: string | null;
  folio: string;
  hasDiscrepancy: boolean;
  id: string;
  lineCount: number;
  notes?: string | null;
  receivedAt?: string | null;
  receivedByUserId?: string | null;
  receivedByUserName?: string | null;
  receivedUnitCount?: string | null;
  requestedUnitCount: string;
  sentUnitCount: string;
  status: AdminTransferStatus;
}

export interface AdminTransferReceipt {
  difference?: string | null;
  discrepancyReasonRequired: boolean;
  expectedTotalQuantity: string;
  hasDiscrepancy: boolean;
  receiptDocumentId?: string | null;
  receivedTotalQuantity?: string | null;
  state: string;
}

export interface AdminTransferRelatedDocument {
  documentId: string;
  documentType: string;
  folio: string;
  status: string;
}

export interface AdminTransferAvailableActions {
  canCancel: boolean;
  canDispatch: boolean;
  canEdit: boolean;
  canReceive: boolean;
  canViewMovements: boolean;
}

export interface AdminTransferDetail {
  availableActions: AdminTransferAvailableActions;
  destination: AdminTransferBranch;
  inventoryImpact: AdminTransferInventoryImpact;
  lines: AdminTransferLine[];
  origin: AdminTransferBranch;
  overview: AdminTransferOverview;
  receipt: AdminTransferReceipt;
  relatedDocuments: AdminTransferRelatedDocument[];
  warnings: AdminTransferWarning[];
}

export interface AdminTransferLinePayload {
  notes?: string | null;
  productId: string;
  quantity: string;
}

export interface AdminTransferCreatePayload {
  destinationBranchId: string;
  lines: AdminTransferLinePayload[];
  notes?: string | null;
  originBranchId: string;
}

export interface AdminTransferUpdatePayload {
  destinationBranchId?: string | null;
  lines?: AdminTransferLinePayload[] | null;
  notes?: string | null;
  originBranchId?: string | null;
}

export interface AdminTransferReceiveLinePayload {
  notes?: string | null;
  receivedQuantity: string;
  shipmentLineId: string;
  varianceReason?: string | null;
}

export interface AdminTransferReceivePayload {
  lines: AdminTransferReceiveLinePayload[];
  notes?: string | null;
}
