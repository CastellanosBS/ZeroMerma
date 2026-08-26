import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminWorkstationBackendContract,
  AdminWorkstationCreatePayload,
  AdminWorkstationDetail,
  AdminWorkstationFilterOption,
  AdminWorkstationListFilters,
  AdminWorkstationListItem,
  AdminWorkstationListResponse,
  AdminWorkstationUpdatePayload,
  AdminWorkstationWarning,
} from "./types";

export const adminWorkstationsBackendContract: AdminWorkstationBackendContract = {
  createEndpoint: "POST /v1/admin/workstations",
  detailEndpoint: "GET /v1/admin/workstations/{id}",
  listEndpoint: "GET /v1/admin/workstations",
  updateEndpoint: "PATCH /v1/admin/workstations/{id}",
};

type AdminWorkstationApiFilterOption = components["schemas"]["AdminBranchFilterOptionView"];
type AdminWorkstationApiWarning = components["schemas"]["AdminBranchWarningView"];
type AdminWorkstationApiListItem = components["schemas"]["AdminWorkstationListItemView"];
type AdminWorkstationsApiListResponse = components["schemas"]["AdminWorkstationsListResponse"];
type AdminWorkstationApiDetail = components["schemas"]["AdminWorkstationDetailView"];
type AdminWorkstationApiCreatePayload = components["schemas"]["AdminWorkstationCreateRequest"];
type AdminWorkstationApiUpdatePayload = components["schemas"]["AdminWorkstationUpdateRequest"];

function appendOptionalParam(params: URLSearchParams, key: string, value: string | null | undefined) {
  if (!value || value === "all") {
    return;
  }

  params.set(key, value);
}

function mapMetric(value: number): string {
  return String(value);
}

function mapFilterOptions(options: AdminWorkstationApiFilterOption[]): AdminWorkstationFilterOption[] {
  return options.map((option) => ({
    id: option.id,
    label: option.label,
  }));
}

function mapWarningFromApi(warning: AdminWorkstationApiWarning): AdminWorkstationWarning {
  return {
    code: warning.code,
    message: warning.message,
    severity: warning.severity,
  };
}

export function mapAdminWorkstationListItemFromApi(
  item: AdminWorkstationApiListItem,
): AdminWorkstationListItem {
  return {
    activeCashSessionId: item.active_cash_session_id ?? null,
    branchCode: item.branch_code,
    branchId: item.branch_id,
    branchIsActive: item.branch_is_active,
    branchName: item.branch_name,
    code: item.code,
    hasActiveCashSession: item.has_active_cash_session,
    id: item.id,
    lastClosedAt: item.last_closed_at ?? null,
    lastOpenedAt: item.last_opened_at ?? null,
    name: item.name,
    readiness: item.readiness,
    status: item.status,
    updatedAt: item.updated_at ?? null,
    warnings: item.warnings.map(mapWarningFromApi),
  };
}

export function mapAdminWorkstationDetailFromApi(
  item: AdminWorkstationApiDetail,
): AdminWorkstationDetail {
  return {
    accessContext: {
      activeAssignedUserCount: item.access_context.active_assigned_user_count,
      assignedUserCount: item.access_context.assigned_user_count,
      users: item.access_context.users.map((user) => ({
        isActive: user.is_active,
        userEmail: user.user_email,
        userId: user.user_id,
        userName: user.user_name,
      })),
    },
    availableActions: {
      canActivate: item.available_actions.can_activate,
      canDeactivate: item.available_actions.can_deactivate,
      canEdit: item.available_actions.can_edit,
      canOpenBranch: item.available_actions.can_open_branch,
      canOpenCashSession: item.available_actions.can_open_cash_session,
    },
    branchRelationship: {
      branchCode: item.branch_relationship.branch_code,
      branchId: item.branch_relationship.branch_id,
      branchIsActive: item.branch_relationship.branch_is_active,
      branchName: item.branch_relationship.branch_name,
      branchTimezone: item.branch_relationship.branch_timezone,
    },
    cashSessionContext: {
      activeSession: item.cash_session_context.active_session
        ? {
            closedAt: item.cash_session_context.active_session.closed_at ?? null,
            id: item.cash_session_context.active_session.id,
            openedAt: item.cash_session_context.active_session.opened_at,
            openedByUserId: item.cash_session_context.active_session.opened_by_user_id ?? null,
            openedByUserName: item.cash_session_context.active_session.opened_by_user_name ?? null,
            openingAmount: item.cash_session_context.active_session.opening_amount,
            status: item.cash_session_context.active_session.status,
          }
        : null,
      lastClosedSession: item.cash_session_context.last_closed_session
        ? {
            closedAt: item.cash_session_context.last_closed_session.closed_at ?? null,
            id: item.cash_session_context.last_closed_session.id,
            openedAt: item.cash_session_context.last_closed_session.opened_at,
            openedByUserId: item.cash_session_context.last_closed_session.opened_by_user_id ?? null,
            openedByUserName: item.cash_session_context.last_closed_session.opened_by_user_name ?? null,
            openingAmount: item.cash_session_context.last_closed_session.opening_amount,
            status: item.cash_session_context.last_closed_session.status,
          }
        : null,
    },
    operationalConfig: {
      isActive: item.operational_config.is_active,
      posEnabled: item.operational_config.pos_enabled,
    },
    overview: {
      code: item.overview.code,
      createdAt: item.overview.created_at ?? null,
      id: item.overview.id,
      name: item.overview.name,
      readiness: item.overview.readiness,
      status: item.overview.status,
      updatedAt: item.overview.updated_at ?? null,
    },
    warnings: item.warnings.map(mapWarningFromApi),
  };
}

