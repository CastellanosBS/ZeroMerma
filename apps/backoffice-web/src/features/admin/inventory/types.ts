export type AdminInventoryLocationCode = "BACKROOM" | "COUNTER" | "IN_TRANSIT" | "WASTE";
export type AdminInventoryProductKind = "FINISHED_GOOD" | "RAW_MATERIAL" | "CONSUMABLE" | "DISPOSABLE";
export type AdminInventoryProductStatus = "active" | "inactive";
export type AdminInventoryStockState = "in_stock" | "out_of_stock" | "low_stock" | "negative_stock";
export type AdminInventoryWarningSeverity = "info" | "warning" | "critical";
export type AdminInventoryAdjustmentType = "INCREASE" | "DECREASE" | "SET_COUNTED";
export type AdminInventoryMovementDirection = "IN" | "OUT";

export interface AdminInventoryFilterOption {
  id: string;
  label: string;
}

export interface AdminInventoryWarning {
  code: string;
  message: string;
  severity: AdminInventoryWarningSeverity;
}

export interface AdminInventoryListItem {
  availableQuantity?: string | null;
  balanceId: string;
  branchId: string;
  branchIsActive: boolean;
  branchName: string;
  classId: string;
  className: string;
  inTransitQuantity?: string | null;
  lastMovementAt?: string | null;
  locationCode: AdminInventoryLocationCode;
  locationName: string;
  productCode: string;
  productId: string;
  productIsActive: boolean;
  productKind: AdminInventoryProductKind;
  productName: string;
  quantityOnHand: string;
  reservedQuantity?: string | null;
  stockState: AdminInventoryStockState;
  unitOfMeasure: string;
  warningState?: AdminInventoryWarningSeverity | null;
  warnings: AdminInventoryWarning[];
}

export interface AdminInventoryProduct {
  classId: string;
  className: string;
  code: string;
  id: string;
  isActive: boolean;
  isSellable: boolean;
  name: string;
  productKind: AdminInventoryProductKind;
  standardCost?: string | null;
  unitOfMeasure: string;
}

export interface AdminInventoryBranchLocation {
  branchId: string;
  branchIsActive: boolean;
  branchName: string;
  locationCode: AdminInventoryLocationCode;
  locationModelSupported: boolean;
  locationName: string;
}

export interface AdminInventoryStockBreakdown {
  availableQuantity?: string | null;
  estimatedValue?: string | null;
  inTransitQuantity?: string | null;
  quantityOnHand: string;
  reservedQuantity?: string | null;
  unitOfMeasure: string;
}

export interface AdminInventoryMovementSummary {
  lastAdjustmentAt?: string | null;
  lastInboundAt?: string | null;
  lastMovementAt?: string | null;
  lastOutboundAt?: string | null;
}

export interface AdminInventoryRelatedActions {
  canCreateAdjustment: boolean;
  canOpenBranch: boolean;
  canOpenProduct: boolean;
  canStartCount: boolean;
  countEndpointAvailable: boolean;
}

export interface AdminInventoryMovement {
  balanceAfter?: string | null;
  branchId: string;
  branchName: string;
  direction: AdminInventoryMovementDirection;
  id: string;
  locationCode: AdminInventoryLocationCode;
  movementType: string;
  notes?: string | null;
  occurredAt: string;
  operatorName?: string | null;
  productId: string;
  quantity: string;
  reason?: string | null;
  sourceDocumentId?: string | null;
  sourceDocumentType?: string | null;
  unitOfMeasure: string;
}

export interface AdminInventoryDetail {
  balanceId: string;
  branchLocation: AdminInventoryBranchLocation;
  movementSummary: AdminInventoryMovementSummary;
  movements: AdminInventoryMovement[];
  product: AdminInventoryProduct;
  relatedActions: AdminInventoryRelatedActions;
  stockBreakdown: AdminInventoryStockBreakdown;
  stockState: AdminInventoryStockState;
  warnings: AdminInventoryWarning[];
}

export interface AdminInventoryMetrics {
  estimatedValue?: string | null;
  negativeStock: string;
  productsWithStock: string;
  staleStock: string;
  totalRecords: string;
}

export interface AdminInventoryFilterOptions {
  branches: AdminInventoryFilterOption[];
  classes: AdminInventoryFilterOption[];
  locations: AdminInventoryFilterOption[];
  productKinds: AdminInventoryFilterOption[];
  products: AdminInventoryFilterOption[];
}

export interface AdminInventoryBackendContract {
  adjustmentEndpoint: "POST /v1/admin/inventory/adjustments";
  detailEndpoint: "GET /v1/admin/inventory/{balance_id}";
  listEndpoint: "GET /v1/admin/inventory";
  movementsEndpoint: "GET /v1/admin/inventory/{balance_id}/movements";
}

export interface AdminInventoryListResponse {
  backendContract: AdminInventoryBackendContract;
  filterOptions: AdminInventoryFilterOptions;
  isBackendConnected: boolean;
  items: AdminInventoryListItem[];
  metrics: AdminInventoryMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminInventoryMovementsResponse {
  items: AdminInventoryMovement[];
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminInventoryListFilters {
  branchId?: string | null;
  classId?: string | null;
  locationCode?: AdminInventoryLocationCode | "all";
  page: number;
  pageSize: number;
  productKind?: AdminInventoryProductKind | "all";
  productStatus?: AdminInventoryProductStatus | "all";
  search?: string;
  stockState?: AdminInventoryStockState | "all";
}

export interface AdminInventoryAdjustmentPayload {
  adjustmentType: AdminInventoryAdjustmentType;
  branchId: string;
  locationCode: AdminInventoryLocationCode;
  notes?: string | null;
  productId: string;
  quantity: string;
  reason: string;
}

export interface AdminInventoryAdjustment {
  adjustmentType: AdminInventoryAdjustmentType;
  balanceId: string;
  branchId: string;
  createdAt: string;
  createdByUserId: string;
  id: string;
  locationCode: AdminInventoryLocationCode;
  newQuantity: string;
  notes?: string | null;
  previousQuantity: string;
  productId: string;
  quantity: string;
  reason: string;
}
