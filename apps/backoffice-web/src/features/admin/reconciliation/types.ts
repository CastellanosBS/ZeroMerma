export interface AdminReconciliationBackendContract {
  createEndpoint: string;
  detailEndpoint: string;
  evidenceEndpoint: string | null;
  exportEndpoint: string | null;
  listEndpoint: string;
  pendingEndpoint: string;
  resolveEndpoint: string;
}

export interface AdminReconciliationFilterOption {
  id: string;
  label: string;
}

export interface AdminReconciliationFilterOptions {
  branches: AdminReconciliationFilterOption[];
  cashiers: AdminReconciliationFilterOption[];
  discrepancyTypes: AdminReconciliationFilterOption[];
  evidenceStates: AdminReconciliationFilterOption[];
  paymentMethods: AdminReconciliationFilterOption[];
  reasonCodes: AdminReconciliationFilterOption[];
  sourceTypes: AdminReconciliationFilterOption[];
  statuses: AdminReconciliationFilterOption[];
  workstations: AdminReconciliationFilterOption[];
}

export interface AdminReconciliationMetrics {
  pendingCount: string;
  reconciledCount: string;
  netDifferenceAmount: string;
  shortageAmount: string;
  overageAmount: string;
  cardTerminalPendingCount: string;
  cashPendingCount: string;
  withEvidenceCount: string;
}

export interface AdminReconciliationListFilters {
  amountMax: string;
  amountMin: string;
  branchId: string;
  cashierId: string;
  dateFrom: string | null;
  dateTo: string | null;
  discrepancyType: string;
  evidenceState: string;
  page: number;
  pageSize: number;
  paymentMethod: string;
  search: string;
  sourceType: string;
  status: string;
  workstationId: string;
}

export interface AdminReconciliationListItem {
  id: string;
  folio: string;
  sourceType: string;
  sourceDocumentId: string;
  sourceReference: string;
  branchId: string;
  branchName: string;
  workstationId: string;
  workstationName: string;
  operatorId: string | null;
  operatorName: string;
  occurredAt: string;
  paymentMethod: string;
  expectedAmount: string;
  actualAmount: string;
  differenceAmount: string;
  differenceDirection: string;
  status: string;
  reasonCode: string | null;
  hasEvidence: boolean;
  warningState: string;
  updatedAt: string;
}

export interface AdminPendingDiscrepancyItem {
  sourceType: string;
  sourceDocumentId: string;
  sourceReference: string;
  branchId: string;
  branchName: string;
  workstationId: string;
  workstationName: string;
  operatorId: string | null;
  operatorName: string;
  paymentMethod: string;
  expectedAmount: string;
  actualAmount: string;
  differenceAmount: string;
  differenceDirection: string;
  occurredAt: string;
  suggestedWarningState: string;
}

export interface AdminReconciliationListResponse {
  backendContract: AdminReconciliationBackendContract;
  filterOptions: AdminReconciliationFilterOptions;
  isBackendConnected: boolean;
  items: AdminReconciliationListItem[];
  metrics: AdminReconciliationMetrics;
  page: number;
  pageSize: number;
  pendingDiscrepancies: AdminPendingDiscrepancyItem[];
  total: number;
}

export interface AdminReconciliationSourceContext {
  sourceType: string;
  sourceReference: string;
  sourceRouteHint: string | null;
  openedAt: string | null;
  closedAt: string | null;
  expectedCashAmount: string | null;
  countedCashAmount: string | null;
  differenceAmount: string | null;
  paymentMethod: string | null;
  terminalReference: string | null;
  externalReportedAmount: string | null;
  operationalPaymentCategory: string | null;
  refundOriginalTicket: string | null;
  note: string | null;
}

export interface AdminReconciliationRelatedDocument {
  id: string;
  documentType: string;
  folio: string;
  status: string;
  amount: string | null;
  occurredAt: string | null;
  routeHint: string | null;
}

export interface AdminReconciliationDetail {
  availableActions: {
    canAttachEvidence: boolean;
    canCopyFolio: boolean;
    canExportReport: boolean;
    canOpenSource: boolean;
    canResolve: boolean;
    canSaveNotes: boolean;
    canVoid: boolean;
    note: string | null;
  };
  backendContract: AdminReconciliationBackendContract;
  differenceBreakdown: {
    actualAmount: string;
    differenceAmount: string;
    direction: string;
    expectedAmount: string;
    paymentMethod: string;
    toleranceNote: string | null;
    toleranceStatus: string;
  };
  evidence: {
    emptyState: string;
    evidenceNote: string | null;
    files: string[];
    hasEvidence: boolean;
    isSupported: boolean;
  };
  explanationReason: {
    notes: string | null;
    reasonCode: string | null;
    reasonLabel: string | null;
    responsibleUserId: string | null;
    responsibleUserName: string | null;
    timestamp: string | null;
  };
  overview: AdminReconciliationListItem & {
    createdAt: string;
    resolvedAt: string | null;
  };
  relatedDocuments: AdminReconciliationRelatedDocument[];
  resolution: {
    canResolve: boolean;
    evidenceSummary: string | null;
    finalNotes: string | null;
    requiredFields: string[];
    resolutionReason: string | null;
    resolvedAt: string | null;
    resolvedByUserId: string | null;
    resolvedByUserName: string | null;
    status: string;
  };
  sourceDocumentContext: AdminReconciliationSourceContext;
}

export interface AdminReconciliationCreatePayload {
  evidenceNote: string | null;
  finalStatus: string;
  notes: string | null;
  reasonCode: string;
  sourceDocumentId: string;
  sourceType: string;
}

export interface AdminReconciliationResolvePayload {
  evidenceNote: string | null;
  notes: string | null;
  reasonCode: string;
}