function mapAdminWorkstationsListFromApi(
  response: AdminWorkstationsApiListResponse,
): AdminWorkstationListResponse {
  return {
    backendContract: adminWorkstationsBackendContract,
    filterOptions: {
      branches: mapFilterOptions(response.filter_options.branches),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminWorkstationListItemFromApi),
    metrics: {
      activeWorkstations: mapMetric(response.metrics.active_workstations),
      inactiveWorkstations: mapMetric(response.metrics.inactive_workstations),
      totalWorkstations: mapMetric(response.metrics.total_workstations),
      withOpenCashSession: mapMetric(response.metrics.with_open_cash_session),
      withWarnings: mapMetric(response.metrics.with_warnings),
      withoutActiveBranch: mapMetric(response.metrics.without_active_branch),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function toCreateApiPayload(payload: AdminWorkstationCreatePayload): AdminWorkstationApiCreatePayload {
  return {
    branch_id: payload.branchId,
    code: payload.code,
    is_active: payload.isActive,
    name: payload.name,
  };
}

function toUpdateApiPayload(payload: AdminWorkstationUpdatePayload): AdminWorkstationApiUpdatePayload {
  return {
    branch_id: payload.branchId,
    code: payload.code,
    is_active: payload.isActive,
    name: payload.name,
  };
}

export function buildAdminWorkstationsListPath(filters: AdminWorkstationListFilters): string {
  const params = new URLSearchParams();

  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "branch_id", filters.branchId);
  appendOptionalParam(params, "cash_session_state", filters.cashSessionState);
  appendOptionalParam(params, "readiness", filters.readiness);
  appendOptionalParam(params, "search", filters.search?.trim());
  appendOptionalParam(params, "status", filters.status);
  appendOptionalParam(params, "warning_state", filters.warningState);

  return `/v1/admin/workstations?${params.toString()}`;
}

export function fetchAdminWorkstations(
  accessToken: string,
  filters: AdminWorkstationListFilters,
): Promise<AdminWorkstationListResponse> {
  return requestJson<AdminWorkstationsApiListResponse>({
    accessToken,
    path: buildAdminWorkstationsListPath(filters),
  }).then(mapAdminWorkstationsListFromApi);
}

export function fetchAdminWorkstationDetail(
  accessToken: string,
  workstationId: string,
): Promise<AdminWorkstationDetail> {
  return requestJson<AdminWorkstationApiDetail>({
    accessToken,
    path: `/v1/admin/workstations/${workstationId}`,
  }).then(mapAdminWorkstationDetailFromApi);
}

export function createAdminWorkstation(
  accessToken: string,
  payload: AdminWorkstationCreatePayload,
): Promise<AdminWorkstationDetail> {
  return requestJson<AdminWorkstationApiDetail>({
    accessToken,
    body: toCreateApiPayload(payload),
    method: "POST",
    path: "/v1/admin/workstations",
  }).then(mapAdminWorkstationDetailFromApi);
}

export function updateAdminWorkstation(
  accessToken: string,
  workstationId: string,
  payload: AdminWorkstationUpdatePayload,
): Promise<AdminWorkstationDetail> {
  return requestJson<AdminWorkstationApiDetail>({
    accessToken,
    body: toUpdateApiPayload(payload),
    method: "PATCH",
    path: `/v1/admin/workstations/${workstationId}`,
  }).then(mapAdminWorkstationDetailFromApi);
}
