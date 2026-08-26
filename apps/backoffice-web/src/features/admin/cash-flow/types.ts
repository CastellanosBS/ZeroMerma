export interface AdminCashFlowBackendContract {
  detailEndpoint: string;
  exportEndpoint: string | null;
  listEndpoint: string;
  trendEndpoint: string | null;
}

export interface AdminCashFlowFilterOption {
  id: string;
  label: string;
}

export interface AdminCashFlowFilterOptions {
  branches: AdminCashFlowFilterOption[];
  categories: AdminCashFlowFilterOption[];
  directions: AdminCashFlowFilterOption[];
  operators: AdminCashFlowFilterOption[];
  paymentMethods: AdminCashFlowFilterOption[];
  reconciliationStates: AdminCashFlowFilterOption[];
  sourceTypes: AdminCashFlowFilterOption[];
  workstations: AdminCashFlowFilterOption[];
}

export interface AdminCashFlowSummary {
  cardTotal: string;
  cashTotal: string;
  differenceTotal: string;
  inflowsTotal: string;
  netTotal: string;
  operationalPaymentsTotal: string;
  outflowsTotal: string;
  pendingReconciliationTotal: string;
  refundsTotal: string;
}

export interface AdminCashFlowTrendPoint {
  date: string;
  inflows: string;
  net: string;
  outflows: string;
}

export interface AdminCashFlowListFilters {
  amountMax: string;
  amountMin: string;
  branchId: string;
  category: string;
  dateFrom: string | null;
  dateTo: string | null;
  direction: string;
  operatorId: string;
  page: number;
  pageSize: number;
  paymentMethod: string;
  reconciliationState: string;
  search: string;
  sourceType: string;
  workstationId: string;
}

export interface AdminCashFlowMovementListItem {
  amount: string;
  branchId: string;
  branchName: string;
  category: string | null;
  currency: string;
  direction: string;
  id: string;
  occurredAt: string;
  operatorId: string | null;
  operatorName: string;
  paymentMethod: string;
  reconciliationStatus: string;
  sourceDocumentId: string;
  sourceReference: string;
  sourceType: string;
  warningState: string;
  workstationId: string;
  workstationName: string;
}

export interface AdminCashFlowListResponse {
  backendContract: AdminCashFlowBackendContract;
  filterOptions: AdminCashFlowFilterOptions;
  isBackendConnected: boolean;
  items: AdminCashFlowMovementListItem[];
  page: number;
  pageSize: number;
  summary: AdminCashFlowSummary;
  total: number;
  trend: AdminCashFlowTrendPoint[];
}

export interface AdminCashFlowMovementDetail {
  availableActions: {
    canCopyReference: boolean;
    canExport: boolean;
    canOpenCashCut: boolean;
    canOpenReconciliation: boolean;
    canOpenSource: boolean;
    note: string | null;
  };
  backendContract: AdminCashFlowBackendContract;
  financialClassification: {
    affectsBankSettlement: boolean;
    affectsCashDrawer: boolean;
    cardImpact: string;
    cashImpact: string;
    direction: string;
    netEffect: string;
    note: string | null;
    paymentMethod: string;
    sourceCategory: string | null;
  };
  overview: AdminCashFlowMovementListItem;
  reconciliation: {
    message: string;
    reasonLabel: string | null;
    reconciliationFolio: string | null;
    reconciliationId: string | null;
    routeHint: string | null;
    status: string;
    unresolvedAmount: string | null;
  };
  relatedDocuments: Array<{
    amount: string | null;
    documentType: string;
    folio: string;
    id: string;
    occurredAt: string | null;
    routeHint: string | null;
    status: string;
  }>;
  sourceDocumentContext: {
    cashCutFolio: string | null;
    cashCutId: string | null;
    cashCutRouteHint: string | null;
    cashSessionId: string | null;
    concept: string | null;
    countedCashAmount: string | null;
    differenceAmount: string | null;
    expectedCashAmount: string | null;
    note: string | null;
    originalTicketFolio: string | null;
    sourcePaymentMethod: string | null;
    sourceReference: string;
    sourceRouteHint: string | null;
    sourceStatus: string | null;
    sourceTotalAmount: string | null;
    sourceType: string;
  };
}
