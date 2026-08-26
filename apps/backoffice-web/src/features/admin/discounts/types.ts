export type AdminDiscountType = "PERCENTAGE" | "FIXED_AMOUNT";
export type AdminDiscountScope = "GLOBAL" | "PRODUCT" | "CLASS";
export type AdminDiscountStatus = "ACTIVE" | "INACTIVE" | "ARCHIVED";
export type AdminDiscountValidityStatus = "current" | "upcoming" | "expired" | "not_scheduled";
export type AdminDiscountHealth = "healthy" | "warning" | "invalid" | "expired";

export interface AdminDiscountFilterOption {
  id: string;
  label: string;
}

export interface AdminDiscountWarnings {
  codes: string[];
  messages: string[];
}

export interface AdminDiscount {
  basePrice: string | null;
  brandId: string | null;
  brandName: string | null;
  code: string | null;
  createdAt: string;
  currencyCode: string;
  description: string | null;
  discountType: AdminDiscountType;
  health: AdminDiscountHealth;
  id: string;
  isPosEligible: boolean;
  name: string;
  previewPrice: string | null;
  priority: number;
  status: AdminDiscountStatus;
  targetClassId: string | null;
  targetClassName: string | null;
  targetCode: string | null;
  targetId: string | null;
  targetName: string | null;
  targetScope: AdminDiscountScope;
  targetStatus: string | null;
  updatedAt: string;
  validFromUtc: string | null;
  validToUtc: string | null;
  validityStatus: AdminDiscountValidityStatus;
  value: string;
  warnings: AdminDiscountWarnings;
}

export interface AdminDiscountMetrics {
  activeDiscounts: string;
  classScoped: string;
  expiredDiscounts: string;
  productScoped: string;
  totalDiscounts: string;
  upcomingDiscounts: string;
  withWarnings: string;
}

export interface AdminDiscountFilterOptions {
  brands: AdminDiscountFilterOption[];
  classes: AdminDiscountFilterOption[];
  products: AdminDiscountFilterOption[];
}

export interface AdminDiscountBackendContract {
  createEndpoint: string;
  detailEndpoint: string;
  duplicateEndpoint: string;
  listEndpoint: string;
  updateEndpoint: string;
}

export interface AdminDiscountListResponse {
  backendContract: AdminDiscountBackendContract;
  filterOptions: AdminDiscountFilterOptions;
  isBackendConnected: boolean;
  items: AdminDiscount[];
  metrics: AdminDiscountMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminDiscountListFilters {
  brandId?: string | null;
  classId?: string | null;
  discountType: AdminDiscountType | "all";
  page: number;
  pageSize: number;
  search: string;
  status: AdminDiscountStatus | "all";
  targetScope: AdminDiscountScope | "all";
  validity: AdminDiscountValidityStatus | "all";
  warningState: "all" | "with_warnings" | "without_warnings";
}

export interface AdminDiscountSavePayload {
  brandId?: string | null;
  code?: string | null;
  currencyCode: string;
  description?: string | null;
  discountType: AdminDiscountType;
  isPosEligible: boolean;
  name: string;
  priority: number;
  status: AdminDiscountStatus;
  targetId?: string | null;
  targetScope: AdminDiscountScope;
  validFromUtc?: string | null;
  validToUtc?: string | null;
  value: string;
}

export interface AdminDiscountDuplicatePayload {
  code?: string | null;
  name?: string | null;
}
