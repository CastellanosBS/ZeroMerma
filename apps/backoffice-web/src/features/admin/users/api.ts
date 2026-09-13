import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminUserBackendContract,
  AdminUserBranchAssignment,
  AdminUserCreatePayload,
  AdminUserDetail,
  AdminUserFilterOption,
  AdminUserListFilters,
  AdminUserListItem,
  AdminUserListResponse,
  AdminUserLockPayload,
  AdminUserStatusPayload,
  AdminUserUpdatePayload,
  AdminUserRoleAssignmentPayload,
} from "./types";

type ApiBackendContract = components["schemas"]["AdminUserBackendContractView"];
type ApiBranchAssignment = components["schemas"]["AdminUserBranchAssignmentView"];
type ApiCreate = components["schemas"]["AdminUserCreateRequest"];
type ApiDetail = components["schemas"]["AdminUserDetailView"];
type ApiListItem = components["schemas"]["AdminUserListItemView"];
type ApiListResponse = components["schemas"]["AdminUsersListResponse"];
type ApiLock = components["schemas"]["AdminUserLockRequest"];
type ApiStatus = components["schemas"]["AdminUserStatusChangeRequest"];
type ApiUpdate = components["schemas"]["AdminUserUpdateRequest"];

export const adminUserBackendContract: AdminUserBackendContract = {
  branchAssignmentEndpoint: "POST /v1/admin/users/{id}/branch-assignments",
  createEndpoint: "POST /v1/admin/users",
  detailEndpoint: "GET /v1/admin/users/{id}",
  invitationSupported: false,
  listEndpoint: "GET /v1/admin/users",
  lockEndpoint: "POST /v1/admin/users/{id}/lock",
  passwordResetSupported: false,
  roleAssignmentSupported: true,
  sessionRevocationSupported: false,
  statusEndpoint: "POST /v1/admin/users/{id}/status",
  unlockEndpoint: "POST /v1/admin/users/{id}/unlock",
  updateEndpoint: "PATCH /v1/admin/users/{id}",
};

function appendOptionalParam(
  params: URLSearchParams,
  key: string,
  value: string | null | undefined,
) {
  if (!value || value === "all") {
    return;
  }
  params.set(key, value);
}

function mapOption(option: { id: string; label: string }): AdminUserFilterOption {
  return { id: option.id, label: option.label };
}

function mapBackendContract(contract?: ApiBackendContract): AdminUserBackendContract {
  if (!contract) {
    return adminUserBackendContract;
  }
  return {
    branchAssignmentEndpoint: contract.branch_assignment_endpoint,
    createEndpoint: contract.create_endpoint,
    detailEndpoint: contract.detail_endpoint,
    invitationSupported: contract.invitation_supported,
    listEndpoint: contract.list_endpoint,
    lockEndpoint: contract.lock_endpoint,
    passwordResetSupported: contract.password_reset_supported,
    roleAssignmentSupported: contract.role_assignment_supported,
    sessionRevocationSupported: contract.session_revocation_supported,
    statusEndpoint: contract.status_endpoint,
    unlockEndpoint: contract.unlock_endpoint,
    updateEndpoint: contract.update_endpoint,
  };
}

export function mapAdminUserListItemFromApi(item: ApiListItem): AdminUserListItem {
  return {
    allowedSurfaces: item.allowed_surfaces,
    branchCount: item.branch_count,
    branchNames: item.branch_names,
    createdAt: item.created_at,
    defaultSurface: item.default_surface,
    email: item.email,
    fullName: item.full_name,
    id: item.id,
    lastLoginAt: item.last_login_at ?? null,
    roleCount: item.role_count,
    roleNames: item.role_names ?? [],
    status: item.status,
    updatedAt: item.updated_at,
    warningState: item.warning_state,
    warnings: item.warnings ?? [],
  };
}

