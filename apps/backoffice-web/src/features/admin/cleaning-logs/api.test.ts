import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildAdminCleaningLogsListPath,
  completeAdminCleaningLog,
  createAdminCleaningLog,
  fetchAdminCleaningLogDetail,
  fetchAdminCleaningLogs,
  fetchAdminCleaningTemplates,
} from "./api";
import type { AdminCleaningListFilters } from "./types";

const filters: AdminCleaningListFilters = {
  areaName: "all",
  areaType: "all",
  branchId: "all",
  cleaningType: "all",
  dateFrom: null,
  dateTo: null,
  evidenceState: "all",
  observationState: "all",
  page: 1,
  pageSize: 25,
  responsibleUserId: "all",
  riskLevel: "all",
  search: "",
  shiftCode: "all",
  status: "all",
  templateId: "all",
  warningState: "all",
};

const apiWarning = {
  code: "high_risk",
  message: "Bitacora de alto riesgo.",
  severity: "warning",
} as const;

const apiItem = {
  area_id: null,
  area_name: "Cocina",
  branch_id: "11111111-1111-4111-8111-111111111111",
  branch_name: "Sucursal Centro",
  checklist_completed_count: 2,
  checklist_total_count: 3,
  cleaning_type: "SANITATION",
  completed_at: null,
  equipment_id: null,
  equipment_name: "Mesa fria",
  folio: "CLN-000001",
  has_evidence: true,
  has_observations: true,
  id: "22222222-2222-4222-8222-222222222222",
  responsible_user_id: "33333333-3333-4333-8333-333333333333",
  responsible_user_name: "Ana Lopez",
  risk_level: "HIGH",
  scheduled_at: "2026-05-21T15:00:00Z",
  shift_code: "MORNING",
  status: "PENDING",
  task_name: "Sanitizacion de cocina",
  updated_at: "2026-05-21T15:10:00Z",
  warning_state: "high_risk",
  warnings: [apiWarning],
} as const;

const apiDetail = {
  available_actions: {
    can_add_evidence: true,
    can_cancel: true,
    can_complete: true,
    can_create_incident: true,
    can_edit: true,
    can_export: false,
    can_print: false,
    note: "Incidencias requieren backend dedicado.",
  },
  checklist: [
    {
      display_order: 1,
      id: "44444444-4444-4444-8444-444444444444",
      is_completed: true,
      is_required: true,
      label: "Retirar residuos",
      notes: null,
    },
    {
      display_order: 2,
      id: "55555555-5555-4555-8555-555555555555",
      is_completed: false,
      is_required: true,
      label: "Sanitizar mesa",
      notes: null,
    },
  ],
  evidence: {
    empty_state: "Esta bitacora no tiene evidencia adjunta.",
    evidence_note: "Foto en archivo interno 123",
    files: [],
    has_evidence: true,
    is_supported: true,
    upload_supported: false,
  },
  location_area: {
    area_name: "Cocina",
    area_type: "PRODUCTION_AREA",
    branch_code: "CENTRO",
    branch_id: "11111111-1111-4111-8111-111111111111",
    branch_name: "Sucursal Centro",
    equipment_name: "Mesa fria",
  },
  observations_issues: {
    cancellation_reason: null,
    corrective_note: null,
    incomplete_required_count: 1,
    issue_notes: "Quedo pendiente sanitizar mesa.",
    notes: "Turno matutino",
  },
  overview: {
    area_name: "Cocina",
    branch_id: "11111111-1111-4111-8111-111111111111",
    branch_name: "Sucursal Centro",
    cleaning_type: "SANITATION",
    completed_at: null,
    created_at: "2026-05-21T15:05:00Z",
    created_by_user_id: "66666666-6666-4666-8666-666666666666",
    created_by_user_name: "Admin",
    equipment_name: "Mesa fria",
    folio: "CLN-000001",
    id: "22222222-2222-4222-8222-222222222222",
    responsible_user_id: "33333333-3333-4333-8333-333333333333",
    responsible_user_name: "Ana Lopez",
    risk_level: "HIGH",
    scheduled_at: "2026-05-21T15:00:00Z",
    shift_code: "MORNING",
    started_at: null,
    status: "PENDING",
    task_name: "Sanitizacion de cocina",
    warning_state: "high_risk",
  },
  related_documents: [],
  task_template: {
    cleaning_type: "SANITATION",
    estimated_duration_minutes: 20,
    frequency: "DAILY",
    method_summary: "Limpiar y sanitizar superficies.",
    required_tools: "Sanitizante, panos",
    risk_level: "HIGH",
    task_name: "Sanitizacion de cocina",
    task_template_id: "77777777-7777-4777-8777-777777777777",
    task_template_name: "Cocina diaria",
  },
  warnings: [apiWarning],
} as const;

const apiTemplate = {
  area_type: "PRODUCTION_AREA",
  cleaning_type: "SANITATION",
  description: "Cierre de cocina",
  estimated_duration_minutes: 20,
  frequency: "DAILY",
  id: "77777777-7777-4777-8777-777777777777",
  is_active: true,
  items: [
    {
      description: null,
      display_order: 1,
      id: "88888888-8888-4888-8888-888888888888",
      is_required: true,
      label: "Retirar residuos",
    },
  ],
  method_summary: "Limpiar y sanitizar superficies.",
  name: "Cocina diaria",
  required_tools: "Sanitizante",
  requires_evidence: true,
  risk_level: "HIGH",
} as const;

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

