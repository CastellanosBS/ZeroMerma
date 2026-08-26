export type AdminProductionStatus = "DRAFT" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";
export type AdminProductionWarningSeverity = "info" | "warning" | "critical";
export type AdminProductionVarianceState = "with_variance" | "without_variance";

export interface AdminProductionFilterOption {
  id: string;
  label: string;
}

export interface AdminProductionWarning {
  code: string;
  message: string;
  severity: AdminProductionWarningSeverity;
}

export interface AdminProductionBackendContract {
  cancelEndpoint: string;
  completeEndpoint: string;
  createEndpoint: string;
  detailEndpoint: string;
  listEndpoint: string;
  startEndpoint: string;
  updateEndpoint: string;
}

export interface AdminProductionMetrics {
  completedBatches: string;
  inProgressBatches: string;
  pendingBatches: string;
  producedUnits: string;
  totalBatches: string;
  withShortages: string;
  withVariance: string;
}

export interface AdminProductionFilterOptions {
  branches: AdminProductionFilterOption[];
  operators: AdminProductionFilterOption[];
  products: AdminProductionFilterOption[];
  recipes: AdminProductionFilterOption[];
  statuses: AdminProductionFilterOption[];
}

export interface AdminProductionListFilters {
  branchId?: string | null;
  dateFrom?: string | null;
  dateTo?: string | null;
  operatorUserId?: string | null;
  page: number;
  pageSize: number;
  productId?: string | null;
  recipeId?: string | null;
  search?: string;
  status?: AdminProductionStatus | "all";
  varianceState?: AdminProductionVarianceState | "all";
  warningState?: AdminProductionWarningSeverity | "all";
}

export interface AdminProductionListItem {
  actualOutputQty?: string | null;
  branchId: string;
  branchName: string;
  completedAt?: string | null;
  folio: string;
  id: string;
  operatorName: string;
  plannedAt?: string | null;
  plannedOutputQty: string;
  productCode: string;
  productId: string;
  productName: string;
  recipeId: string;
  recipeName: string;
  startedAt?: string | null;
  status: AdminProductionStatus;
  variancePercent?: string | null;
  varianceQty?: string | null;
  warningState?: AdminProductionWarningSeverity | null;
  warnings: AdminProductionWarning[];
}

export interface AdminProductionListResponse {
  backendContract: AdminProductionBackendContract;
  filterOptions: AdminProductionFilterOptions;
  isBackendConnected: boolean;
  items: AdminProductionListItem[];
  metrics: AdminProductionMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminProductionOverview {
  actualOutputQty?: string | null;
  branchId: string;
  branchName: string;
  cancelledAt?: string | null;
  completedAt?: string | null;
  completedByUserId?: string | null;
  completedByUserName?: string | null;
  createdAt: string;
  createdByUserId: string;
  createdByUserName: string;
  folio: string;
  id: string;
  notes?: string | null;
  plannedAt?: string | null;
  plannedOutputQty: string;
  startedAt?: string | null;
  startedByUserId?: string | null;
  startedByUserName?: string | null;
  status: AdminProductionStatus;
  variancePercent?: string | null;
  varianceQty?: string | null;
  varianceReason?: string | null;
  warningState?: AdminProductionWarningSeverity | null;
}

export interface AdminProductionProductRecipe {
  productCode: string;
  productId: string;
  productIsActive: boolean;
  productKind: string;
  productName: string;
  productUnitOfMeasure: string;
  recipeId: string;
  recipeIsActive: boolean;
  recipeName: string;
  recipeYieldQty: string;
  recipeYieldUom: string;
}

export interface AdminProductionInputLine {
  availableQty?: string | null;
  inputProductCode: string;
  inputProductId: string;
  inputProductName: string;
  requiredQty: string;
  shortageQty?: string | null;
  standardCost?: string | null;
  status: "available" | "insufficient" | "unavailable";
  uom: string;
}

export interface AdminProductionActualConsumptionLine {
  consumedQty?: string | null;
  differenceQty?: string | null;
  expectedQty: string;
  inputProductCode: string;
  inputProductId: string;
  inputProductName: string;
  uom: string;
}

export interface AdminProductionOutputYield {
  actualOutputQty?: string | null;
  plannedOutputQty: string;
  uom: string;
  variancePercent?: string | null;
  varianceQty?: string | null;
  varianceReason?: string | null;
}

export interface AdminProductionInventoryMovement {
  balanceAfter?: string | null;
  branchId: string;
  direction: string;
  id: string;
  locationCode: string;
  movementType: string;
  productId: string;
  quantity: string;
  sourceDocumentId?: string | null;
  sourceDocumentType?: string | null;
  unitOfMeasure: string;
}

export interface AdminProductionInventoryImpact {
  integrationAvailable: boolean;
  movements: AdminProductionInventoryMovement[];
  notes?: string | null;
}

export interface AdminProductionRelatedDocument {
  documentId: string;
  documentType: string;
  folio: string;
  status: string;
}

export interface AdminProductionWasteScrap {
  integrationAvailable: boolean;
  notes: string;
  records: Array<Record<string, string>>;
}

export interface AdminProductionAvailableActions {
  canCancel: boolean;
  canComplete: boolean;
  canEdit: boolean;
  canStart: boolean;
  canViewMovements: boolean;
}

export interface AdminProductionDetail {
  actualConsumption: AdminProductionActualConsumptionLine[];
  availableActions: AdminProductionAvailableActions;
  inventoryImpact: AdminProductionInventoryImpact;
  outputYield: AdminProductionOutputYield;
  overview: AdminProductionOverview;
  plannedInputs: AdminProductionInputLine[];
  productRecipe: AdminProductionProductRecipe;
  relatedDocuments: AdminProductionRelatedDocument[];
  warnings: AdminProductionWarning[];
  wasteScrap: AdminProductionWasteScrap;
}

export interface AdminProductionCreatePayload {
  branchId: string;
  notes?: string | null;
  plannedAt?: string | null;
  plannedOutputQty: string;
  productId: string;
  recipeId?: string | null;
}

export interface AdminProductionUpdatePayload {
  notes?: string | null;
  plannedAt?: string | null;
  plannedOutputQty?: string | null;
  productId?: string | null;
  recipeId?: string | null;
}

export interface AdminProductionCompletePayload {
  actualOutputQty: string;
  notes?: string | null;
  varianceReason?: string | null;
}
