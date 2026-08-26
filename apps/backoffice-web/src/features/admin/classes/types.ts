export type AdminProductClassCaptureMode = "PRODUCT_DIRECT" | "CLASS_CAPTURE";

export type AdminProductClassStatus = "active" | "inactive";

export type AdminProductClassProductPresence = "all" | "with_products" | "without_products";

export type AdminProductClassReadinessStatus =
  | "ready"
  | "requires_attention"
  | "incomplete"
  | "pending_integration"
  | "unknown";

export interface AdminProductClassFilterOption {
  id: string;
  label: string;
}

export interface AdminProductClassProductSummary {
  id: string;
  code: string;
  name: string;
  status: AdminProductClassStatus;
  unitPrice: string;
  updatedAt?: string | null;
}

export interface AdminProductClassWarnings {
  codes: string[];
  messages: string[];
}

export interface AdminProductClass {
  activeProductCount: number;
  brandId: string;
  brandName: string;
  captureModeDefault: AdminProductClassCaptureMode;
  classCaptureUnitPrice?: string | null;
  code: string;
  currencyCode: string;
  displayOrder: number;
  id: string;
  inactiveProductCount: number;
  isSellable: boolean;
  linkedProducts: AdminProductClassProductSummary[];
  name: string;
  productCount: number;
  quickName?: string | null;
  readiness: AdminProductClassReadinessStatus;
  searchAliases?: string | null;
  status: AdminProductClassStatus;
  updatedAt?: string | null;
  warnings: AdminProductClassWarnings;
}

export interface AdminProductClassCreatePayload {
  brandId: string;
  captureModeDefault: AdminProductClassCaptureMode;
  classCaptureUnitPrice?: string | null;
  code: string;
  currencyCode: string;
  displayOrder: number;
  isSellable: boolean;
  name: string;
  quickName?: string | null;
  searchAliases?: string | null;
  status: AdminProductClassStatus;
}

export interface AdminProductClassUpdatePayload {
  brandId?: string | null;
  captureModeDefault?: AdminProductClassCaptureMode | null;
  classCaptureUnitPrice?: string | null;
  code?: string | null;
  currencyCode?: string | null;
  displayOrder?: number | null;
  isSellable?: boolean | null;
  name?: string | null;
  quickName?: string | null;
  searchAliases?: string | null;
  status?: AdminProductClassStatus | null;
}

export interface AdminProductClassListFilters {
  brandId?: string | null;
  captureMode?: AdminProductClassCaptureMode | "all";
  page: number;
  pageSize: number;
  productPresence?: AdminProductClassProductPresence;
  search?: string;
  status?: AdminProductClassStatus | "all";
}

export interface AdminProductClassMetrics {
  activeClasses: string;
  classCapture: string;
  productDirect: string;
  totalClasses: string;
  withWarnings: string;
  withoutProducts: string;
}

export interface AdminProductClassFilterOptions {
  brands: AdminProductClassFilterOption[];
}

export interface AdminProductClassBackendContract {
  createEndpoint: "POST /v1/admin/product-classes";
  detailEndpoint: "GET /v1/admin/product-classes/{id}";
  listEndpoint: "GET /v1/admin/product-classes";
  updateEndpoint: "PATCH /v1/admin/product-classes/{id}";
}

export interface AdminProductClassListResponse {
  backendContract: AdminProductClassBackendContract;
  filterOptions: AdminProductClassFilterOptions;
  isBackendConnected: boolean;
  items: AdminProductClass[];
  metrics: AdminProductClassMetrics;
  page: number;
  pageSize: number;
  total: number;
}
