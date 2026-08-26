export type AdminPurchaseStatus = "DRAFT" | "ORDERED" | "PARTIALLY_RECEIVED" | "RECEIVED" | "CANCELLED";
export type AdminPurchaseType = "PURCHASE" | "DIRECT_ENTRY";
export type AdminPurchaseWarningSeverity = "info" | "warning" | "critical";

export interface AdminPurchaseFilterOption {
  id: string;
  label: string;
}

export interface AdminPurchaseBackendContract {
  cancelEndpoint: string;
  confirmEndpoint: string;
  createDirectEntryEndpoint: string;
  createEndpoint: string;
  detailEndpoint: string;
  listEndpoint: string;
  receiveEndpoint: string;
  updateEndpoint: string;
}

export interface AdminPurchaseFilterOptions {
  branches: AdminPurchaseFilterOption[];
  operators: AdminPurchaseFilterOption[];
  productKinds: AdminPurchaseFilterOption[];
  products: AdminPurchaseFilterOption[];
  statuses: AdminPurchaseFilterOption[];
  suppliers: AdminPurchaseFilterOption[];
}

export interface AdminPurchaseMetrics {
  activeSuppliersUsed: string;
  confirmedEntries: string;
  partiallyReceived: string;
  pendingReceipt: string;
  totalAmount: string;
  totalDocuments: string;
  withDiscrepancies: string;
}

export interface AdminPurchaseWarning {
  code: string;
  message: string;
  severity: AdminPurchaseWarningSeverity;
}

export interface AdminPurchaseListFilters {
  amountMax?: string | null;
  amountMin?: string | null;
  branchId?: string | null;
  dateFrom?: string | null;
  dateTo?: string | null;
  discrepancyState?: "all" | "with_discrepancy" | "without_discrepancy";
  operatorUserId?: string | null;
  page: number;
  pageSize: number;
  productId?: string | null;
  productKind?: string | "all";
  search?: string;
  status?: AdminPurchaseStatus | "all";
  supplierId?: string | null;
  warningState?: "all" | "with_warnings" | "without_warnings" | AdminPurchaseWarningSeverity;
}

export interface AdminPurchaseListItem {
  branchId: string;
  branchName: string;
  createdAt: string;
  documentDate: string;
  documentType: AdminPurchaseType;
  externalDocumentNumber?: string | null;
  folio: string;
  hasDiscrepancy: boolean;
  id: string;
  lineCount: number;
  operatorName: string;
  receivedAt?: string | null;
  receivedUnitCount: string;
  status: AdminPurchaseStatus;
  supplierId: string;
  supplierName: string;
  totalAmount: string;
  warningState?: AdminPurchaseWarningSeverity | null;
  warnings: AdminPurchaseWarning[];
}

export interface AdminPurchaseListResponse {
  backendContract: AdminPurchaseBackendContract;
  filterOptions: AdminPurchaseFilterOptions;
  isBackendConnected: boolean;
  items: AdminPurchaseListItem[];
  metrics: AdminPurchaseMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminPurchaseOverview {
  branchId: string;
  branchName: string;
  confirmedAt?: string | null;
  createdAt: string;
  createdByUserId: string;
  createdByUserName: string;
  documentDate: string;
  documentType: AdminPurchaseType;
  externalDocumentNumber?: string | null;
  externalDocumentType?: string | null;
  folio: string;
  hasDiscrepancy: boolean;
  id: string;
  lineCount: number;
  notes?: string | null;
  receivedAt?: string | null;
  receivedUnitCount: string;
  status: AdminPurchaseStatus;
  supplierId: string;
  supplierName: string;
  totalAmount: string;
  warningState?: AdminPurchaseWarningSeverity | null;
}

export interface AdminPurchaseSupplierContext {
  commercialName?: string | null;
  leadTimeDays: number;
  paymentTermsSummary: string;
  primaryContact?: string | null;
  status: string;
  supplierId: string;
  supplierName: string;
}

export interface AdminPurchaseBranch {
  branchCode: string;
  branchId: string;
  branchIsActive: boolean;
  branchName: string;
  timezone: string;
}

export interface AdminPurchaseLine {
  discrepancy: string;
  discrepancyReason?: string | null;
  lineStatus: string;
  lineTotal: string;
  notes?: string | null;
  orderedQuantity: string;
  pendingQuantity: string;
  productCode: string;
  productId: string;
  productKind: string;
  productName: string;
  purchaseLineId: string;
  receivedQuantity: string;
  standardCost?: string | null;
  supplierLastKnownPrice?: string | null;
  unitCost: string;
  unitOfMeasure: string;
}

export interface AdminPurchaseReceiptSummary {
  expectedQuantity: string;
  hasDiscrepancy: boolean;
  pendingQuantity: string;
  receiptCount: number;
  receivedQuantity: string;
  state: string;
}

export interface AdminPurchaseCostSummary {
  currency: string;
  receivedTotal: string;
  subtotal: string;
  taxes?: string | null;
  total: string;
}

export interface AdminPurchaseInventoryMovement {
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

export interface AdminPurchaseInventoryImpact {
  integrationAvailable: boolean;
  movements: AdminPurchaseInventoryMovement[];
  notes?: string | null;
}

export interface AdminPurchaseRelatedDocument {
  documentId: string;
  documentType: string;
  folio: string;
  status: string;
}

export interface AdminPurchaseAvailableActions {
  canCancel: boolean;
  canConfirm: boolean;
  canEdit: boolean;
  canReceive: boolean;
  canViewMovements: boolean;
}

export interface AdminPurchaseDetail {
  availableActions: AdminPurchaseAvailableActions;
  costSummary: AdminPurchaseCostSummary;
  inventoryImpact: AdminPurchaseInventoryImpact;
  lines: AdminPurchaseLine[];
  overview: AdminPurchaseOverview;
  receipt: AdminPurchaseReceiptSummary;
  receivingBranch: AdminPurchaseBranch;
  relatedDocuments: AdminPurchaseRelatedDocument[];
  supplierContext: AdminPurchaseSupplierContext;
  warnings: AdminPurchaseWarning[];
}

export interface AdminPurchaseLinePayload {
  notes?: string | null;
  orderedQuantity: string;
  productId: string;
  unitCost: string;
}

export interface AdminPurchasePayload {
  branchId: string;
  confirmNow?: boolean;
  documentDate?: string | null;
  externalDocumentDate?: string | null;
  externalDocumentNumber?: string | null;
  externalDocumentType?: string | null;
  lines: AdminPurchaseLinePayload[];
  notes?: string | null;
  supplierId: string;
}

export interface AdminDirectEntryLinePayload {
  notes?: string | null;
  productId: string;
  receivedQuantity: string;
  unitCost: string;
}

export interface AdminDirectEntryPayload {
  branchId: string;
  documentDate?: string | null;
  externalDocumentDate?: string | null;
  externalDocumentNumber?: string | null;
  externalDocumentType?: string | null;
  lines: AdminDirectEntryLinePayload[];
  notes?: string | null;
  supplierId: string;
}

export interface AdminPurchaseReceiptLinePayload {
  discrepancyReason?: string | null;
  notes?: string | null;
  purchaseLineId: string;
  receivedQuantity: string;
  unitCost?: string | null;
}

export interface AdminPurchaseReceiptPayload {
  lines: AdminPurchaseReceiptLinePayload[];
  notes?: string | null;
}

export interface AdminPurchaseCancelPayload {
  reason?: string | null;
}
