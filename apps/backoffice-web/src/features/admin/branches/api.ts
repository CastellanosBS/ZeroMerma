import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminBranchBackendContract,
  AdminBranchCreatePayload,
  AdminBranchDetail,
  AdminBranchFilterOption,
  AdminBranchListFilters,
  AdminBranchListItem,
  AdminBranchListResponse,
  AdminBranchUpdatePayload,
  AdminBranchWarning,
} from "./types";

export const adminBranchesBackendContract: AdminBranchBackendContract = {
  createEndpoint: "POST /v1/admin/branches",
  detailEndpoint: "GET /v1/admin/branches/{id}",
  listEndpoint: "GET /v1/admin/branches",
  updateEndpoint: "PATCH /v1/admin/branches/{id}",
};

type AdminBranchApiFilterOption = components["schemas"]["AdminBranchFilterOptionView"];
type AdminBranchApiListItem = components["schemas"]["AdminBranchListItemView"];
type AdminBranchesApiListResponse = components["schemas"]["AdminBranchesListResponse"];
type AdminBranchApiDetail = components["schemas"]["AdminBranchDetailView"];
type AdminBranchApiCreatePayload = components["schemas"]["AdminBranchCreateRequest"];
type AdminBranchApiUpdatePayload = components["schemas"]["AdminBranchUpdateRequest"];
type AdminBranchApiWarning = components["schemas"]["AdminBranchWarningView"];

function appendOptionalParam(params: URLSearchParams, key: string, value: string | null | undefined) {
  if (!value || value === "all") {
    return;
  }

  params.set(key, value);
}

function mapMetric(value: number): string {
  return String(value);
}

function mapFilterOptions(options: AdminBranchApiFilterOption[]): AdminBranchFilterOption[] {
  return options.map((option) => ({
    id: option.id,
    label: option.label,
  }));
}

function mapWarningFromApi(warning: AdminBranchApiWarning): AdminBranchWarning {
  return {
    code: warning.code,
    message: warning.message,
    severity: warning.severity,
  };
}

export function mapAdminBranchListItemFromApi(item: AdminBranchApiListItem): AdminBranchListItem {
  return {
    activeWorkstationCount: item.active_workstation_count,
    assignedUserCount: item.assigned_user_count,
    brandId: item.brand_id,
    brandName: item.brand_name,
    code: item.code,
    id: item.id,
    name: item.name,
    readiness: item.readiness,
    status: item.status,
    timezone: item.timezone,
    updatedAt: item.updated_at ?? null,
    warnings: item.warnings.map(mapWarningFromApi),
    workstationCount: item.workstation_count,
  };
}

export function mapAdminBranchDetailFromApi(item: AdminBranchApiDetail): AdminBranchDetail {
  return {
    availableActions: {
      canActivate: item.available_actions.can_activate,
      canDeactivate: item.available_actions.can_deactivate,
      canEdit: item.available_actions.can_edit,
      canOpenUsers: item.available_actions.can_open_users,
      canOpenWorkstations: item.available_actions.can_open_workstations,
    },
    locationContact: {
      addressLine: item.location_contact.address_line ?? null,
      city: item.location_contact.city ?? null,
      contactEmail: item.location_contact.contact_email ?? null,
      country: item.location_contact.country ?? null,
      notes: item.location_contact.notes ?? null,
      phone: item.location_contact.phone ?? null,
      postalCode: item.location_contact.postal_code ?? null,
      state: item.location_contact.state ?? null,
    },
    operationalConfig: {
      inventoryScopeReady: item.operational_config.inventory_scope_ready,
      isActive: item.operational_config.is_active,
      posReady: item.operational_config.pos_ready,
      productionScopeReady: item.operational_config.production_scope_ready,
      timezone: item.operational_config.timezone,
    },
    overview: {
      brandId: item.overview.brand_id,
      brandName: item.overview.brand_name,
      code: item.overview.code,
      createdAt: item.overview.created_at ?? null,
      id: item.overview.id,
      name: item.overview.name,
      readiness: item.overview.readiness,
      status: item.overview.status,
      timezone: item.overview.timezone,
      updatedAt: item.overview.updated_at ?? null,
    },
    relatedOperationsSummary: {
      openCashSessions: item.related_operations_summary.open_cash_sessions,
    },
    userAssignmentsSummary: {
      active: item.user_assignments_summary.active,
      inactive: item.user_assignments_summary.inactive,
      items: item.user_assignments_summary.items.map((assignment) => ({
        assignmentId: assignment.assignment_id,
        isActive: assignment.is_active,
        updatedAt: assignment.updated_at ?? null,
        userEmail: assignment.user_email,
        userId: assignment.user_id,
        userName: assignment.user_name,
      })),
      total: item.user_assignments_summary.total,
    },
    warnings: item.warnings.map(mapWarningFromApi),
    workstationsSummary: {
      active: item.workstations_summary.active,
      inactive: item.workstations_summary.inactive,
      items: item.workstations_summary.items.map((workstation) => ({
        code: workstation.code,
        id: workstation.id,
        isActive: workstation.is_active,
        name: workstation.name,
        updatedAt: workstation.updated_at ?? null,
      })),
      total: item.workstations_summary.total,
    },
  };
}

