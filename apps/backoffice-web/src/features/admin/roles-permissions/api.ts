import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminPermission,
  AdminPermissionGroup,
  AdminPermissionsResponse,
  AdminRoleBackendContract,
  AdminRoleCreatePayload,
  AdminRoleDetail,
  AdminRoleFilterOption,
  AdminRoleListFilters,
  AdminRoleListItem,
  AdminRoleListResponse,
  AdminRoleUpdatePayload,
} from "./types";

type ApiBackendContract = components["schemas"]["AdminRoleBackendContractView"];
type ApiCreate = components["schemas"]["AdminRoleCreateRequest"];
type ApiDetail = components["schemas"]["AdminRoleDetailView"];
type ApiListItem = components["schemas"]["AdminRoleListItemView"];
type ApiListResponse = components["schemas"]["AdminRolesListResponse"];
type ApiPermission = components["schemas"]["AdminPermissionView"];
type ApiPermissionGroup = components["schemas"]["AdminPermissionGroupView"];
type ApiPermissionsResponse = components["schemas"]["AdminPermissionsResponse"];
type ApiStatus = components["schemas"]["AdminRoleStatusChangeRequest"];
type ApiUpdate = components["schemas"]["AdminRoleUpdateRequest"];

export const adminRoleBackendContract: AdminRoleBackendContract = {
  assignUserEndpoint: "POST /v1/admin/roles/{id}/users/{user_id}",
  createEndpoint: "POST /v1/admin/roles",
  destructiveDeleteSupported: false,
  detailEndpoint: "GET /v1/admin/roles/{id}",
  duplicateSupported: false,
  listEndpoint: "GET /v1/admin/roles",
  permissionsEndpoint: "GET /v1/admin/roles/permissions",
  removeUserEndpoint: "POST /v1/admin/roles/{id}/users/{user_id}/remove",
  scopedRolesSupported: false,
  statusEndpoint: "POST /v1/admin/roles/{id}/status",
  updateEndpoint: "PATCH /v1/admin/roles/{id}",
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

function mapOption(option: { id: string; label: string }): AdminRoleFilterOption {
  return { id: option.id, label: option.label };
}

function mapBackendContract(contract?: ApiBackendContract): AdminRoleBackendContract {
  if (!contract) {
    return adminRoleBackendContract;
  }
  return {
    assignUserEndpoint: contract.assign_user_endpoint,
    createEndpoint: contract.create_endpoint,
    destructiveDeleteSupported: contract.destructive_delete_supported,
    detailEndpoint: contract.detail_endpoint,
    duplicateSupported: contract.duplicate_supported,
    listEndpoint: contract.list_endpoint,
    permissionsEndpoint: contract.permissions_endpoint,
    removeUserEndpoint: contract.remove_user_endpoint,
    scopedRolesSupported: contract.scoped_roles_supported,
    statusEndpoint: contract.status_endpoint,
    updateEndpoint: contract.update_endpoint,
  };
}

function mapPermission(item: ApiPermission): AdminPermission {
  return {
    action: item.action,
    code: item.code,
    description: item.description ?? null,
    id: item.id,
    isEnabled: item.is_enabled,
    isSensitive: item.is_sensitive,
    label: item.label,
    module: item.module,
    moduleLabel: item.module_label,
    surfaces: item.surfaces,
  };
}

function mapPermissionGroup(group: ApiPermissionGroup): AdminPermissionGroup {
  return {
    label: group.label,
    module: group.module,
    permissions: group.permissions.map(mapPermission),
  };
}

export function mapAdminRoleListItemFromApi(item: ApiListItem): AdminRoleListItem {
  return {
    assignedUserCount: item.assigned_user_count,
    code: item.code,
    description: item.description ?? null,
    id: item.id,
    isHighPrivilege: item.is_high_privilege,
    isSystem: item.is_system,
    name: item.name,
    permissionCount: item.permission_count,
    scopeSummary: item.scope_summary,
    status: item.status,
    surfaces: item.surfaces,
    updatedAt: item.updated_at,
    warningState: item.warning_state,
    warnings: item.warnings ?? [],
  };
}

function mapListFromApi(response: ApiListResponse): AdminRoleListResponse {
  return {
    backendContract: mapBackendContract(response.backend_contract),
    filterOptions: {
      appSurfaces: response.filter_options.app_surfaces.map(mapOption),
      hasUsers: response.filter_options.has_users.map(mapOption),
      highPrivilege: response.filter_options.high_privilege.map(mapOption),
      permissionModules: response.filter_options.permission_modules.map(mapOption),
      statuses: response.filter_options.statuses.map(mapOption),
      systemStates: response.filter_options.system_states.map(mapOption),
      warningStates: response.filter_options.warning_states.map(mapOption),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminRoleListItemFromApi),
    metrics: {
      activeRoles: String(response.metrics.active_roles),
      backofficeRoles: String(response.metrics.backoffice_roles),
      highPrivilege: String(response.metrics.high_privilege),
      inactiveRoles: String(response.metrics.inactive_roles),
      posRoles: String(response.metrics.pos_roles),
      totalRoles: String(response.metrics.total_roles),
      withUsers: String(response.metrics.with_users),
      withWarnings: String(response.metrics.with_warnings),
      withoutUsers: String(response.metrics.without_users),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function mapDetailFromApi(response: ApiDetail): AdminRoleDetail {
  return {
    accessSurfaces: {
      backofficeEnabled: response.access_surfaces.backoffice_enabled,
      grantsBothSurfaces: response.access_surfaces.grants_both_surfaces,
      note: response.access_surfaces.note,
      posEnabled: response.access_surfaces.pos_enabled,
      surfaces: response.access_surfaces.surfaces,
    },
    assignedUsers: response.assigned_users.map((item) => ({
      assignedAt: item.assigned_at,
      branchSummary: item.branch_summary,
      email: item.email,
      fullName: item.full_name,
      status: item.status,
      surfaces: item.surfaces,
      userId: item.user_id,
    })),
    auditHistory: response.audit_history.map((item) => ({
      action: item.action,
      actorId: item.actor_id ?? null,
      id: item.id,
      metadata: item.metadata,
      occurredAt: item.occurred_at,
    })),
    availableActions: {
      canActivate: response.available_actions.can_activate,
      canAssignUsers: response.available_actions.can_assign_users,
      canDeactivate: response.available_actions.can_deactivate,
      canDelete: response.available_actions.can_delete,
      canDuplicate: response.available_actions.can_duplicate,
      canEdit: response.available_actions.can_edit,
      canOpenAudit: response.available_actions.can_open_audit,
      canRemoveUsers: response.available_actions.can_remove_users,
    },
    overview: {
      ...mapAdminRoleListItemFromApi({
        assigned_user_count: response.assigned_users.length,
        code: response.overview.code,
        description: response.overview.description,
        id: response.overview.id,
        is_high_privilege: response.overview.is_high_privilege,
        is_system: response.overview.is_system,
        name: response.overview.name,
        permission_count: response.permission_matrix.reduce(
          (count, group) => count + group.permissions.filter((permission) => permission.is_enabled).length,
          0,
        ),
        scope_summary: response.scopes.scope_summary,
        status: response.overview.status,
        surfaces: response.overview.surfaces,
        updated_at: response.overview.updated_at,
        warning_state: response.overview.warning_state,
        warnings: response.warnings,
      }),
      createdAt: response.overview.created_at,
    },
    permissionMatrix: response.permission_matrix.map(mapPermissionGroup),
    scopes: {
      isSupported: response.scopes.is_supported,
      missingContractNote: response.scopes.missing_contract_note,
      scopeSummary: response.scopes.scope_summary,
    },
    sensitivePermissions: response.sensitive_permissions.map(mapPermission),
    warnings: response.warnings,
  };
}

function mapCreatePayload(payload: AdminRoleCreatePayload): ApiCreate {
  return {
    code: payload.code,
    confirmed_high_risk_change: payload.confirmedHighRiskChange,
    description: payload.description,
    is_active: payload.isActive,
    name: payload.name,
    permission_codes: payload.permissionCodes,
    surfaces: payload.surfaces,
  };
}

function mapUpdatePayload(payload: AdminRoleUpdatePayload): ApiUpdate {
  return {
    confirmed_high_risk_change: payload.confirmedHighRiskChange,
    description: payload.description,
    is_active: payload.isActive,
    name: payload.name,
    permission_codes: payload.permissionCodes,
    surfaces: payload.surfaces,
  };
}

export async function fetchAdminRoles(
  accessToken: string,
  filters: AdminRoleListFilters,
): Promise<AdminRoleListResponse> {
  const params = new URLSearchParams();
  appendOptionalParam(params, "search", filters.search);
  appendOptionalParam(params, "status", filters.status);
  appendOptionalParam(params, "app_surface", filters.appSurface);
  appendOptionalParam(params, "high_privilege", filters.highPrivilege);
  appendOptionalParam(params, "has_users", filters.hasUsers);
  appendOptionalParam(params, "permission_module", filters.permissionModule);
  appendOptionalParam(params, "warning_state", filters.warningState);
  appendOptionalParam(params, "system_state", filters.systemState);
  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));

  const suffix = params.toString();
  const response = await requestJson<ApiListResponse>({
    accessToken,
    path: `/v1/admin/roles${suffix ? `?${suffix}` : ""}`,
  });
  return mapListFromApi(response);
}

export async function fetchAdminRoleDetail(
  accessToken: string,
  roleId: string,
): Promise<AdminRoleDetail> {
  const response = await requestJson<ApiDetail>({
    accessToken,
    path: `/v1/admin/roles/${roleId}`,
  });
  return mapDetailFromApi(response);
}

export async function fetchAdminRolePermissions(
  accessToken: string,
): Promise<AdminPermissionsResponse> {
  const response = await requestJson<ApiPermissionsResponse>({
    accessToken,
    path: "/v1/admin/roles/permissions",
  });
  return {
    groups: response.groups.map(mapPermissionGroup),
    sensitivePermissionCodes: response.sensitive_permission_codes,
  };
}

export async function createAdminRole(
  accessToken: string,
  payload: AdminRoleCreatePayload,
): Promise<AdminRoleDetail> {
  const response = await requestJson<ApiDetail>({
    accessToken,
    body: mapCreatePayload(payload),
    method: "POST",
    path: "/v1/admin/roles",
  });
  return mapDetailFromApi(response);
}

export async function updateAdminRole(
  accessToken: string,
  roleId: string,
  payload: AdminRoleUpdatePayload,
): Promise<AdminRoleDetail> {
  const response = await requestJson<ApiDetail>({
    accessToken,
    body: mapUpdatePayload(payload),
    method: "PATCH",
    path: `/v1/admin/roles/${roleId}`,
  });
  return mapDetailFromApi(response);
}

export async function changeAdminRoleStatus(
  accessToken: string,
  roleId: string,
  isActive: boolean,
  confirmedHighRiskChange: boolean,
): Promise<AdminRoleDetail> {
  const body: ApiStatus = {
    confirmed_high_risk_change: confirmedHighRiskChange,
    is_active: isActive,
  };
  const response = await requestJson<ApiDetail>({
    accessToken,
    body,
    method: "POST",
    path: `/v1/admin/roles/${roleId}/status`,
  });
  return mapDetailFromApi(response);
}

export async function assignAdminRoleToUser(
  accessToken: string,
  roleId: string,
  userId: string,
): Promise<AdminRoleDetail> {
  const response = await requestJson<ApiDetail>({
    accessToken,
    method: "POST",
    path: `/v1/admin/roles/${roleId}/users/${userId}`,
  });
  return mapDetailFromApi(response);
}

export async function removeAdminRoleFromUser(
  accessToken: string,
  roleId: string,
  userId: string,
): Promise<AdminRoleDetail> {
  const response = await requestJson<ApiDetail>({
    accessToken,
    method: "POST",
    path: `/v1/admin/roles/${roleId}/users/${userId}/remove`,
  });
  return mapDetailFromApi(response);
}
