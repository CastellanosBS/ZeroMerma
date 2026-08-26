export type AdminRoleStatus = "active" | "inactive";
export type AdminRoleSurface = "POS" | "BACKOFFICE";
export type AdminRoleWarningState = "ready" | "warning" | "blocked";

export interface AdminRoleWarning {
  code: string;
  message: string;
  severity: "info" | "warning" | "critical";
}

export interface AdminRoleFilterOption {
  id: string;
  label: string;
}

export interface AdminRoleBackendContract {
  assignUserEndpoint: string;
  createEndpoint: string;
  destructiveDeleteSupported: boolean;
  detailEndpoint: string;
  duplicateSupported: boolean;
  listEndpoint: string;
  permissionsEndpoint: string;
  removeUserEndpoint: string;
  scopedRolesSupported: boolean;
  statusEndpoint: string;
  updateEndpoint: string;
}

export interface AdminRoleFilterOptions {
  appSurfaces: AdminRoleFilterOption[];
  hasUsers: AdminRoleFilterOption[];
  highPrivilege: AdminRoleFilterOption[];
  permissionModules: AdminRoleFilterOption[];
  statuses: AdminRoleFilterOption[];
  systemStates: AdminRoleFilterOption[];
  warningStates: AdminRoleFilterOption[];
}

export interface AdminRoleListFilters {
  appSurface: string;
  hasUsers: string;
  highPrivilege: string;
  page: number;
  pageSize: number;
  permissionModule: string;
  search: string;
  status: string;
  systemState: string;
  warningState: string;
}

export interface AdminRoleListItem {
  assignedUserCount: number;
  code: string;
  description: string | null;
  id: string;
  isHighPrivilege: boolean;
  isSystem: boolean;
  name: string;
  permissionCount: number;
  scopeSummary: string;
  status: AdminRoleStatus;
  surfaces: AdminRoleSurface[];
  updatedAt: string;
  warningState: AdminRoleWarningState;
  warnings: AdminRoleWarning[];
}

export interface AdminRoleMetrics {
  activeRoles: string;
  backofficeRoles: string;
  highPrivilege: string;
  inactiveRoles: string;
  posRoles: string;
  totalRoles: string;
  withUsers: string;
  withWarnings: string;
  withoutUsers: string;
}

export interface AdminRoleListResponse {
  backendContract: AdminRoleBackendContract;
  filterOptions: AdminRoleFilterOptions;
  isBackendConnected: boolean;
  items: AdminRoleListItem[];
  metrics: AdminRoleMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminPermission {
  action: string;
  code: string;
  description: string | null;
  id: string;
  isEnabled: boolean;
  isSensitive: boolean;
  label: string;
  module: string;
  moduleLabel: string;
  surfaces: AdminRoleSurface[];
}

export interface AdminPermissionGroup {
  label: string;
  module: string;
  permissions: AdminPermission[];
}

export interface AdminRoleAssignedUser {
  assignedAt: string;
  branchSummary: string;
  email: string;
  fullName: string;
  status: string;
  surfaces: AdminRoleSurface[];
  userId: string;
}

export interface AdminRoleDetail {
  accessSurfaces: {
    backofficeEnabled: boolean;
    grantsBothSurfaces: boolean;
    note: string;
    posEnabled: boolean;
    surfaces: AdminRoleSurface[];
  };
  assignedUsers: AdminRoleAssignedUser[];
  auditHistory: Array<{
    action: string;
    actorId: string | null;
    id: string;
    metadata: Record<string, unknown>;
    occurredAt: string;
  }>;
  availableActions: {
    canActivate: boolean;
    canAssignUsers: boolean;
    canDeactivate: boolean;
    canDelete: boolean;
    canDuplicate: boolean;
    canEdit: boolean;
    canOpenAudit: boolean;
    canRemoveUsers: boolean;
  };
  overview: AdminRoleListItem & {
    createdAt: string;
  };
  permissionMatrix: AdminPermissionGroup[];
  scopes: {
    isSupported: boolean;
    missingContractNote: string;
    scopeSummary: string;
  };
  sensitivePermissions: AdminPermission[];
  warnings: AdminRoleWarning[];
}

export interface AdminPermissionsResponse {
  groups: AdminPermissionGroup[];
  sensitivePermissionCodes: string[];
}

export interface AdminRoleCreatePayload {
  code: string;
  confirmedHighRiskChange: boolean;
  description: string | null;
  isActive: boolean;
  name: string;
  permissionCodes: string[];
  surfaces: AdminRoleSurface[];
}

export interface AdminRoleUpdatePayload {
  confirmedHighRiskChange: boolean;
  description?: string | null;
  isActive?: boolean;
  name?: string;
  permissionCodes?: string[];
  surfaces?: AdminRoleSurface[];
}

