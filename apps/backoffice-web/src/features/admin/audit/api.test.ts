import { afterEach, describe, expect, it, vi } from "vitest";

import {
  exportAdminAuditEvents,
  fetchAdminAuditEventDetail,
  fetchAdminAuditEvents,
} from "./api";
import type { AdminAuditListFilters } from "./types";

const filters: AdminAuditListFilters = {
  action: "all",
  actorEmail: "",
  actorUserId: "all",
  branchId: "all",
  dateFrom: "",
  dateTo: "",
  entityId: "",
  entityType: "all",
  module: "all",
  page: 1,
  pageSize: 25,
  relatedReference: "",
  result: "all",
  search: "",
  sensitive: "all",
  severity: "all",
  sourceApp: "all",
  warningState: "all",
  workstation: "",
};

const apiEvent = {
  action: "admin.user.updated",
  action_label: "Admin User Updated",
  actor_email: "admin@zeromerma.local",
  actor_name: "ZeroMerma Admin",
  actor_type: "user",
  actor_user_id: "user-1",
  branch_id: "branch-1",
  branch_name: "Main Branch",
  entity_id: "user-2",
  entity_reference: "cashier@zeromerma.local",
  entity_type: "user",
  id: "audit-1",
  is_sensitive: true,
  module: "users",
  module_label: "Usuarios",
  occurred_at: "2026-05-22T10:00:00Z",
  result: "success",
  severity: "warning",
  source_app: "BACKOFFICE",
  warning_state: "sensitive",
  workstation_id: null,
  workstation_name: "CAJA-01",
};

const apiDetail = {
  actor_context: {
    branch_assignments_summary: "Main Branch",
    can_open_user: true,
    email: "admin@zeromerma.local",
    full_name: "ZeroMerma Admin",
    roles_summary: "Administrador",
    user_id: "user-1",
    user_status: "active",
  },
  available_actions: {
    can_copy_correlation_id: true,
    can_copy_event_id: true,
    can_export_event: true,
    can_open_related_document: false,
    can_open_user: true,
    can_search_related_events: true,
  },
  change_summary: [
    {
      change_type: "updated",
      field: "password_hash",
      new_value_masked: "[masked]",
      old_value_masked: "[masked]",
    },
  ],
  entity_context: {
    branch_id: "branch-1",
    branch_name: "Main Branch",
    can_open_related_document: false,
    cash_session_id: null,
    entity_id: "user-2",
    entity_reference: "cashier@zeromerma.local",
    entity_type: "user",
    related_module: "users",
    workstation_id: null,
    workstation_name: "CAJA-01",
  },
  overview: { ...apiEvent, request_id: "request-1" },
  related_documents: [
    {
      can_open: false,
      document_id: "user-2",
      document_type: "user",
      label: "Documento origen: User",
      module: "users",
      reference: "cashier@zeromerma.local",
    },
  ],
  request_context: {
    correlation_id: "correlation-1",
    duration_ms: 10,
    endpoint: "/v1/admin/users",
    error_code: null,
    ip_address: null,
    method: "PATCH",
    request_id: "request-1",
    status_code: 200,
    user_agent: null,
  },
  timeline_related_events: [
    {
      action: "admin.user.created",
      action_label: "Admin User Created",
      actor_name: "ZeroMerma Admin",
      id: "audit-2",
      is_sensitive: true,
      occurred_at: "2026-05-22T09:00:00Z",
      result: "success",
    },
  ],
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

describe("admin audit API boundary", () => {
  it("fetches and maps audit list rows from the backend", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        backend_contract: {
          export_supported: true,
          immutable_events: true,
          mutation_supported: false,
          related_timeline_supported: true,
          request_context_supported: true,
        },
        filter_options: {
          actions: [{ code: "admin.user.updated", label: "Admin User Updated" }],
          branches: [{ code: "branch-1", label: "Main Branch" }],
          entity_types: [{ code: "user", label: "User" }],
          modules: [{ code: "users", label: "Usuarios" }],
          results: [{ code: "success", label: "Success" }],
          sensitivities: [{ code: "yes", label: "Sensibles" }],
          severities: [{ code: "warning", label: "Warning" }],
          source_apps: [{ code: "BACKOFFICE", label: "Backoffice" }],
          users: [{ code: "user-1", label: "admin@zeromerma.local" }],
          warning_states: [{ code: "sensitive", label: "Sensitive" }],
        },
        is_backend_connected: true,
        items: [apiEvent],
        metrics: {
          access_events: 1,
          active_actors: 1,
          failed_events: 0,
          financial_events: 0,
          inventory_events: 0,
          sensitive_events: 1,
          system_events: 0,
          total_events: 1,
        },
        page: 1,
        page_size: 25,
        total: 1,
      }),
    );

    const response = await fetchAdminAuditEvents("token-1", {
      ...filters,
      module: "users",
      sensitive: "yes",
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/audit?"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(response.items[0]?.isSensitive).toBe(true);
    expect(response.metrics.sensitiveEvents).toBe("1");
    expect(response.backendContract.immutableEvents).toBe(true);
  });

  it("loads detail with masked change summary", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse(apiDetail));

    const detail = await fetchAdminAuditEventDetail("token-1", "audit-1");

    expect(detail.overview.requestId).toBe("request-1");
    expect(detail.changeSummary[0]?.newValueMasked).toBe("[masked]");
    expect(detail.requestContext?.endpoint).toBe("/v1/admin/users");
    expect(detail.relatedDocuments[0]?.documentType).toBe("user");
  });

  it("exports filtered safe audit rows", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        format: "json",
        generated_at: "2026-05-22T10:00:00Z",
        rows: [
          {
            action: "admin.user.updated",
            actor: "ZeroMerma Admin",
            actor_email: "admin@zeromerma.local",
            branch_name: "Main Branch",
            entity_id: "user-2",
            entity_reference: "cashier@zeromerma.local",
            entity_type: "user",
            is_sensitive: true,
            module: "users",
            occurred_at: "2026-05-22T10:00:00Z",
            result: "success",
            source_app: "BACKOFFICE",
            workstation_name: "CAJA-01",
          },
        ],
        total: 1,
      }),
    );

    const response = await exportAdminAuditEvents("token-1", { ...filters, module: "users" });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/audit/export?"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(response.rows[0]?.isSensitive).toBe(true);
  });
});
