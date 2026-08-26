export type AdminReturnsCorrectionsTab = "returns" | "corrections";

export interface AdminReturnCorrectionFilterOption {
  id: string;
  label: string;
}

export interface AdminReturnsBackendContract {
  createEndpoint: string | null;
  detailEndpoint: string;
  listEndpoint: string;
  reprintEndpoint: string | null;
}

export interface AdminCorrectionsBackendContract {
  createEndpoint: string | null;
  detailEndpoint: string;
  listEndpoint: string;
  printEndpoint: string | null;
}

export interface AdminReturnFilterOptions {
  branches: AdminReturnCorrectionFilterOption[];
  operators: AdminReturnCorrectionFilterOption[];
  refundMethods: AdminReturnCorrectionFilterOption[];
  statuses: AdminReturnCorrectionFilterOption[];
}

export interface AdminCorrectionFilterOptions {
  branches: AdminReturnCorrectionFilterOption[];
  correctionTypes: AdminReturnCorrectionFilterOption[];
  operators: AdminReturnCorrectionFilterOption[];
  reasons: AdminReturnCorrectionFilterOption[];
  statuses: AdminReturnCorrectionFilterOption[];
  targetDocumentTypes: AdminReturnCorrectionFilterOption[];
}

export interface AdminReturnListFilters {
  branchId?: string | null;
  dateFrom?: string | null;
  dateTo?: string | null;
  maxAmount?: string | null;
  minAmount?: string | null;
  operatorId?: string | null;
  page: number;
  pageSize: number;
  refundMethod?: string | null;
  search?: string;
  status?: string | null;
}

export interface AdminCorrectionListFilters {
  branchId?: string | null;
  correctionType?: string | null;
  dateFrom?: string | null;
  dateTo?: string | null;
  netEffect?: string | null;
  operatorId?: string | null;
  page: number;
  pageSize: number;
  reasonCode?: string | null;
  search?: string;
  status?: string | null;
  targetDocumentType?: string | null;
}

export interface AdminReturnMetrics {
  cashRefundedAmount: string;
  pendingReviewCount: number;
  refundedAmount: string;
  returnedLineCount: number;
  returnsCount: number;
}

export interface AdminCorrectionMetrics {
  correctionsCount: number;
  negativeEffectCount: number;
  pendingReviewCount: number;
  positiveEffectCount: number;
  totalUnitsAffected: string;
}

export interface AdminReturnListItem {
  branchId: string;
  branchName: string;
  createdAt: string;
  folio: string;
  id: string;
  operatorId: string;
  operatorName: string;
  originalSaleId: string;
  originalTicketFolio: string;
  refundedAmount: string;
  refundMethod: string;
  returnedLineCount: number;
  status: string;
  warningState: string | null;
  workstationCode: string;
  workstationId: string;
  workstationName: string;
}

export interface AdminCorrectionListItem {
  branchId: string;
  branchName: string;
  correctionType: string;
  createdAt: string;
  folio: string;
  id: string;
  lineCount: number;
  netEffect: string;
  netEffectQuantity: string;
  operatorId: string;
  operatorName: string;
  originalDocumentFolio: string;
  originalDocumentId: string;
  originalDocumentType: string;
  reasonCode: string;
  reasonName: string;
  status: string;
  totalUnitsAffected: string;
  warningState: string | null;
  workstationCode: string;
  workstationId: string;
  workstationName: string;
}

export interface AdminReturnsListResponse {
  backendContract: AdminReturnsBackendContract;
  filterOptions: AdminReturnFilterOptions;
  isBackendConnected: boolean;
  items: AdminReturnListItem[];
  metrics: AdminReturnMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminCorrectionsListResponse {
  backendContract: AdminCorrectionsBackendContract;
  filterOptions: AdminCorrectionFilterOptions;
  isBackendConnected: boolean;
  items: AdminCorrectionListItem[];
  metrics: AdminCorrectionMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminReturnDetail {
  auditSummary: unknown | null;
  availableActions: {
    canCreateFromBackoffice: boolean;
    canOpenOriginalTicket: boolean;
    canReprint: boolean;
    creationNote: string;
  };
  backendContract: AdminReturnsBackendContract;
  originalTicket: {
    branchName: string;
    cashSessionId: string;
    cashierName: string;
    folio: string;
    paymentMethodsLabel: string;
    saleDate: string;
    saleId: string;
    status: string;
    totalAmount: string;
    workstationName: string;
  };
  overview: {
    branchId: string;
    branchName: string;
    createdAt: string;
    folio: string;
    id: string;
    isPartialReturn: boolean;
    notes: string | null;
    operatorId: string;
    operatorName: string;
    reasonCode: string;
    reasonName: string;
    refundMethod: string;
    status: string;
    totalRefundAmount: string;
    workstationCode: string;
    workstationId: string;
    workstationName: string;
  };
  refundImpact: {
    cashImpactAmount: string;
    cashSessionId: string;
    currencyCode: string;
    linkedCashMovementId: string | null;
    refundAmount: string;
    refundMethod: string;
  };
  relatedDocuments: AdminRelatedDocument[];
  returnedLines: AdminReturnedLine[];
}

export interface AdminReturnedLine {
  dispositionCode: string;
  id: string;
  lineStatus: string;
  originalQuantity: string;
  originalSaleLineId: string;
  productClassCode: string;
  productClassName: string;
  productCode: string;
  productName: string;
  refundAmount: string;
  returnedQuantity: string;
  unitPrice: string;
}

export interface AdminCorrectionDetail {
  affectedLines: AdminCorrectionAffectedLine[];
  availableActions: {
    canCreateFromBackoffice: boolean;
    canOpenOriginalDocument: boolean;
    canPrint: boolean;
    creationNote: string;
  };
  backendContract: AdminCorrectionsBackendContract;
  netEffect: {
    cashEffect: string;
    inventoryEffect: string;
    netEffect: string;
    totalAmountAffected: string | null;
    totalUnitsAffected: string;
  };
  originalDocument: {
    branchName: string;
    documentType: string;
    folio: string;
    id: string;
    occurredAt: string | null;
    operatorName: string;
    routeHint: string | null;
    status: string;
    workstationName: string;
  };
  overview: {
    branchId: string;
    branchName: string;
    committedAt: string | null;
    correctionType: string;
    createdAt: string;
    folio: string;
    id: string;
    netEffect: string;
    netEffectQuantity: string;
    operatorId: string;
    operatorName: string;
    originalDocumentFolio: string;
    originalDocumentId: string;
    originalDocumentType: string;
    status: string;
    totalUnitsAffected: string;
    workstationCode: string;
    workstationId: string;
    workstationName: string;
  };
  reasonNotes: {
    auditSummary: unknown | null;
    notes: string | null;
    reasonCode: string;
    reasonName: string;
  };
  relatedDocuments: AdminRelatedDocument[];
}

export interface AdminCorrectionAffectedLine {
  correctedQuantity: string | null;
  differenceQuantity: string;
  id: string;
  notes: string | null;
  originalQuantity: string | null;
  productClassCode: string;
  productClassName: string;
  productCode: string;
  productName: string;
  targetLineId: string | null;
  unitOfMeasureCode: string;
}

export interface AdminRelatedDocument {
  amount?: string | null;
  documentType: string;
  folio: string;
  id: string;
  occurredAt: string | null;
  routeHint: string | null;
  status: string;
}
