export type AdminSupplierStatus = "ACTIVE" | "INACTIVE" | "BLOCKED";
export type AdminSupplierWarningSeverity = "info" | "warning" | "critical";

export interface AdminSupplierFilterOption {
  id: string;
  label: string;
}

export interface AdminSupplierBackendContract {
  contactEndpoint: string;
  createEndpoint: string;
  detailEndpoint: string;
  listEndpoint: string;
  productEndpoint: string;
  statusEndpoint: string;
  updateEndpoint: string;
}

export interface AdminSupplierFilterOptions {
  branches: AdminSupplierFilterOption[];
  categories: AdminSupplierFilterOption[];
  productKinds: AdminSupplierFilterOption[];
  products: AdminSupplierFilterOption[];
  statuses: AdminSupplierFilterOption[];
  warningStates: AdminSupplierFilterOption[];
}

export interface AdminSupplierMetrics {
  activeSuppliers: string;
  blockedSuppliers: string;
  inactiveSuppliers: string;
  suppliersWithRecentActivity: string;
  suppliersWithWarnings: string;
  suppliersWithoutProducts: string;
  totalSuppliers: string;
}

export interface AdminSupplierWarning {
  code: string;
  message: string;
  severity: AdminSupplierWarningSeverity;
}

export interface AdminSupplierListFilters {
  branchId?: string | null;
  category?: string | "all";
  page: number;
  pageSize: number;
  productKind?: string | "all";
  search?: string;
  status?: AdminSupplierStatus | "all";
  warningState?: "all" | "with_warnings" | "without_warnings";
}

export interface AdminSupplierListItem {
  branchCount: number;
  category: string;
  code: string;
  commercialName?: string | null;
  id: string;
  legalName: string;
  primaryContactEmail?: string | null;
  primaryContactName?: string | null;
  primaryContactPhone?: string | null;
  productCount: number;
  status: AdminSupplierStatus;
  taxId?: string | null;
  termsSummary: string;
  updatedAt: string;
  warningState?: AdminSupplierWarningSeverity | null;
  warnings: AdminSupplierWarning[];
}

export interface AdminSupplierListResponse {
  backendContract: AdminSupplierBackendContract;
  filterOptions: AdminSupplierFilterOptions;
  isBackendConnected: boolean;
  items: AdminSupplierListItem[];
  metrics: AdminSupplierMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminSupplierOverview {
  category: string;
  code: string;
  commercialName?: string | null;
  createdAt: string;
  id: string;
  legalName: string;
  readinessState?: AdminSupplierWarningSeverity | null;
  status: AdminSupplierStatus;
  taxId?: string | null;
  updatedAt: string;
}

export interface AdminSupplierFiscalLegal {
  fiscalAddress?: string | null;
  fiscalRegime?: string | null;
  legalName: string;
  notes?: string | null;
  paymentFiscalEmail?: string | null;
  taxId?: string | null;
}

export interface AdminSupplierContact {
  email?: string | null;
  id: string;
  isActive: boolean;
  isPrimary: boolean;
  name: string;
  notes?: string | null;
  phone?: string | null;
  role?: string | null;
  whatsapp?: string | null;
}

export interface AdminSupplierCommercialTerms {
  creditDays: number;
  defaultCurrency: string;
  deliveryNotes?: string | null;
  leadTimeDays: number;
  minimumOrderAmount?: string | null;
  paymentTermsType: string;
  purchaseNotes?: string | null;
  summary: string;
}

export interface AdminSupplierProductAssociation {
  currency: string;
  id: string;
  isActive: boolean;
  lastKnownPrice?: string | null;
  leadTimeDays: number;
  minimumOrderQty?: string | null;
  notes?: string | null;
  productCode: string;
  productId: string;
  productKind: string;
  productName: string;
  purchaseUom: string;
  supplierSku?: string | null;
}

export interface AdminSupplierBranchApplicability {
  branchCode: string;
  branchId: string;
  branchName: string;
  branchStatus: string;
  deliveryNotes?: string | null;
  isActive: boolean;
}

export interface AdminSupplierOperationalActivity {
  integrationAvailable: boolean;
  notes: string;
  openPurchaseOrders?: number | null;
  recentPurchaseOrders?: number | null;
}

export interface AdminSupplierRelatedDocument {
  documentId: string;
  documentType: string;
  folio: string;
  status: string;
}

export interface AdminSupplierAvailableActions {
  canAddContact: boolean;
  canAddProduct: boolean;
  canBlock: boolean;
  canDeactivate: boolean;
  canEdit: boolean;
}

export interface AdminSupplierDetail {
  availableActions: AdminSupplierAvailableActions;
  branchApplicability: AdminSupplierBranchApplicability[];
  commercialTerms: AdminSupplierCommercialTerms;
  contacts: AdminSupplierContact[];
  fiscalLegal: AdminSupplierFiscalLegal;
  operationalActivity: AdminSupplierOperationalActivity;
  overview: AdminSupplierOverview;
  productAssociations: AdminSupplierProductAssociation[];
  relatedDocuments: AdminSupplierRelatedDocument[];
  warnings: AdminSupplierWarning[];
}

export interface AdminSupplierContactPayload {
  email?: string | null;
  isPrimary?: boolean;
  name: string;
  notes?: string | null;
  phone?: string | null;
  role?: string | null;
  whatsapp?: string | null;
}

export interface AdminSupplierProductPayload {
  currency?: string;
  isActive?: boolean;
  lastKnownPrice?: string | null;
  leadTimeDays?: number;
  minimumOrderQty?: string | null;
  notes?: string | null;
  productId: string;
  purchaseUom?: string | null;
  supplierSku?: string | null;
}

export interface AdminSupplierPayload {
  branchIds: string[];
  category: string;
  code?: string | null;
  commercialName?: string | null;
  contacts: AdminSupplierContactPayload[];
  creditDays: number;
  defaultCurrency: string;
  deliveryNotes?: string | null;
  fiscalAddress?: string | null;
  fiscalRegime?: string | null;
  leadTimeDays: number;
  legalName: string;
  minimumOrderAmount?: string | null;
  notes?: string | null;
  paymentFiscalEmail?: string | null;
  paymentTermsType: string;
  productRelations: AdminSupplierProductPayload[];
  purchaseNotes?: string | null;
  status: AdminSupplierStatus;
  taxId?: string | null;
}

export interface AdminSupplierStatusPayload {
  notes?: string | null;
  status: AdminSupplierStatus;
}
