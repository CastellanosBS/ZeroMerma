export type AdminPriceCaptureMode = "PRODUCT_DIRECT" | "CLASS_CAPTURE";
export type AdminPriceEntityType = "product" | "class";
export type AdminPriceHealth =
  | "healthy"
  | "missing_price"
  | "warning"
  | "low_margin"
  | "negative_margin";
export type AdminPriceOwner = "product_unit_price" | "class_capture_unit_price";
export type AdminPriceStatus = "active" | "inactive";

export interface AdminPriceFilterOption {
  id: string;
  label: string;
}

export interface AdminPriceWarnings {
  codes: string[];
  messages: string[];
}

export interface AdminPriceRow {
  brandId: string;
  brandName: string;
  captureMode: AdminPriceCaptureMode;
  classId: string;
  className: string;
  currencyCode: string;
  currentPrice: string | null;
  entityCode: string;
  entityId: string;
  entityName: string;
  entityType: AdminPriceEntityType;
  health: AdminPriceHealth;
  marginPercent: string | null;
  priceCostDelta: string | null;
  priceOwner: AdminPriceOwner;
  relatedClassId: string;
  relatedProductId: string | null;
  standardCost: string | null;
  status: AdminPriceStatus;
  updatedAt: string | null;
  warnings: AdminPriceWarnings;
}

export interface AdminPriceDetail {
  historyNote: string | null;
  price: AdminPriceRow;
}

export interface AdminPriceMetrics {
  classCapture: string;
  highVariance: string;
  missingOrInvalid: string;
  productDirect: string;
  recentlyChanged: string;
  totalEntities: string;
}

export interface AdminPriceFilterOptions {
  brands: AdminPriceFilterOption[];
  classes: AdminPriceFilterOption[];
}

export interface AdminPriceListFilters {
  brandId?: string | null;
  captureMode?: AdminPriceCaptureMode | "all";
  classId?: string | null;
  entityType?: AdminPriceEntityType | "all";
  page: number;
  pageSize: number;
  priceHealth?: AdminPriceHealth | "all";
  search?: string;
  status?: AdminPriceStatus | "all";
  updatedFrom?: string | null;
  updatedTo?: string | null;
}

export interface AdminPriceListResponse {
  backendContract: AdminPriceBackendContract;
  filterOptions: AdminPriceFilterOptions;
  isBackendConnected: boolean;
  items: AdminPriceRow[];
  metrics: AdminPriceMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminPriceUpdatePayload {
  price: string;
}

export interface AdminPriceBackendContract {
  detailEndpoint: string;
  listEndpoint: string;
  updateEndpoint: string;
}