describe("admin cleaning logs API boundary", () => {
  it("builds cleaning-log query parameters", () => {
    const path = buildAdminCleaningLogsListPath({
      ...filters,
      areaType: "PRODUCTION_AREA",
      branchId: "branch-1",
      dateFrom: "2026-05-21",
      evidenceState: "without_evidence",
      riskLevel: "HIGH",
      search: "cocina",
      status: "PENDING",
      warningState: "overdue",
    });

    expect(path).toContain("/v1/admin/cleaning-logs?");
    expect(path).toContain("branch_id=branch-1");
    expect(path).toContain("area_type=PRODUCTION_AREA");
    expect(path).toContain("date_from=2026-05-21T00%3A00%3A00.000Z");
    expect(path).toContain("evidence_state=without_evidence");
    expect(path).toContain("risk_level=HIGH");
    expect(path).toContain("search=cocina");
    expect(path).toContain("status=PENDING");
    expect(path).toContain("warning_state=overdue");
  });

  it("fetches list, detail and templates from backend", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes("/templates")) {
        return mockJsonResponse([apiTemplate]);
      }
      if (url.includes(apiItem.id)) {
        return mockJsonResponse(apiDetail);
      }
      return mockJsonResponse({
        backend_contract: undefined,
        filter_options: {
          area_types: [{ id: "PRODUCTION_AREA", label: "Produccion" }],
          areas: [{ id: "Cocina", label: "Cocina" }],
          branches: [{ id: "branch-1", label: "Sucursal Centro" }],
          cleaning_types: [{ id: "SANITATION", label: "Sanitizacion" }],
          evidence_states: [{ id: "without_evidence", label: "Sin evidencia" }],
          observation_states: [{ id: "with_observations", label: "Con observaciones" }],
          responsible_users: [{ id: "user-1", label: "Ana Lopez" }],
          risk_levels: [{ id: "HIGH", label: "Alto" }],
          shifts: [{ id: "MORNING", label: "Matutino" }],
          statuses: [{ id: "PENDING", label: "Pendiente" }],
          templates: [{ id: apiTemplate.id, label: "Cocina diaria" }],
        },
        is_backend_connected: true,
        items: [apiItem],
        metrics: {
          completed_count: 0,
          high_risk_count: 1,
          overdue_count: 0,
          pending_count: 1,
          requires_review_count: 0,
          total_count: 1,
          with_evidence_count: 1,
          with_observations_count: 1,
        },
        page: 1,
        page_size: 25,
        total: 1,
      });
    });

    const list = await fetchAdminCleaningLogs("token-1", filters);
    const detail = await fetchAdminCleaningLogDetail("token-1", apiItem.id);
    const templates = await fetchAdminCleaningTemplates("token-1");

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/cleaning-logs?page=1&page_size=25"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(list.items[0]?.folio).toBe("CLN-000001");
    expect(list.metrics.highRiskCount).toBe("1");
    expect(detail.checklist[0]?.label).toBe("Retirar residuos");
    expect(detail.evidence.uploadSupported).toBe(false);
    expect(templates[0]?.requiresEvidence).toBe(true);
  });

  it("creates and completes cleaning logs through canonical endpoints", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() => mockJsonResponse(apiDetail, 201));

    await createAdminCleaningLog("token-1", {
      areaName: "Cocina",
      areaType: "PRODUCTION_AREA",
      branchId: "11111111-1111-4111-8111-111111111111",
      checklistItems: [
        {
          id: null,
          isCompleted: true,
          isRequired: true,
          label: "Retirar residuos",
          notes: null,
        },
      ],
      cleaningType: "SANITATION",
      completeImmediately: true,
      completedAt: "2026-05-21T15:30:00Z",
      equipmentName: "Mesa fria",
      evidenceNote: "Foto capturada",
      issueNotes: null,
      notes: "Turno matutino",
      responsibleUserId: "33333333-3333-4333-8333-333333333333",
      riskLevel: "HIGH",
      scheduledAt: "2026-05-21T15:00:00Z",
      shiftCode: "MORNING",
      taskName: null,
      taskTemplateId: "77777777-7777-4777-8777-777777777777",
    });

    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining("/v1/admin/cleaning-logs"),
      expect.objectContaining({
        body: expect.stringContaining('"complete_immediately":true'),
        method: "POST",
      }),
    );

    await completeAdminCleaningLog("token-1", apiItem.id, {
      checklistItems: [
        {
          id: "44444444-4444-4444-8444-444444444444",
          isCompleted: true,
          isRequired: true,
          label: "Retirar residuos",
          notes: null,
        },
      ],
      completedAt: "2026-05-21T15:45:00Z",
      evidenceNote: "Foto capturada",
      issueNotes: null,
      notes: "Cerrada",
    });

    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining(`/v1/admin/cleaning-logs/${apiItem.id}/complete`),
      expect.objectContaining({
        body: expect.stringContaining('"checklist_items"'),
        method: "POST",
      }),
    );
  });
});
