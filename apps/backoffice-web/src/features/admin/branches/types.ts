export type AdminBranchStatus = "active" | "inactive";
export type AdminBranchReadiness = "ready" | "warning" | "inactive";
export type AdminBranchWarningSeverity = "info" | "warning" | "critical";
export type AdminBranchActiveWorkstationFilter = "all" | "yes" | "no";
export type AdminBranchWarningState = "all" | "with_warnings" | "without_warnings";

export interface AdminBranchFilterOption {
  id: string;
  label: string;
}

export interface AdminBranchWarning {
  code: string;
  message: string;
  severity: AdminBranchWarningSeverity;
}

export interface AdminBranchListItem {
  activeWorkstationCount: number;
  assignedUserCount: number;
  brandId: string;
  brandName: string;
  code: string;
  id: string;
  name: string;
  readiness: AdminBranchReadiness;
  status: AdminBranchStatus;
  timezone: string;
  updatedAt?: string | null;
  warnings: AdminBranchWarning[];
  workstationCount: number;
}

export interface AdminBranchOverview {
  brandId: string;
  brandName: string;
  code: string;
  createdAt?: string | null;
  id: string;
  name: string;
  readiness: AdminBranchReadiness;
  status: AdminBranchStatus;
  timezone: string;
  updatedAt?: string | null;
}

export interface AdminBranchLocationContact {
  addressLine?: string | null;
  city?: string | null;
  contactEmail?: string | null;
  country?: string | null;
  notes?: string | null;
  phone?: string | null;
  postalCode?: string | null;
  state?: string | null;
}

export interface AdminBranchOperationalConfig {
  inventoryScopeReady: boolean;
  isActive: boolean;
  posReady: boolean;
  productionScopeReady: boolean;
  timezone: string;
}

export interface AdminBranchWorkstation {
  code: string;
  id: string;
  isActive: boolean;
  name: string;
  updatedAt?: string | null;
}

export interface AdminBranchWorkstationsSummary {
  active: number;
  inactive: number;
  items: AdminBranchWorkstation[];
  total: number;
}

export interface AdminBranchUserAssignment {
  assignmentId: string;
  isActive: boolean;
  updatedAt?: string | null;
  userEmail: string;
  userId: string;
  userName: string;
}

export interface AdminBranchUsersSummary {
  active: number;
  inactive: number;
  items: AdminBranchUserAssignment[];
  total: number;
}

export interface AdminBranchRelatedOperationsSummary {
  openCashSessions: number;
}

export interface AdminBranchAvailableActions {
  canActivate: boolean;
  canDeactivate: boolean;
  canEdit: boolean;
  canOpenUsers: boolean;
  canOpenWorkstations: boolean;
}

export interface AdminBranchDetail {
  availableActions: AdminBranchAvailableActions;
  locationContact: AdminBranchLocationContact;
  operationalConfig: AdminBranchOperationalConfig;
  overview: AdminBranchOverview;
  relatedOperationsSummary: AdminBranchRelatedOperationsSummary;
  userAssignmentsSummary: AdminBranchUsersSummary;
  warnings: AdminBranchWarning[];
  workstationsSummary: AdminBranchWorkstationsSummary;
}

export interface AdminBranchCreatePayload {
  addressLine?: string | null;
  brandId: string;
  city?: string | null;
  code: string;
  contactEmail?: string | null;
  country?: string | null;
  isActive: boolean;
  name: string;
  notes?: string | null;
  phone?: string | null;
  postalCode?: string | null;
  state?: string | null;
  timezone: string;
}

export interface AdminBranchUpdatePayload {
  addressLine?: string | null;
  brandId?: string | null;
  city?: string | null;
  code?: string | null;
  contactEmail?: string | null;
  country?: string | null;
  isActive?: boolean | null;
  name?: string | null;
  notes?: string | null;
  phone?: string | null;
  postalCode?: string | null;
  state?: string | null;
  timezone?: string | null;
}

export interface AdminBranchListFilters {
  brandId?: string | null;
  hasActiveWorkstations?: AdminBranchActiveWorkstationFilter;
  page: number;
  pageSize: number;
  search?: string;
  status?: AdminBranchStatus | "all";
  warningState?: AdminBranchWarningState;
}

export interface AdminBranchMetrics {
  activeBranches: string;
  inactiveBranches: string;
  totalBranches: string;
  withWarnings: string;
  withWorkstations: string;
  withoutActiveWorkstation: string;
}

export interface AdminBranchFilterOptions {
  brands: AdminBranchFilterOption[];
}

export interface AdminBranchBackendContract {
  createEndpoint: "POST /v1/admin/branches";
  detailEndpoint: "GET /v1/admin/branches/{id}";
  listEndpoint: "GET /v1/admin/branches";
  updateEndpoint: "PATCH /v1/admin/branches/{id}";
}

export interface AdminBranchListResponse {
  backendContract: AdminBranchBackendContract;
  filterOptions: AdminBranchFilterOptions;
  isBackendConnected: boolean;
  items: AdminBranchListItem[];
  metrics: AdminBranchMetrics;
  page: number;
  pageSize: number;
  total: number;
}
