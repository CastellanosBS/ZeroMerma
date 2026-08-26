export type AdminProductCaptureMode = "PRODUCT_DIRECT" | "CLASS_CAPTURE";

export type AdminProductStatus = "active" | "inactive";

export type AdminProductReadinessStatus =
  | "ready"
  | "requires_attention"
  | "incomplete"
  | "pending_integration"
  | "unknown";

export type AdminProductAvailabilityState =
  | "available"
  | "not_available"
  | "not_configured"
  | "unknown";

export interface AdminProductFilterOption {
  id: string;
  label: string;
}

export interface AdminProductBranchAvailability {
  branchId: string;
  branchName: string;
  brandId?: string | null;
  brandName?: string | null;
  state: AdminProductAvailabilityState;
  visibleInPos: boolean;
  updatedAt?: string | null;
}

export interface AdminProductAvailabilitySummary {
  configuredBranchesCount: number | null;
  state: AdminProductAvailabilityState;
  totalBranchesCount: number | null;
}

export interface AdminProductRelatedReadiness {
  auditTrail: AdminProductReadinessStatus;
  branchAvailability: AdminProductReadinessStatus;
  inventory: AdminProductReadinessStatus;
  posVisibility: AdminProductReadinessStatus;
  price: AdminProductReadinessStatus;
  recipe: AdminProductReadinessStatus;
}

export interface AdminProductReadiness {
  missingRequirements: string[];
  related: AdminProductRelatedReadiness;
  status: AdminProductReadinessStatus;
}

export interface AdminProduct {
  availability: AdminProductAvailabilitySummary;
  branchAvailability: AdminProductBranchAvailability[];
  brandId?: string | null;
  brandName?: string | null;
  captureMode: AdminProductCaptureMode;
  classId?: string | null;
  className?: string | null;
  code?: string | null;
  description?: string | null;
  id: string;
  name: string;
  readiness: AdminProductReadiness;
  sku?: string | null;
  status: AdminProductStatus;
  unitPrice: string;
  currencyCode: string;
  unitOfMeasure?: string | null;
  updatedAt?: string | null;
  visibleInPos: boolean;
}

export interface AdminProductCreatePayload {
  captureMode?: AdminProductCaptureMode;
  code: string;
  name: string;
  productClassId: string;
  quickName?: string | null;
  searchAliases?: string | null;
  status: AdminProductStatus;
  unitPrice: string;
}

export interface AdminProductUpdatePayload {
  captureMode?: AdminProductCaptureMode;
  code?: string;
  name?: string;
  productClassId?: string;
  quickName?: string | null;
  searchAliases?: string | null;
  status?: AdminProductStatus;
  unitPrice?: string;
}

export interface AdminProductListFilters {
  brandId?: string | null;
  branchId?: string | null;
  captureMode?: AdminProductCaptureMode | "all";
  classId?: string | null;
  page: number;
  pageSize: number;
  readiness?: AdminProductReadinessStatus | "all";
  search?: string;
  status?: AdminProductStatus | "all";
}

export interface AdminProductMetrics {
  activeProducts: string | null;
  classCapture: string | null;
  productDirect: string | null;
  requireAttention: string | null;
  withoutBranchAvailability: string | null;
}

export interface AdminProductFilterOptions {
  brands: AdminProductFilterOption[];
  branches: AdminProductFilterOption[];
  classes: AdminProductFilterOption[];
}

export interface AdminProductBackendContract {
  createEndpoint: "POST /v1/admin/products";
  detailEndpoint: "GET /v1/admin/products/{id}";
  listEndpoint: "GET /v1/admin/products";
  updateEndpoint: "PATCH /v1/admin/products/{id}";
  availabilityEndpoint: "POST /v1/admin/products/{id}/availability";
  expectedListFields: string[];
}

export interface AdminProductListResponse {
  backendContract: AdminProductBackendContract;
  filterOptions: AdminProductFilterOptions;
  isBackendConnected: boolean;
  items: AdminProduct[];
  metrics: AdminProductMetrics;
  total: number;
  page: number;
  pageSize: number;
}