function mapBranchAssignmentFromApi(item: ApiBranchAssignment): AdminUserBranchAssignment {
  return {
    assignedAt: item.assigned_at,
    assignmentId: item.assignment_id,
    branchCode: item.branch_code,
    branchId: item.branch_id,
    branchName: item.branch_name,
    isActive: item.is_active,
    isDefault: item.is_default,
    updatedAt: item.updated_at,
  };
}

function mapDetailFromApi(response: ApiDetail): AdminUserDetail {
  const branchAssignments = response.branch_assignments.map(mapBranchAssignmentFromApi);
  const roleItems = response.role_assignments.items ?? [];
  const overviewWarnings = response.warnings ?? [];

  return {
    accountStatus: {
      activeSessionsCount: response.account_status.active_sessions_count ?? null,
      activeSessionsSupported: response.account_status.active_sessions_supported,
      failedLoginCount: response.account_status.failed_login_count ?? null,
      isActive: response.account_status.is_active,
      isLocked: response.account_status.is_locked,
      lastLoginAt: response.account_status.last_login_at ?? null,
      lockReason: response.account_status.lock_reason ?? null,
      passwordResetRequired: response.account_status.password_reset_required,
      pendingInvitation: response.account_status.pending_invitation,
    },
    appAccess: {
      allowedSurfaces: response.app_access.allowed_surfaces,
      backofficeEnabled: response.app_access.backoffice_enabled,
      defaultSurface: response.app_access.default_surface,
      hasBothSurfaces: response.app_access.has_both_surfaces,
      posEnabled: response.app_access.pos_enabled,
    },
    auditTimeline: response.audit_timeline.map((item) => ({
      action: item.action,
      actorId: item.actor_id ?? null,
      id: item.id,
      metadata: item.metadata,
      occurredAt: item.occurred_at,
    })),
    availableActions: {
      canActivate: response.available_actions.can_activate,
      canDeactivate: response.available_actions.can_deactivate,
      canEditAppAccess: response.available_actions.can_edit_app_access,
      canEditBranchAssignments: response.available_actions.can_edit_branch_assignments,
      canEditProfile: response.available_actions.can_edit_profile,
      canEditRoleAssignments: response.available_actions.can_edit_role_assignments,
      canLock: response.available_actions.can_lock,
      canOpenAudit: response.available_actions.can_open_audit,
      canUnlock: response.available_actions.can_unlock,
    },
    branchAssignments,
    operationalContext: {
      activeSessionsSupported: response.operational_context.active_sessions_supported,
      lastWorkstationUsed: response.operational_context.last_workstation_used ?? null,
      openCashSessionsCount: response.operational_context.open_cash_sessions_count,
      recentBackofficeActivityCount: response.operational_context.recent_backoffice_activity_count,
      recentPosActivityCount: response.operational_context.recent_pos_activity_count,
      recentlyOperatedBranches: response.operational_context.recently_operated_branches,
    },
    overview: {
      allowedSurfaces: response.overview.allowed_surfaces,
      branchCount: branchAssignments.filter((assignment) => assignment.isActive).length,
      branchNames: branchAssignments
        .filter((assignment) => assignment.isActive)
        .map((assignment) => assignment.branchName),
      createdAt: response.overview.created_at,
      defaultSurface: response.overview.default_surface,
      email: response.overview.email,
      fullName: response.overview.full_name,
      id: response.overview.id,
      lastLoginAt: response.overview.last_login_at ?? null,
      roleCount: roleItems.length,
      roleNames: roleItems.map((role) => role.role_name),
      status: response.overview.status,
      updatedAt: response.overview.updated_at,
      warningState: response.overview.warning_state,
      warnings: overviewWarnings,
    },
    profile: {
      displayName: response.profile.display_name ?? null,
      email: response.profile.email,
      employeeCode: response.profile.employee_code ?? null,
      fullName: response.profile.full_name,
      notes: response.profile.notes ?? null,
      phone: response.profile.phone ?? null,
    },
    roleAssignments: {
      isSupported: response.role_assignments.is_supported,
      items: roleItems.map((item) => ({
        assignedAt: item.assigned_at ?? null,
        roleDescription: item.role_description ?? null,
        roleId: item.role_id,
        roleName: item.role_name,
        scopeType: item.scope_type,
        branchIds: item.branch_ids,
      })),
      missingContractNote: response.role_assignments.missing_contract_note,
    },
    securityActions: {
      canActivate: response.security_actions.can_activate,
      canDeactivate: response.security_actions.can_deactivate,
      canLock: response.security_actions.can_lock,
      canRevokeSessions: response.security_actions.can_revoke_sessions,
      canSendInvitation: response.security_actions.can_send_invitation,
      canSendPasswordReset: response.security_actions.can_send_password_reset,
      canUnlock: response.security_actions.can_unlock,
      supportsInvitation: response.security_actions.supports_invitation,
      supportsLocking: response.security_actions.supports_locking,
      supportsPasswordReset: response.security_actions.supports_password_reset,
      supportsSessionRevocation: response.security_actions.supports_session_revocation,
    },
    warnings: response.warnings,
  };
}

