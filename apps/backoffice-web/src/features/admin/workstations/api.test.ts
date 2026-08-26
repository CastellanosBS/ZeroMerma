import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildAdminWorkstationsListPath,
  createAdminWorkstation,
  fetchAdminWorkstationDetail,
  fetchAdminWorkstations,
} from "./api";
import type { AdminWorkstationListFilters } from "./types";

const filters: AdminWorkstationListFilters = {
  cashSessionState: "all",
  page: 1,
  pageSize: 25,
  readiness: "all",
  search: "",
  status: "all",
  warningState: "all",
};

const apiWorkstation = {
  active_cash_session_id: null,
  branch_code: "MAIN",
  branch_id: "branch-1",
  branch_is_active: true,
  branch_name: "Main Branch",
  code: "POS-01",
  has_active_cash_session: false,
  id: "workstation-1",
  last_closed_at: null,
  last_opened_at: null,
  name: "Front Register",
  readiness: "ready",
  status: "active",
  updated_at: "2026-05-20T10:00:00Z",
  warnings: [],
};

const apiDetail = {
  access_context: {
    active_assigned_user_count: 1,
    assigned_user_count: 1,
    users: [
      {
        is_active: true,
        user_email: "admin@example.com",
        user_id: "user-1",
        user_name: "Admin",
      },
    ],
  },
  available_actions: {
    can_activate: false,
    can_deactivate: true,
    can_edit: true,
    can_open_branch: true,
    can_open_cash_session: false,
  },
  branch_relationship: {
    branch_code: "MAIN",
    branch_id: "branch-1",
    branch_is_active: true,
    branch_name: "Main Branch",
    branch_timezone: "America/Hermosillo",
  },
  cash_session_context: {
    active_session: null,
    last_closed_session: null,
  },
  operational_config: {
    is_active: true,
    pos_enabled: true,
  },
  overview: {
    code: "POS-01",
    created_at: "2026-05-20T09:00:00Z",
    id: "workstation-1",
    name: "Front Register",
    readiness: "ready",
    status: "active",
    updated_at: "2026-05-20T10:00:00Z",
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

describe("admin workstations API boundary", () => {
  it("builds workstation list query parameters", () => {
    const path = buildAdminWorkstationsListPath({
      ...filters,
      branchId: "branch-1",
      cashSessionState: "open",
      readiness: "warning",
      search: "pos",
      status: "active",
      warningState: "with_warnings",
    });

    expect(path).toContain("/v1/admin/workstations?");
    expect(path).toContain("branch_id=branch-1");
    expect(path).toContain("cash_session_state=open");
    expect(path).toContain("readiness=warning");
    expect(path).toContain("search=pos");
    expect(path).toContain("status=active");
    expect(path).toContain("warning_state=with_warnings");
  });

  it("fetches and maps workstation list rows from the backend", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        backend_contract: {
          create_endpoint: "POST /v1/admin/workstations",
          detail_endpoint: "GET /v1/admin/workstations/{id}",
          list_endpoint: "GET /v1/admin/workstations",
          update_endpoint: "PATCH /v1/admin/workstations/{id}",
        },
        filter_options: {
          branches: [{ id: "branch-1", label: "Main Branch - MAIN" }],
        },
        is_backend_connected: true,
        items: [apiWorkstation],
        metrics: {
          active_workstations: 1,
          inactive_workstations: 0,
          total_workstations: 1,
          with_open_cash_session: 0,
          with_warnings: 0,
          without_active_branch: 0,
        },
        page: 1,
        page_size: 25,
        total: 1,
      }),
    );

    const response = await fetchAdminWorkstations("token-1", filters);

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/workstations?page=1&page_size=25"),
      expect.objectContaining({
        headers: expect.any(Headers),
        method: "GET",
      }),
    );
    expect(response.items).toHaveLength(1);
    expect(response.items[0]?.code).toBe("POS-01");
    expect(response.metrics.activeWorkstations).toBe("1");
    expect(response.filterOptions.branches[0]?.label).toBe("Main Branch - MAIN");
  });

  it("loads workstation detail by id", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse(apiDetail));

    const workstation = await fetchAdminWorkstationDetail("token-1", "workstation-1");

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/workstations/workstation-1"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(workstation.overview.id).toBe("workstation-1");
    expect(workstation.branchRelationship.branchCode).toBe("MAIN");
    expect(workstation.accessContext.users[0]?.userName).toBe("Admin");
  });

  it("submits new workstations through the backend contract", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse(apiDetail, 201));

    const workstation = await createAdminWorkstation("token-1", {
      branchId: "branch-1",
      code: "POS-02",
      isActive: true,
      name: "Front Register 02",
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/workstations"),
      expect.objectContaining({
        body: JSON.stringify({
          branch_id: "branch-1",
          code: "POS-02",
          is_active: true,
          name: "Front Register 02",
        }),
        method: "POST",
      }),
    );
    expect(workstation.overview.name).toBe("Front Register");
  });
});
