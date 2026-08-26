export interface AdminCashCutBackendContract {
  detailEndpoint: string;
  exportEndpoint: string | null;
  listEndpoint: string;
  printEndpoint: string | null;
}

export interface AdminCashCutFilterOption {
  id: string;
  label: string;
}

export interface AdminCashCutFilterOptions {
  branches: AdminCashCutFilterOption[];
  cashiers: AdminCashCutFilterOption[];
  differenceStates: AdminCashCutFilterOption[];
  paymentMethods: AdminCashCutFilterOption[];
  statuses: AdminCashCutFilterOption[];
  workstations: AdminCashCutFilterOption[];
}

export interface AdminCashCutMetrics {
  closedCutsCount: string;
  netSalesAmount: string;
  expectedCashAmount: string;
  countedCashAmount: string;
  netDifferenceAmount: string;
  cutsWithDifferenceCount: string;
  pendingCloseCount: string;
  operationalPaymentsAmount: string;
}

export interface AdminCashCutListItem {
  id: string;
  folio: string;
  cashSessionId: string;
  closeId: string | null;
  openedAt: string;
  closedAt: string | null;
  branchId: string;
  branchName: string;
  workstationId: string;
  workstationCode: string;
  workstationName: string;
  cashierId: string;
  cashierName: string;
  openingAmount: string;
  expectedCashAmount: string;
  countedCashAmount: string | null;
  differenceAmount: string | null;
  totalSalesAmount: string;
  paymentMethodsSummary: string;
  status: string;
  differenceState: string;
  warningState: string;
  warningCount: number;
  hasRefunds: boolean;
  hasOperationalPayments: boolean;
}

export interface AdminCashCutsListResponse {
  backendContract: AdminCashCutBackendContract;
  filterOptions: AdminCashCutFilterOptions;
  isBackendConnected: boolean;
  items: AdminCashCutListItem[];
  metrics: AdminCashCutMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminCashCutListFilters {
  branchId: string;
  cashierId: string;
  dateFrom: string | null;
  dateTo: string | null;
  differenceState: string;
  hasOperationalPayments: string;
  hasRefunds: string;
  page: number;
  pageSize: number;
  paymentMethod: string;
  search: string;
  status: string;
  workstationId: string;
}

export interface AdminCashCutOverview {
  id: string;
  folio: string;
  cashSessionId: string;
  closeId: string | null;
  status: string;
  branchId: string;
  branchName: string;
  branchCode: string;
  workstationId: string;
  workstationCode: string;
  workstationName: string;
  cashierId: string;
  cashierName: string;
  openedAt: string;
  closedAt: string | null;
  openingAmount: string;
  closingNotes: string | null;
  totalDurationMinutes: number | null;
  warningState: string;
}

export interface AdminCashCutExpectedVsCounted {
  openingAmount: string;
  cashSalesAmount: string;
  cashRefundsAmount: string;
  cashOperationalPaymentsAmount: string;
  cashOperationalDiscountsAmount: string;
  cashAdjustmentsAmount: string;
  expectedCashAmount: string;
  countedCashAmount: string | null;
  differenceAmount: string | null;
  differenceState: string;
  isCountedCashAvailable: boolean;
  note: string | null;
}

export interface AdminCashCutPaymentBreakdown {
  paymentMethodCode: string;
  currencyCode: string;
  salesAmount: string;
  refundAmount: string;
  operationalPaymentAmount: string;
  operationalDiscountAmount: string;
  expectedAmount: string | null;
  countedAmount: string | null;
  varianceAmount: string | null;
  netAmount: string;
  isCountedSupported: boolean;
}

export interface AdminCashCutTicketItem {
  ticketId: string;
  folio: string;
  occurredAt: string;
  totalAmount: string;
  currencyCode: string;
  paymentMethodSummary: string;
  cashierName: string;
  status: string;
  routeHint: string;
}

export interface AdminCashCutRefundItem {
  id: string;
  folio: string;
  originalTicketFolio: string;
  amount: string;
  paymentMethodCode: string;
  occurredAt: string;
  operatorName: string;
  reasonName: string;
  status: string;
  routeHint: string;
}

export interface AdminCashCutOperationalPaymentItem {
  id: string;
  folio: string;
  categoryCode: string | null;
  categoryName: string | null;
  amount: string;
  cashAmount: string;
  paymentMethodCode: string;
  occurredAt: string;
  operatorName: string;
  notes: string | null;
  routeHint: string;
}

export interface AdminCashCutCorrectionAdjustmentItem {
  id: string;
  folio: string;
  documentType: string;
  amount: string | null;
  occurredAt: string | null;
  operatorName: string | null;
  notes: string | null;
  routeHint: string | null;
}

export interface AdminCashCutRelatedDocument {
  id: string;
  documentType: string;
  folio: string;
  status: string;
  amount: string | null;
  occurredAt: string | null;
  routeHint: string | null;
}

export interface AdminCashCutTimelineItem {
  eventCode: string;
  label: string;
  occurredAt: string;
  actorName: string | null;
  summary: string | null;
}

export interface AdminCashCutDetail {
  availableActions: {
    canCopyFolio: boolean;
    canExportReport: boolean;
    canPrintReport: boolean;
    canOpenTickets: boolean;
    canOpenReturns: boolean;
    canOpenOperationalPayments: boolean;
    canRemoteClose: boolean;
    remoteCloseNote: string | null;
  };
  auditTimeline: AdminCashCutTimelineItem[];
  backendContract: AdminCashCutBackendContract;
  correctionsAdjustments: AdminCashCutCorrectionAdjustmentItem[];
  denominationCount: {
    isSupported: boolean;
    lines: Array<{ denomination: string; quantity: number; subtotal: string }>;
    totalCounted: string | null;
    note: string | null;
  };
  expectedVsCounted: AdminCashCutExpectedVsCounted;
  includedTickets: AdminCashCutTicketItem[];
  operationalPayments: AdminCashCutOperationalPaymentItem[];
  overview: AdminCashCutOverview;
  paymentBreakdown: AdminCashCutPaymentBreakdown[];
  reconciliationStatus: {
    status: string;
    reconciledAt: string | null;
    reconciledByName: string | null;
    relatedDocumentId: string | null;
    routeHint: string | null;
    note: string | null;
  };
  relatedDocuments: AdminCashCutRelatedDocument[];
  returnsRefunds: AdminCashCutRefundItem[];
}
