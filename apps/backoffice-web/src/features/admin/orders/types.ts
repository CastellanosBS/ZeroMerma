export interface AdminOrderBackendContract {
  cancelEndpoint: string;
  createEndpoint: string | null;
  deliverEndpoint: string;
  detailEndpoint: string;
  financialCaptureEndpoint: string | null;
  listEndpoint: string;
  markReadyEndpoint: string;
}

export interface AdminOrderFilterOption {
  id: string;
  label: string;
}

export interface AdminOrderFilterOptions {
  branches: AdminOrderFilterOption[];
  cashiers: AdminOrderFilterOption[];
  paymentStates: AdminOrderFilterOption[];
  statuses: AdminOrderFilterOption[];
  workstations: AdminOrderFilterOption[];
}

export interface AdminOrderListFilters {
  branchId?: string | null;
  cashierId?: string | null;
  dateFrom?: string | null;
  dateTo?: string | null;
  page: number;
  pageSize: number;
  paymentState?: string | null;
  search?: string;
  status?: string | null;
  workstationId?: string | null;
}

export interface AdminOrderMetrics {
  activeOrders: number;
  canceledOrders: number;
  depositsReceivedAmount: string;
  dueToday: number;
  outstandingBalanceAmount: string;
  readyOrders: number;
}

export interface AdminOrderListItem {
  advanceAmount: string;
  branchId: string;
  branchName: string;
  cancellationRefundAmount: string;
  cancellationRefundEligible: boolean;
  createdAtUtc: string;
  createdByUserFullName: string;
  createdByUserId: string;
  currencyCode: string;
  customerName: string;
  customerPhone: string | null;
  folio: string;
  id: string;
  lineCount: number;
  paymentState: string;
  remainingBalanceAmount: string;
  requestedForAt: string | null;
  status: string;
  totalAmount: string;
  totalUnits: string;
  updatedAtUtc: string;
  warningState: string | null;
  workstationCode: string;
  workstationId: string;
  workstationName: string;
}

export interface AdminOrdersListResponse {
  backendContract: AdminOrderBackendContract;
  filterOptions: AdminOrderFilterOptions;
  isBackendConnected: boolean;
  items: AdminOrderListItem[];
  metrics: AdminOrderMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminOrderOverview {
  advanceAmount: string;
  branchId: string;
  branchName: string;
  canceledAt: string | null;
  cancellationReason: string | null;
  cancellationRefundAmount: string;
  cancellationRefundEligible: boolean;
  createdAtUtc: string;
  currencyCode: string;
  customerName: string;
  customerPhone: string | null;
  deliveredAt: string | null;
  folio: string;
  id: string;
  paymentState: string;
  remainingBalanceAmount: string;
  requestedForAt: string | null;
  status: string;
  totalAmount: string;
  updatedAtUtc: string;
}

export interface AdminOrderCustomer {
  name: string;
  notes: string | null;
  phone: string | null;
}

export interface AdminOrderLine {
  id: string;
  lineNumber: number;
  lineTotalAmount: string;
  productClassCode: string;
  productClassId: string;
  productClassName: string;
  productCode: string;
  productId: string;
  productName: string;
  quantity: string;
  unitPrice: string;
}

export interface AdminOrderPayment {
  amount: string;
  currencyCode: string;
  id: string;
  paymentMethodCode: string;
  paymentType: string;
  recordedAtUtc: string;
  recordedByUserFullName: string;
  recordedByUserId: string;
  sequence: number;
}

export interface AdminOrderTimelineEvent {
  description: string | null;
  key: string;
  label: string;
  occurredAt: string;
}

export interface AdminOrderRelatedDocument {
  amount: string | null;
  documentType: string;
  folio: string;
  id: string;
  occurredAt: string | null;
  routeHint: string | null;
  status: string;
}

export interface AdminOrderAvailableActions {
  canCancel: boolean;
  canCaptureBalance: boolean;
  canCreateFromBackoffice: boolean;
  canDeliver: boolean;
  canMarkReady: boolean;
  financialActionNote: string | null;
  requiresCashSessionForFinancialAction: boolean;
  requiresSettlementOnDelivery: boolean;
}

export interface AdminOrderOperationalContext {
  activeCashSessionId: string | null;
  branchId: string | null;
  branchName: string | null;
  canceledByUserFullName: string | null;
  createdByUserFullName: string | null;
  createdByUserId: string | null;
  deliveredByUserFullName: string | null;
  workstationCode: string | null;
  workstationId: string | null;
  workstationName: string | null;
}

export interface AdminOrderDetail {
  availableActions: AdminOrderAvailableActions;
  backendContract: AdminOrderBackendContract;
  customer: AdminOrderCustomer;
  lines: AdminOrderLine[];
  operationalContext: AdminOrderOperationalContext;
  overview: AdminOrderOverview;
  payments: AdminOrderPayment[];
  relatedDocuments: AdminOrderRelatedDocument[];
  timeline: AdminOrderTimelineEvent[];
}