function mapListFromApi(response: ApiListResponse): AdminUserListResponse {
  return {
    backendContract: mapBackendContract(response.backend_contract),
    filterOptions: {
      appAccess: response.filter_options.app_access.map(mapOption),
      branches: response.filter_options.branches.map((item) => ({
        id: item.id,
        label: item.label,
      })),
      lastLoginStates: response.filter_options.last_login_states.map(mapOption),
      roles: (response.filter_options.roles ?? []).map(mapOption),
      statuses: response.filter_options.statuses.map(mapOption),
      warningStates: response.filter_options.warning_states.map(mapOption),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminUserListItemFromApi),
    metrics: {
      activeUsers: String(response.metrics.active_users),
      backofficeUsers: String(response.metrics.backoffice_users),
      inactiveUsers: String(response.metrics.inactive_users),
      lockedUsers: String(response.metrics.locked_users),
      pendingUsers: String(response.metrics.pending_users),
      posUsers: String(response.metrics.pos_users),
      totalUsers: String(response.metrics.total_users),
      withoutBranch: String(response.metrics.without_branch),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function mapCreatePayload(payload: AdminUserCreatePayload): ApiCreate {
  return {
    allowed_surfaces: payload.allowedSurfaces,
    branch_assignments: payload.branchAssignments.map((item) => ({
      branch_id: item.branchId,
      is_default: item.isDefault,
    })),
    default_surface: payload.defaultSurface,
    email: payload.email,
    full_name: payload.fullName,
    notes: payload.notes,
    phone: payload.phone,
    send_invitation: payload.sendInvitation,
    temporary_password: payload.temporaryPassword,
  };
}

function mapUpdatePayload(payload: AdminUserUpdatePayload): ApiUpdate {
  return {
    allowed_surfaces: payload.allowedSurfaces,
    default_surface: payload.defaultSurface,
    email: payload.email,
    full_name: payload.fullName,
    notes: payload.notes,
    phone: payload.phone,
  };
}

export async function fetchAdminUsers(
  accessToken: string,
  filters: AdminUserListFilters,
): Promise<AdminUserListResponse> {
  const params = new URLSearchParams();
  appendOptionalParam(params, "search", filters.search);
  appendOptionalParam(params, "status", filters.status);
  appendOptionalParam(params, "app_access", filters.appAccess);
  appendOptionalParam(params, "branch_id", filters.branchId);
  appendOptionalParam(params, "role_id", filters.roleId);
  appendOptionalParam(params, "last_login_state", filters.lastLoginState);
  appendOptionalParam(params, "warning_state", filters.warningState);
  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));

  const suffix = params.toString();
  const response = await requestJson<ApiListResponse>({
    accessToken,
    path: `/v1/admin/users${suffix ? `?${suffix}` : ""}`,
  });
  return mapListFromApi(response);
}

export async function fetchAdminUserDetail(
  accessToken: string,
  userId: string,
): Promise<AdminUserDetail> {
  const response = await requestJson<ApiDetail>({
    accessToken,
    path: `/v1/admin/users/${userId}`,
  });
  return mapDetailFromApi(response);
}

export async function createAdminUser(
  accessToken: string,
  payload: AdminUserCreatePayload,
): Promise<AdminUserDetail> {
  const response = await requestJson<ApiDetail>({
    accessToken,
    body: mapCreatePayload(payload),
    method: "POST",
    path: "/v1/admin/users",
  });
  return mapDetailFromApi(response);
}

export async function updateAdminUser(
  accessToken: string,
  userId: string,
  payload: AdminUserUpdatePayload,
): Promise<AdminUserDetail> {
  const response = await requestJson<ApiDetail>({
    accessToken,
    body: mapUpdatePayload(payload),
    method: "PATCH",
    path: `/v1/admin/users/${userId}`,
  });
  return mapDetailFromApi(response);
}

export async function changeAdminUserStatus(
  accessToken: string,
  userId: string,
  payload: AdminUserStatusPayload,
): Promise<AdminUserDetail> {
  const body: ApiStatus = { is_active: payload.isActive };
  const response = await requestJson<ApiDetail>({
    accessToken,
    body,
    method: "POST",
    path: `/v1/admin/users/${userId}/status`,
  });
  return mapDetailFromApi(response);
}

export async function lockAdminUser(
  accessToken: string,
  userId: string,
  payload: AdminUserLockPayload,
): Promise<AdminUserDetail> {
  const body: ApiLock = { reason: payload.reason };
  const response = await requestJson<ApiDetail>({
    accessToken,
    body,
    method: "POST",
    path: `/v1/admin/users/${userId}/lock`,
  });
  return mapDetailFromApi(response);
}

export async function unlockAdminUser(
  accessToken: string,
  userId: string,
): Promise<AdminUserDetail> {
  const response = await requestJson<ApiDetail>({
    accessToken,
    method: "POST",
    path: `/v1/admin/users/${userId}/unlock`,
  });
  return mapDetailFromApi(response);
}

export async function addAdminUserBranchAssignment(
  accessToken: string,
  userId: string,
  branchId: string,
  isDefault: boolean,
): Promise<AdminUserDetail> {
  const response = await requestJson<ApiDetail>({
    accessToken,
    body: { branch_id: branchId, is_default: isDefault },
    method: "POST",
    path: `/v1/admin/users/${userId}/branch-assignments`,
  });
  return mapDetailFromApi(response);
}

export async function deactivateAdminUserBranchAssignment(
  accessToken: string,
  userId: string,
  branchId: string,
): Promise<AdminUserDetail> {
  const response = await requestJson<ApiDetail>({
    accessToken,
    method: "POST",
    path: `/v1/admin/users/${userId}/branch-assignments/${branchId}/deactivate`,
  });
  return mapDetailFromApi(response);
}

export async function assignAdminUserRole(
  accessToken: string,
  userId: string,
  payload: AdminUserRoleAssignmentPayload,
): Promise<AdminUserDetail> {
  return mapDetailFromApi(
    await requestJson<ApiDetail>({
      accessToken,
      path: `/v1/admin/users/${userId}/roles`,
      method: "POST",
      body: payload,
    }),
  );
}

export async function removeAdminUserRole(
  accessToken: string,
  userId: string,
  roleId: string,
): Promise<AdminUserDetail> {
  return mapDetailFromApi(
    await requestJson<ApiDetail>({
      accessToken,
      path: `/v1/admin/users/${userId}/roles/${roleId}/remove`,
      method: "POST",
    }),
  );
}
