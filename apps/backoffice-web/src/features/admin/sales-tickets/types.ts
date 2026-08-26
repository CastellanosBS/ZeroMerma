export interface AdminSalesTicketBackendContract {
  detailEndpoint: string;
  listEndpoint: string;
  reprintEndpoint: string | null;
}

export interface AdminSalesTicketFilterOption {
  id: string;
  label: string;
}

export interface AdminSalesTicketFilterOptions {
  branches: AdminSalesTicketFilterOption[];
  cashiers: AdminSalesTicketFilterOption[];
  paymentMethods: AdminSalesTicketFilterOption[];
  statuses: AdminSalesTicketFilterOption[];
  workstations: AdminSalesTicketFilterOption[];
}

export interface AdminSalesTicketListFilters {
  branchId?: string | null;
  cashierId?: string | null;
  dateFrom?: string | null;
  dateTo?: string | null;
  maxAmount?: string | null;
  minAmount?: string | null;
  page: number;
  pageSize: number;
  paymentMethod?: string | null;
  search?: string;
  status?: string | null;
  workstationId?: string | null;
}

export interface AdminSalesTicketPaymentSummary {
  amount: string;
  currencyCode: string;
  paymentMethodCode: string;
}

export interface AdminSalesTicketMetrics {
  averageTicketAmount: string;
  cardAmount: string;
  cashAmount: string;
  ticketCount: string;
  ticketsWithReturns: string;
  totalSalesAmount: string;
}

export interface AdminSalesTicketListItem {
  branchId: string;
  branchName: string;
  cashierId: string;
  cashierName: string;
  currencyCode: string;
  folio: string;
  hasReturns: boolean;
  id: string;
  itemCount: number;
  occurredAt: string;
  paymentMethodsLabel: string;
  paymentSummary: AdminSalesTicketPaymentSummary[];
  returnCount: number;
  returnStatus: string;
  saleId: string;
  status: string;
  totalAmount: string;
  unitCount: string;
  workstationCode: string;
  workstationId: string;
  workstationName: string;
}

export interface AdminSalesTicketListResponse {
  backendContract: AdminSalesTicketBackendContract;
  filterOptions: AdminSalesTicketFilterOptions;
  isBackendConnected: boolean;
  items: AdminSalesTicketListItem[];
  metrics: AdminSalesTicketMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminSalesTicketOverview {
  changeAmount: string;
  confirmedAt: string;
  currencyCode: string;
  folio: string;
  id: string;
  itemCount: number;
  paidAmount: string;
  returnCount: number;
  returnStatus: string;
  returnedAmount: string;
  status: string;
  subtotalAmount: string;
  totalAmount: string;
  unitCount: string;
}

export interface AdminSalesTicketOperationalContext {
  branchId: string;
  branchName: string;
  cashSessionId: string;
  cashierEmail: string;
  cashierId: string;
  cashierName: string;
  confirmedAt: string;
  createdAt: string;
  saleId: string;
  workstationCode: string;
  workstationId: string;
  workstationName: string;
}

export interface AdminSalesTicketLine {
  captureMode: string;
  catalogCode: string;
  catalogName: string;
  discountAmount: string;
  id: string;
  lineTotalAmount: string;
  physicalAttributionStatus: string;
  productClassId: string | null;
  productId: string | null;
  quantity: string;
  sequence: number;
  unitPrice: string;
}

export interface AdminSalesTicketPayment {
  appliedAmount: string;
  changeAmount: string;
  currencyCode: string;
  id: string;
  paymentMethodCode: string;
  receivedAt: string;
  sequence: number;
  tenderedAmount: string;
}

export interface AdminSalesTicketRelatedDocument {
  amount: string | null;
  documentType: string;
  folio: string;
  id: string;
  occurredAt: string | null;
  routeHint: string | null;
  status: string;
}

export interface AdminSalesTicketPrintable {
  canReprint: boolean;
  note: string | null;
  previewAvailable: boolean;
}

export interface AdminSalesTicketDetail {
  lines: AdminSalesTicketLine[];
  operationalContext: AdminSalesTicketOperationalContext;
  overview: AdminSalesTicketOverview;
  payments: AdminSalesTicketPayment[];
  printableTicket: AdminSalesTicketPrintable;
  relatedDocuments: AdminSalesTicketRelatedDocument[];
}
