import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createAdminRole,
  fetchAdminRoleDetail,
  fetchAdminRolePermissions,
  fetchAdminRoles,
} from "./api";
import type { AdminRoleListFilters } from "./types";

const filters: AdminRoleListFilters = {
  appSurface: "all",
  hasUsers: "all",
  highPrivilege: "all",
  page: 1,
  pageSize: 25,
  permissionModule: "all",
  search: "",
  status: "all",
  systemState: "all",
  warningState: "all",
};

const apiPermission = {
  action: "manage",
  code: "roles.manage",
  description: "Permite modificar roles.",
  id: "permission-1",
  is_enabled: true,
  is_sensitive: true,
  label: "Gestionar roles",
  module: "control",
  module_label: "Control",
  surfaces: ["BACKOFFICE"],
};

const apiRole = {
  assigned_user_count: 1,
  code: "admin",
  description: "Acceso administrativo completo.",
  id: "role-1",
  is_high_privilege: true,
  is_system: true,
  name: "Administrador",
  permission_count: 1,
  scope_summary: "Sin restricciones de alcance configuradas.",
  status: "active",
  surfaces: ["BACKOFFICE"],
  updated_at: "2026-05-22T10:00:00Z",
  warning_state: "warning",
  warnings: [],
};

const apiDetail = {
  access_surfaces: {
    backoffice_enabled: true,
    grants_both_surfaces: false,
    note: "Surface note",
    pos_enabled: false,
    surfaces: ["BACKOFFICE"],
  },
  assigned_users: [
    {
      assigned_at: "2026-05-22T10:00:00Z",
      branch_summary: "Main Branch",
      email: "admin@zeromerma.local",
      full_name: "ZeroMerma Admin",
      status: "active",
      surfaces: ["BACKOFFICE"],
      user_id: "user-1",
    },
  ],
  audit_history: [
    {
      action: "admin.role.created",
      actor_id: "user-1",
      id: "audit-1",
      metadata: {},
      occurred_at: "2026-05-22T10:00:00Z",
    },
  ],
  available_actions: {
    can_activate: false,
    can_assign_users: false,
    can_deactivate: false,
    can_delete: false,
    can_duplicate: false,
    can_edit: false,
    can_open_audit: true,
    can_remove_users: false,
  },
  overview: {
    code: "admin",
    created_at: "2026-05-22T10:00:00Z",
    description: "Acceso administrativo completo.",
    id: "role-1",
    is_high_privilege: true,
    is_system: true,
    name: "Administrador",
    status: "active",
    surfaces: ["BACKOFFICE"],
    updated_at: "2026-05-22T10:00:00Z",
    warning_state: "warning",
  },
  permission_matrix: [{ label: "Control", module: "control", permissions: [apiPermission] }],
  scopes: {
    is_supported: false,
    missing_contract_note: "Branch-scoped roles are not available yet.",
    scope_summary: "Sin restricciones de alcance configuradas.",
  },
  sensitive_permissions: [apiPermission],
  warnings: [],
};

function mockJsonResponse(payload: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      headers: { "Content-Type": "application/json" },
      status,
    }),
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("admin roles API boundary", () => {
  it("fetches and maps role list rows from the backend", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        backend_contract: {
          assign_user_endpoint: "POST /v1/admin/roles/{id}/users/{user_id}",
          create_endpoint: "POST /v1/admin/roles",
          destructive_delete_supported: false,
          detail_endpoint: "GET /v1/admin/roles/{id}",
          duplicate_supported: false,
          list_endpoint: "GET /v1/admin/roles",
          permissions_endpoint: "GET /v1/admin/roles/permissions",
          remove_user_endpoint: "POST /v1/admin/roles/{id}/users/{user_id}/remove",
          scoped_roles_supported: false,
          status_endpoint: "POST /v1/admin/roles/{id}/status",
          update_endpoint: "PATCH /v1/admin/roles/{id}",
        },
        filter_options: {
          app_surfaces: [{ id: "BACKOFFICE", label: "Backoffice" }],
          has_users: [{ id: "yes", label: "Con usuarios" }],
          high_privilege: [{ id: "yes", label: "Alto privilegio" }],
          permission_modules: [{ id: "control", label: "Control" }],
          statuses: [{ id: "active", label: "Activos" }],
          system_states: [{ id: "system", label: "Sistema" }],
          warning_states: [{ id: "with_warnings", label: "Con advertencias" }],
        },
        is_backend_connected: true,
        items: [apiRole],
        metrics: {
          active_roles: 1,
          backoffice_roles: 1,
          high_privilege: 1,
          inactive_roles: 0,
          pos_roles: 0,
          total_roles: 1,
          with_users: 1,
          with_warnings: 1,
          without_users: 0,
        },
        page: 1,
        page_size: 25,
        total: 1,
      }),
    );

    const response = await fetchAdminRoles("token-1", {
      ...filters,
      appSurface: "BACKOFFICE",
      search: "admin",
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/roles?"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(response.items[0]?.code).toBe("admin");
    expect(response.metrics.highPrivilege).toBe("1");
    expect(response.backendContract.scopedRolesSupported).toBe(false);
  });

  it("loads detail and permissions", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      if (String(input).includes("/permissions")) {
        return mockJsonResponse({
          groups: [{ label: "Control", module: "control", permissions: [apiPermission] }],
          sensitive_permission_codes: ["roles.manage"],
        });
      }
      return mockJsonResponse(apiDetail);
    });

    const detail = await fetchAdminRoleDetail("token-1", "role-1");
    const permissions = await fetchAdminRolePermissions("token-1");

    expect(fetchSpy).toHaveBeenCalledTimes(2);
    expect(detail.overview.isHighPrivilege).toBe(true);
    expect(detail.assignedUsers[0]?.email).toBe("admin@zeromerma.local");
    expect(permissions.sensitivePermissionCodes).toContain("roles.manage");
  });

  it("submits role create through the backend endpoint", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse(apiDetail, 201),
    );

    await createAdminRole("token-1", {
      code: "cash_auditor",
      confirmedHighRiskChange: true,
      description: "Consulta caja.",
      isActive: true,
      name: "Auditor de caja",
      permissionCodes: ["cash_finance.view"],
      surfaces: ["BACKOFFICE"],
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/roles"),
      expect.objectContaining({
        body: expect.stringContaining('"confirmed_high_risk_change":true'),
        method: "POST",
      }),
    );
  });
});

