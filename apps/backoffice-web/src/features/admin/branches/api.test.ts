import { afterEach, describe, expect, it, vi } from "vitest";

import { buildAdminBranchesListPath, createAdminBranch, fetchAdminBranchDetail, fetchAdminBranches } from "./api";
import type { AdminBranchListFilters } from "./types";

const filters: AdminBranchListFilters = {
  hasActiveWorkstations: "all",
  page: 1,
  pageSize: 25,
  search: "",
  status: "all",
  warningState: "all",
};

const apiBranch = {
  active_workstation_count: 1,
  assigned_user_count: 2,
  brand_id: "brand-1",
  brand_name: "El Mejor Pan",
  code: "MAIN",
  id: "branch-1",
  name: "Main Branch",
  readiness: "ready",
  status: "active",
  timezone: "America/Hermosillo",
  updated_at: "2026-05-20T10:00:00Z",
  warnings: [],
  workstation_count: 1,
};

const apiDetail = {
  available_actions: {
    can_activate: false,
    can_deactivate: true,
    can_edit: true,
    can_open_users: true,
    can_open_workstations: true,
  },
  location_contact: {
    address_line: null,
    city: "Hermosillo",
    contact_email: null,
    country: "Mexico",
    notes: null,
    phone: null,
    postal_code: null,
    state: "Sonora",
  },
  operational_config: {
    inventory_scope_ready: true,
    is_active: true,
    pos_ready: true,
    production_scope_ready: true,
    timezone: "America/Hermosillo",
  },
  overview: {
    brand_id: "brand-1",
    brand_name: "El Mejor Pan",
    code: "MAIN",
    created_at: "2026-05-20T09:00:00Z",
    id: "branch-1",
    name: "Main Branch",
    readiness: "ready",
    status: "active",
    timezone: "America/Hermosillo",
    updated_at: "2026-05-20T10:00:00Z",
  },
  related_operations_summary: {
    open_cash_sessions: 0,
  },
  user_assignments_summary: {
    active: 1,
    inactive: 0,
    items: [
      {
        assignment_id: "assignment-1",
        is_active: true,
        updated_at: "2026-05-20T10:00:00Z",
        user_email: "admin@example.com",
        user_id: "user-1",
        user_name: "Admin",
      },
    ],
    total: 1,
  },
  warnings: [],
  workstations_summary: {
    active: 1,
    inactive: 0,
    items: [
      {
        code: "POS-01",
        id: "workstation-1",
        is_active: true,
        name: "Front Register",
        updated_at: "2026-05-20T10:00:00Z",
      },
    ],
    total: 1,
  },
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

describe("admin branches API boundary", () => {
  it("builds real branch list query parameters", () => {
    const path = buildAdminBranchesListPath({
      ...filters,
      brandId: "brand-1",
      hasActiveWorkstations: "no",
      search: "main",
      status: "active",
      warningState: "with_warnings",
    });

    expect(path).toContain("/v1/admin/branches?");
    expect(path).toContain("brand_id=brand-1");
    expect(path).toContain("has_active_workstations=no");
    expect(path).toContain("search=main");
    expect(path).toContain("status=active");
    expect(path).toContain("warning_state=with_warnings");
  });

  it("fetches and maps branch list rows from the backend", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        backend_contract: {
          create_endpoint: "POST /v1/admin/branches",
          detail_endpoint: "GET /v1/admin/branches/{id}",
          list_endpoint: "GET /v1/admin/branches",
          update_endpoint: "PATCH /v1/admin/branches/{id}",
        },
        filter_options: {
          brands: [{ id: "brand-1", label: "El Mejor Pan" }],
        },
        is_backend_connected: true,
        items: [apiBranch],
        metrics: {
          active_branches: 1,
          inactive_branches: 0,
          total_branches: 1,
          with_warnings: 0,
          with_workstations: 1,
          without_active_workstation: 0,
        },
        page: 1,
        page_size: 25,
        total: 1,
      }),
    );

    const response = await fetchAdminBranches("token-1", filters);

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/branches?page=1&page_size=25"),
      expect.objectContaining({
        headers: expect.any(Headers),
        method: "GET",
      }),
    );
    expect(response.items).toHaveLength(1);
    expect(response.items[0]?.name).toBe("Main Branch");
    expect(response.metrics.activeBranches).toBe("1");
    expect(response.filterOptions.brands[0]?.label).toBe("El Mejor Pan");
  });

  it("loads branch detail by id", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse(apiDetail));

    const branch = await fetchAdminBranchDetail("token-1", "branch-1");

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/branches/branch-1"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(branch.overview.id).toBe("branch-1");
    expect(branch.workstationsSummary.active).toBe(1);
    expect(branch.userAssignmentsSummary.items[0]?.userName).toBe("Admin");
  });

  it("submits new branches through the backend contract", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse(apiDetail, 201));

    const branch = await createAdminBranch("token-1", {
      brandId: "brand-1",
      code: "CENTRO",
      isActive: true,
      name: "Sucursal Centro",
      timezone: "America/Hermosillo",
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/branches"),
      expect.objectContaining({
        body: JSON.stringify({
          address_line: null,
          brand_id: "brand-1",
          city: null,
          code: "CENTRO",
          contact_email: null,
          country: null,
          is_active: true,
          name: "Sucursal Centro",
          notes: null,
          phone: null,
          postal_code: null,
          state: null,
          timezone: "America/Hermosillo",
        }),
        method: "POST",
      }),
    );
    expect(branch.overview.name).toBe("Main Branch");
  });
});