function mapAdminBranchesListFromApi(response: AdminBranchesApiListResponse): AdminBranchListResponse {
  return {
    backendContract: adminBranchesBackendContract,
    filterOptions: {
      brands: mapFilterOptions(response.filter_options.brands),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminBranchListItemFromApi),
    metrics: {
      activeBranches: mapMetric(response.metrics.active_branches),
      inactiveBranches: mapMetric(response.metrics.inactive_branches),
      totalBranches: mapMetric(response.metrics.total_branches),
      withWarnings: mapMetric(response.metrics.with_warnings),
      withWorkstations: mapMetric(response.metrics.with_workstations),
      withoutActiveWorkstation: mapMetric(response.metrics.without_active_workstation),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function toCreateApiPayload(payload: AdminBranchCreatePayload): AdminBranchApiCreatePayload {
  return {
    address_line: payload.addressLine ?? null,
    brand_id: payload.brandId,
    city: payload.city ?? null,
    code: payload.code,
    contact_email: payload.contactEmail ?? null,
    country: payload.country ?? null,
    is_active: payload.isActive,
    name: payload.name,
    notes: payload.notes ?? null,
    phone: payload.phone ?? null,
    postal_code: payload.postalCode ?? null,
    state: payload.state ?? null,
    timezone: payload.timezone,
  };
}

function toUpdateApiPayload(payload: AdminBranchUpdatePayload): AdminBranchApiUpdatePayload {
  return {
    address_line: payload.addressLine,
    brand_id: payload.brandId,
    city: payload.city,
    code: payload.code,
    contact_email: payload.contactEmail,
    country: payload.country,
    is_active: payload.isActive,
    name: payload.name,
    notes: payload.notes,
    phone: payload.phone,
    postal_code: payload.postalCode,
    state: payload.state,
    timezone: payload.timezone,
  };
}

export function buildAdminBranchesListPath(filters: AdminBranchListFilters): string {
  const params = new URLSearchParams();

  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "brand_id", filters.brandId);
  appendOptionalParam(params, "has_active_workstations", filters.hasActiveWorkstations);
  appendOptionalParam(params, "search", filters.search?.trim());
  appendOptionalParam(params, "status", filters.status);
  appendOptionalParam(params, "warning_state", filters.warningState);

  return `/v1/admin/branches?${params.toString()}`;
}

export function fetchAdminBranches(
  accessToken: string,
  filters: AdminBranchListFilters,
): Promise<AdminBranchListResponse> {
  return requestJson<AdminBranchesApiListResponse>({
    accessToken,
    path: buildAdminBranchesListPath(filters),
  }).then(mapAdminBranchesListFromApi);
}

export function fetchAdminBranchDetail(accessToken: string, branchId: string): Promise<AdminBranchDetail> {
  return requestJson<AdminBranchApiDetail>({
    accessToken,
    path: `/v1/admin/branches/${branchId}`,
  }).then(mapAdminBranchDetailFromApi);
}

export function createAdminBranch(
  accessToken: string,
  payload: AdminBranchCreatePayload,
): Promise<AdminBranchDetail> {
  return requestJson<AdminBranchApiDetail>({
    accessToken,
    body: toCreateApiPayload(payload),
    method: "POST",
    path: "/v1/admin/branches",
  }).then(mapAdminBranchDetailFromApi);
}

export function updateAdminBranch(
  accessToken: string,
  branchId: string,
  payload: AdminBranchUpdatePayload,
): Promise<AdminBranchDetail> {
  return requestJson<AdminBranchApiDetail>({
    accessToken,
    body: toUpdateApiPayload(payload),
    method: "PATCH",
    path: `/v1/admin/branches/${branchId}`,
  }).then(mapAdminBranchDetailFromApi);
}
