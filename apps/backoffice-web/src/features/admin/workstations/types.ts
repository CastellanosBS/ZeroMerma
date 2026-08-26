export type AdminWorkstationStatus = "active" | "inactive";
export type AdminWorkstationReadiness = "ready" | "warning" | "blocked";
export type AdminWorkstationCashSessionState = "all" | "open" | "closed" | "no_recent_session";
export type AdminWorkstationWarningSeverity = "info" | "warning" | "critical";
export type AdminWorkstationWarningState = "all" | "with_warnings" | "without_warnings";

export interface AdminWorkstationFilterOption {
  id: string;
  label: string;
}

export interface AdminWorkstationWarning {
  code: string;
  message: string;
  severity: AdminWorkstationWarningSeverity;
}

export interface AdminWorkstationListItem {
  activeCashSessionId?: string | null;
  branchCode: string;
  branchId: string;
  branchIsActive: boolean;
  branchName: string;
  code: string;
  hasActiveCashSession: boolean;
  id: string;
  lastClosedAt?: string | null;
  lastOpenedAt?: string | null;
  name: string;
  readiness: AdminWorkstationReadiness;
  status: AdminWorkstationStatus;
  updatedAt?: string | null;
  warnings: AdminWorkstationWarning[];
}

export interface AdminWorkstationOverview {
  code: string;
  createdAt?: string | null;
  id: string;
  name: string;
  readiness: AdminWorkstationReadiness;
  status: AdminWorkstationStatus;
  updatedAt?: string | null;
}

export interface AdminWorkstationBranchRelationship {
  branchCode: string;
  branchId: string;
  branchIsActive: boolean;
  branchName: string;
  branchTimezone: string;
}

export interface AdminWorkstationOperationalConfig {
  isActive: boolean;
  posEnabled: boolean;
}

export interface AdminWorkstationCashSessionSummary {
  closedAt?: string | null;
  id: string;
  openedAt: string;
  openedByUserId?: string | null;
  openedByUserName?: string | null;
  openingAmount: string;
  status: string;
}

export interface AdminWorkstationCashSessionContext {
  activeSession?: AdminWorkstationCashSessionSummary | null;
  lastClosedSession?: AdminWorkstationCashSessionSummary | null;
}

export interface AdminWorkstationAccessUser {
  isActive: boolean;
  userEmail: string;
  userId: string;
  userName: string;
}

export interface AdminWorkstationAccessContext {
  activeAssignedUserCount: number;
  assignedUserCount: number;
  users: AdminWorkstationAccessUser[];
}

export interface AdminWorkstationAvailableActions {
  canActivate: boolean;
  canDeactivate: boolean;
  canEdit: boolean;
  canOpenBranch: boolean;
  canOpenCashSession: boolean;
}

export interface AdminWorkstationDetail {
  accessContext: AdminWorkstationAccessContext;
  availableActions: AdminWorkstationAvailableActions;
  branchRelationship: AdminWorkstationBranchRelationship;
  cashSessionContext: AdminWorkstationCashSessionContext;
  operationalConfig: AdminWorkstationOperationalConfig;
  overview: AdminWorkstationOverview;
  warnings: AdminWorkstationWarning[];
}

export interface AdminWorkstationCreatePayload {
  branchId: string;
  code: string;
  isActive: boolean;
  name: string;
}

export interface AdminWorkstationUpdatePayload {
  branchId?: string | null;
  code?: string | null;
  isActive?: boolean | null;
  name?: string | null;
}

export interface AdminWorkstationListFilters {
  branchId?: string | null;
  cashSessionState?: AdminWorkstationCashSessionState;
  page: number;
  pageSize: number;
  readiness?: AdminWorkstationReadiness | "all";
  search?: string;
  status?: AdminWorkstationStatus | "all";
  warningState?: AdminWorkstationWarningState;
}

export interface AdminWorkstationMetrics {
  activeWorkstations: string;
  inactiveWorkstations: string;
  totalWorkstations: string;
  withOpenCashSession: string;
  withWarnings: string;
  withoutActiveBranch: string;
}

export interface AdminWorkstationFilterOptions {
  branches: AdminWorkstationFilterOption[];
}

export interface AdminWorkstationBackendContract {
  createEndpoint: "POST /v1/admin/workstations";
  detailEndpoint: "GET /v1/admin/workstations/{id}";
  listEndpoint: "GET /v1/admin/workstations";
  updateEndpoint: "PATCH /v1/admin/workstations/{id}";
}

export interface AdminWorkstationListResponse {
  backendContract: AdminWorkstationBackendContract;
  filterOptions: AdminWorkstationFilterOptions;
  isBackendConnected: boolean;
  items: AdminWorkstationListItem[];
  metrics: AdminWorkstationMetrics;
  page: number;
  pageSize: number;
  total: number;
}
