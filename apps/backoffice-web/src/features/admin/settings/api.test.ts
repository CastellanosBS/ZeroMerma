import { afterEach, describe, expect, it, vi } from "vitest";

import {
  fetchAdminSettingDetail,
  fetchAdminSettings,
  resetAdminSetting,
  updateAdminSetting,
} from "./api";
import type { AdminSettingsFilters } from "./types";

const filters: AdminSettingsFilters = {
  affectedModule: "all",
  category: "all",
  readonly: "all",
  scope: "all",
  search: "",
  sensitivity: "all",
  status: "all",
};

const apiDefinition = {
  affects_modules: ["tickets"],
  category: "tickets",
  category_label: "Tickets y comprobantes",
  default_value: "Gracias por su compra.",
  description: "Texto operativo mostrado en comprobantes.",
  is_readonly: false,
  is_required: false,
  is_sensitive: false,
  key: "tickets.receipt_footer_text",
  label: "Pie de ticket",
  options: [],
  requires_restart: false,
  scope: "global",
  supported_scopes: ["global"],
  type: "string",
  validation_rules: [{ message: "Longitud maxima permitida.", rule: "max_length", value: 240 }],
};

const apiListItem = {
  available_actions: ["view", "edit"],
  definition: apiDefinition,
  value: {
    current_value: "Gracias por su compra.",
    effective_value: "Gracias por su compra.",
    inherited_from: "default",
    key: "tickets.receipt_footer_text",
    scope: "global",
    scope_id: null,
    status: "ready",
    updated_at: null,
    updated_by: null,
    warning_state: "ready",
  },
  warnings: [],
};

const apiDetail = {
  available_actions: ["view", "edit"],
  definition: apiDefinition,
  history: [],
  validation: { is_valid: true, messages: [] },
  value: apiListItem.value,
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

describe("admin settings API boundary", () => {
  it("fetches and maps settings list from backend", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        backend_contract: {
          detail_endpoint: "GET /v1/admin/settings/{key}",
          export_supported: false,
          history_supported: true,
          list_endpoint: "GET /v1/admin/settings",
          reset_endpoint: "POST /v1/admin/settings/{key}/reset",
          scoped_overrides_supported: false,
          secret_storage_supported: false,
          update_endpoint: "PATCH /v1/admin/settings/{key}",
        },
        categories: [{ description: "Tickets", id: "tickets", label: "Tickets y comprobantes" }],
        filter_options: {
          categories: [{ id: "tickets", label: "Tickets y comprobantes" }],
          modules: [{ id: "tickets", label: "Tickets" }],
          readonly_states: [{ id: "editable", label: "Editables" }],
          scopes: [{ id: "global", label: "Global" }],
          sensitivities: [{ id: "standard", label: "Operativas" }],
          statuses: [{ id: "ready", label: "Listas" }],
        },
        is_backend_connected: true,
        items: [apiListItem],
        metrics: {
          active_settings: 1,
          incomplete_required: 0,
          integration_settings: 0,
          recent_changes: 0,
          scoped_overrides: 0,
          sensitive_settings: 0,
          warning_settings: 0,
        },
        total: 1,
      }),
    );

    const response = await fetchAdminSettings("token-1", {
      ...filters,
      category: "tickets",
      status: "ready",
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/settings?"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(response.items[0]?.definition.key).toBe("tickets.receipt_footer_text");
    expect(response.metrics.activeSettings).toBe("1");
  });

  it("fetches setting detail", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse(apiDetail));

    const detail = await fetchAdminSettingDetail("token-1", "tickets.receipt_footer_text");

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/settings/tickets.receipt_footer_text"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(detail.definition.label).toBe("Pie de ticket");
  });

  it("updates and resets settings through backend", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse(apiDetail));

    await updateAdminSetting("token-1", "tickets.receipt_footer_text", {
      changeNote: "Copy update",
      value: "Vuelve pronto",
    });
    await resetAdminSetting("token-1", "tickets.receipt_footer_text", {
      changeNote: "Default",
    });

    expect(fetchSpy).toHaveBeenNthCalledWith(
      1,
      expect.stringContaining("/v1/admin/settings/tickets.receipt_footer_text"),
      expect.objectContaining({ method: "PATCH" }),
    );
    expect(fetchSpy).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining("/v1/admin/settings/tickets.receipt_footer_text/reset"),
      expect.objectContaining({ method: "POST" }),
    );
  });
});
