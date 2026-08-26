import { afterEach, describe, expect, it, vi } from "vitest";

import { createAdminUser, fetchAdminUserDetail, fetchAdminUsers, lockAdminUser } from "./api";
import type { AdminUserListFilters } from "./types";

const filters: AdminUserListFilters = {
  appAccess: "all",
  branchId: "all",
  lastLoginState: "all",
  page: 1,
  pageSize: 25,
  roleId: "all",
  search: "",
  status: "all",
  warningState: "all",
};

const apiUser = {
  allowed_surfaces: ["POS", "BACKOFFICE"],
  branch_count: 1,
  branch_names: ["Main Branch"],
  created_at: "2026-05-22T10:00:00Z",
  default_surface: "BACKOFFICE",
  email: "admin@zeromerma.local",
  full_name: "ZeroMerma Admin",
  id: "user-1",
  last_login_at: "2026-05-22T11:00:00Z",
  role_count: 0,
  role_names: [],
  status: "active",
  updated_at: "2026-05-22T11:00:00Z",
  warning_state: "ready",
  warnings: [],
};

const apiDetail = {
  account_status: {
    active_sessions_count: null,
    active_sessions_supported: false,
    failed_login_count: null,
    is_active: true,
    is_locked: false,
    last_login_at: "2026-05-22T11:00:00Z",
    lock_reason: null,
    password_reset_required: false,
    pending_invitation: false,
  },
  app_access: {
    allowed_surfaces: ["POS", "BACKOFFICE"],
    backoffice_enabled: true,
    default_surface: "BACKOFFICE",
    has_both_surfaces: true,
    pos_enabled: true,
  },
  audit_timeline: [
    {
      action: "admin.user.created",
      actor_id: "admin-1",
      id: "audit-1",
      metadata: {},
      occurred_at: "2026-05-22T10:00:00Z",
    },
  ],
  available_actions: {
    can_activate: false,
    can_deactivate: true,
    can_edit_app_access: true,
    can_edit_branch_assignments: true,
    can_edit_profile: true,
    can_edit_role_assignments: false,
    can_lock: true,
    can_open_audit: true,
    can_unlock: false,
  },
  branch_assignments: [
    {
      assigned_at: "2026-05-22T10:00:00Z",
      assignment_id: "assignment-1",
      branch_code: "MAIN",
      branch_id: "branch-1",
      branch_name: "Main Branch",
      is_active: true,
      is_default: true,
      updated_at: "2026-05-22T10:00:00Z",
    },
  ],
  operational_context: {
    active_sessions_supported: false,
    last_workstation_used: null,
    open_cash_sessions_count: 0,
    recent_backoffice_activity_count: 1,
    recent_pos_activity_count: 0,
    recently_operated_branches: [],
  },
  overview: apiUser,
  profile: {
    display_name: null,
    email: "admin@zeromerma.local",
    employee_code: null,
    full_name: "ZeroMerma Admin",
    notes: null,
    phone: null,
  },
  role_assignments: {
    is_supported: false,
    items: [],
    missing_contract_note: "Role assignment backend support is not available yet.",
  },
  security_actions: {
    can_activate: false,
    can_deactivate: true,
    can_lock: true,
    can_revoke_sessions: false,
    can_send_invitation: false,
    can_send_password_reset: false,
    can_unlock: false,
    supports_invitation: false,
    supports_locking: true,
    supports_password_reset: false,
    supports_session_revocation: false,
  },
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

describe("admin users API boundary", () => {
  it("fetches and maps user list rows from the backend", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        backend_contract: {
          branch_assignment_endpoint: "POST /v1/admin/users/{id}/branch-assignments",
          create_endpoint: "POST /v1/admin/users",
          detail_endpoint: "GET /v1/admin/users/{id}",
          invitation_supported: false,
          list_endpoint: "GET /v1/admin/users",
          lock_endpoint: "POST /v1/admin/users/{id}/lock",
          password_reset_supported: false,
          role_assignment_supported: false,
          session_revocation_supported: false,
          status_endpoint: "POST /v1/admin/users/{id}/status",
          unlock_endpoint: "POST /v1/admin/users/{id}/unlock",
          update_endpoint: "PATCH /v1/admin/users/{id}",
        },
        filter_options: {
          app_access: [{ id: "POS", label: "POS" }],
          branches: [{ id: "branch-1", label: "Main Branch - MAIN" }],
          last_login_states: [{ id: "with_login", label: "Con acceso" }],
          roles: [],
          statuses: [{ id: "active", label: "Activos" }],
          warning_states: [{ id: "with_warnings", label: "Con advertencias" }],
        },
        is_backend_connected: true,
        items: [apiUser],
        metrics: {
          active_users: 1,
          backoffice_users: 1,
          inactive_users: 0,
          locked_users: 0,
          pending_users: 0,
          pos_users: 1,
          total_users: 1,
          without_branch: 0,
        },
        page: 1,
        page_size: 25,
        total: 1,
      }),
    );

    const response = await fetchAdminUsers("token-1", {
      ...filters,
      appAccess: "BACKOFFICE",
      search: "admin",
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/users?"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(response.items[0]?.email).toBe("admin@zeromerma.local");
    expect(response.metrics.totalUsers).toBe("1");
    expect(response.backendContract.roleAssignmentSupported).toBe(false);
  });

  it("loads detail and maps security/account fields", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse(apiDetail),
    );

    const detail = await fetchAdminUserDetail("token-1", "user-1");

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/users/user-1"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(detail.appAccess.hasBothSurfaces).toBe(true);
    expect(detail.branchAssignments[0]?.branchCode).toBe("MAIN");
    expect(detail.roleAssignments.isSupported).toBe(false);
  });

  it("submits user create and lock requests through backend endpoints", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse(apiDetail, 201),
    );

    await createAdminUser("token-1", {
      allowedSurfaces: ["BACKOFFICE"],
      branchAssignments: [],
      defaultSurface: "BACKOFFICE",
      email: "new-admin@zeromerma.local",
      fullName: "New Admin",
      notes: null,
      phone: null,
      roleIds: [],
      sendInvitation: false,
      temporaryPassword: "TempUser123!",
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/users"),
      expect.objectContaining({
        body: expect.stringContaining('"temporary_password":"TempUser123!"'),
        method: "POST",
      }),
    );

    await lockAdminUser("token-1", "user-1", { reason: "Security review" });
    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining("/v1/admin/users/user-1/lock"),
      expect.objectContaining({
        body: JSON.stringify({ reason: "Security review" }),
        method: "POST",
      }),
    );
  });
});
