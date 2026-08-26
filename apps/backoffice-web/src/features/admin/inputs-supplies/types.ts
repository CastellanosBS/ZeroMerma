export type AdminInputSupplyKind = "RAW_MATERIAL" | "CONSUMABLE" | "DISPOSABLE";
export type AdminInputSupplyStatus = "active" | "inactive";
export type AdminInputSupplyStockState =
  | "in_stock"
  | "low_stock"
  | "negative_stock"
  | "out_of_stock"
  | "no_inventory";
export type AdminInputSupplyWarningSeverity = "info" | "warning" | "critical";
export type AdminInputSupplyWarningState = "ok" | AdminInputSupplyWarningSeverity;

export interface AdminInputSupplyFilterOption {
  id: string;
  label: string;
}

export interface AdminInputSupplyBackendContract {
  addSupplierRelationEndpoint: string;
  createEndpoint: string;
  detailEndpoint: string;
  listEndpoint: string;
  statusEndpoint: string;
  updateEndpoint: string;
  updateSupplierRelationEndpoint: string;
}

export interface AdminInputSupplyWarning {
  code: string;
  message: string;
  severity: AdminInputSupplyWarningSeverity;
}

export interface AdminInputSupplyMetrics {
  activeConsumables: string;
  activeDisposables: string;
  activeRawMaterials: string;
  lowStock: string;
  missingCost: string;
  usedInRecipes: string;
  withoutSupplier: string;
}

export interface AdminInputSupplyFilterOptions {
  classes: AdminInputSupplyFilterOption[];
  costStates: AdminInputSupplyFilterOption[];
  productKinds: AdminInputSupplyFilterOption[];
  recipeUsageStates: AdminInputSupplyFilterOption[];
  statuses: AdminInputSupplyFilterOption[];
  stockStates: AdminInputSupplyFilterOption[];
  suppliers: AdminInputSupplyFilterOption[];
  usageTypes: AdminInputSupplyFilterOption[];
  warningStates: AdminInputSupplyFilterOption[];
}

export interface AdminInputSupplyListFilters {
  classId?: string | null;
  costState?: "all" | "with_cost" | "missing_cost";
  inventoryTracked?: "all" | "true" | "false";
  page: number;
  pageSize: number;
  productKind?: "all" | AdminInputSupplyKind;
  purchasable?: "all" | "true" | "false";
  recipeUsage?: "all" | "used" | "unused";
  search?: string;
  status?: "all" | AdminInputSupplyStatus;
  stockState?: "all" | AdminInputSupplyStockState;
  supplierId?: string | null;
  usageType?: string | null;
  warningState?: "all" | "with_warnings" | "without_warnings" | AdminInputSupplyWarningSeverity;
  withoutSupplier?: "all" | "true" | "false";
}

export interface AdminInputSupplyListItem {
  baseUom: string;
  categoryId: string;
  categoryName: string;
  code: string;
  id: string;
  isActive: boolean;
  isInventoryTracked: boolean;
  isPurchasable: boolean;
  lastMovementAt?: string | null;
  lastPurchaseCost?: string | null;
  name: string;
  primarySupplierName?: string | null;
  productKind: AdminInputSupplyKind;
  purchaseUom?: string | null;
  recipeUsageCount: number;
  standardCost?: string | null;
  stockState: AdminInputSupplyStockState;
  supplierCount: number;
  updatedAt: string;
  warningState: AdminInputSupplyWarningState;
  warnings: AdminInputSupplyWarning[];
}

export interface AdminInputSupplyListResponse {
  backendContract: AdminInputSupplyBackendContract;
  filterOptions: AdminInputSupplyFilterOptions;
  isBackendConnected: boolean;
  items: AdminInputSupplyListItem[];
  metrics: AdminInputSupplyMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminInputSupplySupplierRelation {
  conversionFactor?: string | null;
  currency: string;
  id: string;
  isActive: boolean;
  lastKnownPrice?: string | null;
  leadTimeDays: number;
  minimumOrderQty?: string | null;
  notes?: string | null;
  purchaseUom?: string | null;
  supplierId: string;
  supplierName: string;
  supplierSku?: string | null;
}

export interface AdminInputSupplyInventoryBranch {
  branchId: string;
  branchName: string;
  lastMovementAt?: string | null;
  quantityOnHand: string;
  stockState: AdminInputSupplyStockState;
}

export interface AdminInputSupplyRecipeUsage {
  finishedProductCode: string;
  finishedProductId: string;
  finishedProductName: string;
  quantity: string;
  recipeId: string;
  recipeVersionName?: string | null;
  unitOfMeasure: string;
}

export interface AdminInputSupplyRelatedDocument {
  documentId: string;
  documentType: string;
  folio: string;
  status: string;
}

export interface AdminInputSupplyDetail {
  availableActions: {
    canAddSupplier: boolean;
    canDeactivate: boolean;
    canEdit: boolean;
    canOpenInventory: boolean;
    canOpenProduct: boolean;
    canOpenRecipes: boolean;
  };
  classification: {
    kind: AdminInputSupplyKind;
    notes?: string | null;
    status: AdminInputSupplyStatus;
    storageGroup?: string | null;
    usageType?: string | null;
  };
  cost: {
    costUpdatedAt?: string | null;
    currency: string;
    lastPurchaseCost?: string | null;
    standardCost?: string | null;
    supplierPriceMax?: string | null;
    supplierPriceMin?: string | null;
    warnings: AdminInputSupplyWarning[];
  };
  inventoryStatus: {
    integrationAvailable: boolean;
    lastMovementAt?: string | null;
    minimumStock?: string | null;
    preferredOrderQuantity?: string | null;
    reorderPoint?: string | null;
    stockByBranch: AdminInputSupplyInventoryBranch[];
    stockState: AdminInputSupplyStockState;
    totalStock?: string | null;
    unitOfMeasure: string;
  };
  overview: AdminInputSupplyListItem & {
    createdAt: string;
    readinessState: AdminInputSupplyWarningState;
  };
  procurementWarnings: AdminInputSupplyWarning[];
  recipeUsage: AdminInputSupplyRecipeUsage[];
  relatedDocuments: AdminInputSupplyRelatedDocument[];
  suppliers: AdminInputSupplySupplierRelation[];
  unitsConversion: {
    baseUom: string;
    consumptionUom: string;
    conversionFactor?: string | null;
    minimumPurchaseQuantity?: string | null;
    purchaseUom?: string | null;
    unitConversionSupported: boolean;
  };
}

export interface AdminInputSupplySupplierRelationPayload {
  conversionFactor?: string | null;
  currency?: string;
  isActive?: boolean;
  lastKnownPrice?: string | null;
  leadTimeDays?: number;
  minimumOrderQty?: string | null;
  notes?: string | null;
  purchaseUom?: string | null;
  supplierId: string;
  supplierSku?: string | null;
}

export interface AdminInputSupplyPayload {
  code: string;
  isActive: boolean;
  isInventoryTracked: boolean;
  isPurchasable: boolean;
  minimumStock?: string | null;
  name: string;
  preferredOrderQuantity?: string | null;
  procurementNotes?: string | null;
  productClassId: string;
  productKind: AdminInputSupplyKind;
  purchaseConversionFactor?: string | null;
  purchaseUom?: string | null;
  reorderPoint?: string | null;
  standardCost?: string | null;
  supplierRelations: AdminInputSupplySupplierRelationPayload[];
  unitOfMeasure: string;
  usageType?: string | null;
}

export interface AdminInputSupplyStatusPayload {
  isActive: boolean;
  notes?: string | null;
}
