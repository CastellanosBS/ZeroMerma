import type { components } from "@zeromerma/api-client";

export type AdminUserRoleAssignmentPayload =
  components["schemas"]["AdminUserRoleAssignmentRequest"];
export type AdminUserStatus = "active" | "inactive" | "locked";
export type AdminUserSurface = "POS" | "BACKOFFICE";
export type AdminUserWarningState = "ready" | "warning" | "blocked";

export interface AdminUserWarning {
  code: string;
  message: string;
  severity: "info" | "warning" | "critical";
}

export interface AdminUserFilterOption {
  id: string;
  label: string;
}

export interface AdminUserBranchFilterOption {
  id: string;
  label: string;
}

export interface AdminUserBackendContract {
  branchAssignmentEndpoint: string;
  createEndpoint: string;
  detailEndpoint: string;
  invitationSupported: boolean;
  listEndpoint: string;
  lockEndpoint: string;
  passwordResetSupported: boolean;
  roleAssignmentSupported: boolean;
  sessionRevocationSupported: boolean;
  statusEndpoint: string;
  unlockEndpoint: string;
  updateEndpoint: string;
}

export interface AdminUserFilterOptions {
  appAccess: AdminUserFilterOption[];
  branches: AdminUserBranchFilterOption[];
  lastLoginStates: AdminUserFilterOption[];
  roles: AdminUserFilterOption[];
  statuses: AdminUserFilterOption[];
  warningStates: AdminUserFilterOption[];
}

export interface AdminUserListFilters {
  appAccess: string;
  branchId: string;
  lastLoginState: string;
  page: number;
  pageSize: number;
  roleId: string;
  search: string;
  status: string;
  warningState: string;
}

export interface AdminUserListItem {
  allowedSurfaces: AdminUserSurface[];
  branchCount: number;
  branchNames: string[];
  createdAt: string;
  defaultSurface: AdminUserSurface;
  email: string;
  fullName: string;
  id: string;
  lastLoginAt: string | null;
  roleCount: number;
  roleNames: string[];
  status: AdminUserStatus;
  updatedAt: string;
  warningState: AdminUserWarningState;
  warnings: AdminUserWarning[];
}

export interface AdminUserMetrics {
  activeUsers: string;
  backofficeUsers: string;
  inactiveUsers: string;
  lockedUsers: string;
  pendingUsers: string;
  posUsers: string;
  totalUsers: string;
  withoutBranch: string;
}

export interface AdminUserListResponse {
  backendContract: AdminUserBackendContract;
  filterOptions: AdminUserFilterOptions;
  isBackendConnected: boolean;
  items: AdminUserListItem[];
  metrics: AdminUserMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminUserBranchAssignment {
  assignedAt: string;
  assignmentId: string;
  branchCode: string;
  branchId: string;
  branchName: string;
  isActive: boolean;
  isDefault: boolean;
  updatedAt: string;
}

export interface AdminUserRoleAssignment {
  assignedAt: string | null;
  roleDescription: string | null;
  roleId: string;
  roleName: string;
  scopeType: AdminUserRoleAssignmentPayload["scope_type"];
  branchIds: string[];
}

export interface AdminUserDetail {
  accountStatus: {
    activeSessionsCount: number | null;
    activeSessionsSupported: boolean;
    failedLoginCount: number | null;
    isActive: boolean;
    isLocked: boolean;
    lastLoginAt: string | null;
    lockReason: string | null;
    passwordResetRequired: boolean;
    pendingInvitation: boolean;
  };
  appAccess: {
    allowedSurfaces: AdminUserSurface[];
    backofficeEnabled: boolean;
    defaultSurface: AdminUserSurface;
    hasBothSurfaces: boolean;
    posEnabled: boolean;
  };
  auditTimeline: Array<{
    action: string;
    actorId: string | null;
    id: string;
    metadata: Record<string, unknown>;
    occurredAt: string;
  }>;
  availableActions: {
    canActivate: boolean;
    canDeactivate: boolean;
    canEditAppAccess: boolean;
    canEditBranchAssignments: boolean;
    canEditProfile: boolean;
    canEditRoleAssignments: boolean;
    canLock: boolean;
    canOpenAudit: boolean;
    canUnlock: boolean;
  };
  branchAssignments: AdminUserBranchAssignment[];
  operationalContext: {
    activeSessionsSupported: boolean;
    lastWorkstationUsed: string | null;
    openCashSessionsCount: number;
    recentBackofficeActivityCount: number;
    recentPosActivityCount: number;
    recentlyOperatedBranches: string[];
  };
  overview: AdminUserListItem;
  profile: {
    displayName: string | null;
    email: string;
    employeeCode: string | null;
    fullName: string;
    notes: string | null;
    phone: string | null;
  };
  roleAssignments: {
    isSupported: boolean;
    items: AdminUserRoleAssignment[];
    missingContractNote: string;
  };
  securityActions: {
    canActivate: boolean;
    canDeactivate: boolean;
    canLock: boolean;
    canRevokeSessions: boolean;
    canSendInvitation: boolean;
    canSendPasswordReset: boolean;
    canUnlock: boolean;
    supportsInvitation: boolean;
    supportsLocking: boolean;
    supportsPasswordReset: boolean;
    supportsSessionRevocation: boolean;
  };
  warnings: AdminUserWarning[];
}

export interface AdminUserCreatePayload {
  allowedSurfaces: AdminUserSurface[];
  branchAssignments: Array<{ branchId: string; isDefault: boolean }>;
  defaultSurface: AdminUserSurface | null;
  email: string;
  fullName: string;
  notes: string | null;
  phone: string | null;

  sendInvitation: boolean;
  temporaryPassword: string | null;
}

export interface AdminUserUpdatePayload {
  allowedSurfaces?: AdminUserSurface[];
  defaultSurface?: AdminUserSurface | null;
  email?: string;
  fullName?: string;
  notes?: string | null;
  phone?: string | null;
}

export interface AdminUserStatusPayload {
  isActive: boolean;
}

export interface AdminUserLockPayload {
  reason: string | null;
}
