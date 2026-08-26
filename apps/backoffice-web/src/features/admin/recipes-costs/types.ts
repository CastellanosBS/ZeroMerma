export type AdminRecipeState = "all" | "no_recipe" | "active_recipe" | "warning";
export type AdminRecipeHealthStatus = "healthy" | "warning" | "incomplete" | "no_recipe";
export type AdminRecipeProductStatus = "active" | "inactive";

export interface AdminRecipeFilterOption {
  id: string;
  label: string;
}

export interface AdminRecipeInput {
  id: string;
  inputProductId: string;
  inputProductCode: string;
  inputProductName: string;
  unitOfMeasure: string;
  quantity: string;
  standardCost: string | null;
  extendedCost: string | null;
  status: AdminRecipeProductStatus;
}

export interface AdminRecipe {
  id: string;
  productId: string;
  versionName: string | null;
  yieldQty: string;
  yieldUom: string;
  isActive: boolean;
  inputCount: number;
  totalBatchCost: string | null;
  calculatedUnitCost: string | null;
  createdAt: string;
  updatedAt: string;
  inputs: AdminRecipeInput[];
}

export interface AdminRecipeWarnings {
  codes: string[];
  messages: string[];
}

export interface AdminRecipeCostProduct {
  productId: string;
  productCode: string;
  productName: string;
  classId: string;
  className: string;
  brandId: string;
  brandName: string;
  unitOfMeasure: string;
  productStatus: AdminRecipeProductStatus;
  productStandardCost: string | null;
  productUnitPrice: string;
  currencyCode: string;
  activeRecipeId: string | null;
  activeRecipeVersionName: string | null;
  activeRecipeUpdatedAt: string | null;
  recipeInputCount: number;
  yieldQty: string | null;
  yieldUom: string | null;
  totalBatchCost: string | null;
  calculatedUnitCost: string | null;
  costVariance: string | null;
  costVariancePercent: string | null;
  healthStatus: AdminRecipeHealthStatus;
  warnings: AdminRecipeWarnings;
  updatedAt: string | null;
}

export interface AdminRecipeCostDetail {
  product: AdminRecipeCostProduct;
  activeRecipe: AdminRecipe | null;
  recipeVersions: AdminRecipe[];
}

export interface AdminRecipeCreateInputPayload {
  inputProductId: string;
  quantity: string;
}

export interface AdminRecipeCreatePayload {
  activate: boolean;
  inputs: AdminRecipeCreateInputPayload[];
  productId: string;
  versionName?: string | null;
  yieldQty: string;
  yieldUom: string;
}

export interface AdminRecipeDuplicatePayload {
  activate: boolean;
  versionName?: string | null;
}

export interface AdminRecipeCostListFilters {
  brandId?: string | null;
  classId?: string | null;
  page: number;
  pageSize: number;
  recipeState?: AdminRecipeState;
  search?: string;
}

export interface AdminRecipeCostMetrics {
  highVariance: string;
  recentlyUpdated: string;
  withActiveRecipe: string;
  withoutRecipe: string;
  withWarnings: string;
}

export interface AdminRecipeCostFilterOptions {
  brands: AdminRecipeFilterOption[];
  classes: AdminRecipeFilterOption[];
  rawMaterials: AdminRecipeFilterOption[];
}

export interface AdminRecipeCostBackendContract {
  applyStandardCostEndpoint: "POST /v1/admin/recipes-costs/recipes/{id}/apply-standard-cost";
  createEndpoint: "POST /v1/admin/recipes-costs/recipes";
  detailEndpoint: "GET /v1/admin/recipes-costs/products/{id}";
  duplicateEndpoint: "POST /v1/admin/recipes-costs/recipes/{id}/duplicate";
  listEndpoint: "GET /v1/admin/recipes-costs/products";
}

export interface AdminRecipeCostListResponse {
  backendContract: AdminRecipeCostBackendContract;
  filterOptions: AdminRecipeCostFilterOptions;
  isBackendConnected: boolean;
  items: AdminRecipeCostProduct[];
  metrics: AdminRecipeCostMetrics;
  page: number;
  pageSize: number;
  total: number;
}
