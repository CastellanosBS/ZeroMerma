import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildAdminSanitaryVerificationsListPath,
  completeAdminSanitaryVerification,
  createAdminSanitaryVerification,
  fetchAdminSanitaryTemplates,
  fetchAdminSanitaryVerificationDetail,
  fetchAdminSanitaryVerifications,
  startAdminSanitaryVerification,
} from "./api";
import type { AdminSanitaryListFilters } from "./types";

const filters: AdminSanitaryListFilters = {
  areaName: "all",
  areaType: "all",
  branchId: "all",
  dateFrom: null,
  dateTo: null,
  evidenceState: "all",
  incidentState: "all",
  inspectorUserId: "all",
  page: 1,
  pageSize: 25,
  processName: "all",
  processType: "all",
  result: "all",
  riskLevel: "all",
  search: "",
  status: "all",
  templateId: "all",
  warningState: "all",
};

const apiWarning = {
  code: "high_risk",
  message: "Verificacion de alto riesgo.",
  severity: "warning",
} as const;

const apiItem = {
  area_id: null,
  area_name: "Cocina",
  branch_id: "11111111-1111-4111-8111-111111111111",
  branch_name: "Sucursal Centro",
  checklist_total_count: 2,
  completed_at: null,
  equipment_id: null,
  equipment_name: "Mesa fria",
  failed_count: 0,
  folio: "SAN-000001",
  has_evidence: false,
  has_incident: false,
  id: "22222222-2222-4222-8222-222222222222",
  inspector_user_id: "33333333-3333-4333-8333-333333333333",
  inspector_user_name: "Ana Lopez",
  passed_count: 0,
  process_name: "Produccion diaria",
  result: "NOT_EVALUATED",
  risk_level: "HIGH",
  scheduled_at: "2026-05-21T15:00:00Z",
  status: "PENDING",
  template_name: "Revision sanitaria",
  updated_at: "2026-05-21T15:10:00Z",
  warning_state: "high_risk",
  warnings: [apiWarning],
} as const;

const apiDetail = {
  available_actions: {
    can_add_evidence: true,
    can_cancel: true,
    can_complete: true,
    can_create_incident: false,
    can_edit: true,
    can_export: false,
    can_print: false,
    can_start: true,
    note: "Incidencias requieren backend dedicado.",
  },
  checklist_results: [
    {
      display_order: 1,
      evidence_required_on_failure: false,
      expected_standard: "Sin residuos visibles.",
      id: "44444444-4444-4444-8444-444444444444",
      is_required: true,
      label: "Superficies limpias",
      notes: null,
      result: "PENDING",
      risk_level: "HIGH",
    },
  ],
  checklist_template: {
    area_type: "PRODUCTION_AREA",
    description: "Revision de produccion",
    failed_items: 0,
    frequency: "DAILY",
    passed_items: 0,
    pass_threshold_percent: 80,
    process_type: "PRODUCTION",
    risk_level: "HIGH",
    template_id: "77777777-7777-4777-8777-777777777777",
    template_name: "Revision sanitaria",
    total_items: 1,
  },
  evidence: {
    empty_state: "Esta verificacion no tiene evidencia adjunta.",
    evidence_note: null,
    files: [],
    has_evidence: false,
    is_supported: true,
    upload_supported: false,
  },
  findings_observations: {
    cancellation_reason: null,
    failed_required_count: 0,
    findings_notes: null,
    follow_up_due_at: null,
    follow_up_required: false,
    notes: "Turno matutino",
  },
  overview: {
    area_name: "Cocina",
    branch_id: "11111111-1111-4111-8111-111111111111",
    branch_name: "Sucursal Centro",
    completed_at: null,
    created_at: "2026-05-21T15:05:00Z",
    created_by_user_id: "66666666-6666-4666-8666-666666666666",
    created_by_user_name: "Admin",
    equipment_name: "Mesa fria",
    folio: "SAN-000001",
    id: "22222222-2222-4222-8222-222222222222",
    inspector_user_id: "33333333-3333-4333-8333-333333333333",
    inspector_user_name: "Ana Lopez",
    process_name: "Produccion diaria",
    result: "NOT_EVALUATED",
    risk_level: "HIGH",
    scheduled_at: "2026-05-21T15:00:00Z",
    started_at: null,
    status: "PENDING",
    warning_state: "high_risk",
  },
  related_cleaning_logs: [],
  related_documents: [],
  scope: {
    area_name: "Cocina",
    area_type: "PRODUCTION_AREA",
    branch_code: "CENTRO",
    branch_id: "11111111-1111-4111-8111-111111111111",
    branch_name: "Sucursal Centro",
    equipment_name: "Mesa fria",
    process_name: "Produccion diaria",
    process_type: "PRODUCTION",
  },
  score_result: {
    max_score: null,
    percentage: null,
    result: "NOT_EVALUATED",
    score: 0,
    threshold_percent: 80,
  },
  warnings: [apiWarning],
} as const;

const apiTemplate = {
  area_type: "PRODUCTION_AREA",
  description: "Revision de produccion",
  frequency: "DAILY",
  id: "77777777-7777-4777-8777-777777777777",
  is_active: true,
  items: [
    {
      description: null,
      display_order: 1,
      evidence_required_on_failure: false,
      expected_standard: "Sin residuos visibles.",
      id: "88888888-8888-4888-8888-888888888888",
      is_required: true,
      label: "Superficies limpias",
      risk_level: "HIGH",
    },
  ],
  name: "Revision sanitaria",
  pass_threshold_percent: 80,
  process_type: "PRODUCTION",
  requires_evidence_on_failure: true,
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

describe("admin sanitary verifications API boundary", () => {
  it("builds sanitary verification query parameters", () => {
    const path = buildAdminSanitaryVerificationsListPath({
      ...filters,
      areaType: "PRODUCTION_AREA",
      branchId: "branch-1",
      dateFrom: "2026-05-21",
      evidenceState: "without_evidence",
      result: "FAILED",
      riskLevel: "HIGH",
      search: "cocina",
      status: "PENDING",
      warningState: "high_risk",
    });

    expect(path).toContain("/v1/admin/sanitary-verifications?");
    expect(path).toContain("branch_id=branch-1");
    expect(path).toContain("area_type=PRODUCTION_AREA");
    expect(path).toContain("date_from=2026-05-21T00%3A00%3A00.000Z");
    expect(path).toContain("evidence_state=without_evidence");
    expect(path).toContain("result=FAILED");
    expect(path).toContain("risk_level=HIGH");
    expect(path).toContain("search=cocina");
    expect(path).toContain("status=PENDING");
    expect(path).toContain("warning_state=high_risk");
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
          evidence_states: [{ id: "without_evidence", label: "Sin evidencia" }],
          incident_states: [{ id: "with_incident", label: "Con incidencia" }],
          inspectors: [{ id: "user-1", label: "Ana Lopez" }],
          process_types: [{ id: "PRODUCTION", label: "Produccion" }],
          processes: [{ id: "Produccion diaria", label: "Produccion diaria" }],
          results: [{ id: "NOT_EVALUATED", label: "Sin evaluar" }],
          risk_levels: [{ id: "HIGH", label: "Alto" }],
          statuses: [{ id: "PENDING", label: "Pendiente" }],
          templates: [{ id: apiTemplate.id, label: "Revision sanitaria" }],
        },
        is_backend_connected: true,
        items: [apiItem],
        metrics: {
          failed_count: 0,
          high_risk_count: 1,
          pending_count: 1,
          passed_count: 0,
          requires_follow_up_count: 0,
          total_count: 1,
          with_evidence_count: 0,
          with_incident_count: 0,
        },
        page: 1,
        page_size: 25,
        total: 1,
      });
    });

    const list = await fetchAdminSanitaryVerifications("token-1", filters);
    const detail = await fetchAdminSanitaryVerificationDetail("token-1", apiItem.id);
    const templates = await fetchAdminSanitaryTemplates("token-1");

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/sanitary-verifications?page=1&page_size=25"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(list.items[0]?.folio).toBe("SAN-000001");
    expect(list.metrics.highRiskCount).toBe("1");
    expect(detail.checklistResults[0]?.label).toBe("Superficies limpias");
    expect(detail.evidence.uploadSupported).toBe(false);
    expect(templates[0]?.requiresEvidenceOnFailure).toBe(true);
  });

  it("creates, starts and completes sanitary verifications through canonical endpoints", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() => mockJsonResponse(apiDetail, 201));

    await createAdminSanitaryVerification("token-1", {
      areaName: "Cocina",
      areaType: "PRODUCTION_AREA",
      branchId: "11111111-1111-4111-8111-111111111111",
      checklistResults: [
        {
          evidenceRequiredOnFailure: false,
          expectedStandard: "Sin residuos visibles.",
          id: null,
          isRequired: true,
          label: "Superficies limpias",
          notes: null,
          result: "PASSED",
          riskLevel: "HIGH",
        },
      ],
      completeImmediately: true,
      completedAt: "2026-05-21T15:30:00Z",
      equipmentName: "Mesa fria",
      evidenceNote: "Foto capturada",
      findingsNotes: null,
      inspectorUserId: "33333333-3333-4333-8333-333333333333",
      notes: "Turno matutino",
      processName: "Produccion diaria",
      processType: "PRODUCTION",
      riskLevel: "HIGH",
      scheduledAt: "2026-05-21T15:00:00Z",
      templateId: "77777777-7777-4777-8777-777777777777",
      templateName: null,
    });

    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining("/v1/admin/sanitary-verifications"),
      expect.objectContaining({
        body: expect.stringContaining('"complete_immediately":true'),
        method: "POST",
      }),
    );

    await startAdminSanitaryVerification("token-1", apiItem.id);
    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining(`/v1/admin/sanitary-verifications/${apiItem.id}/start`),
      expect.objectContaining({ method: "POST" }),
    );

    await completeAdminSanitaryVerification("token-1", apiItem.id, {
      checklistResults: [
        {
          evidenceRequiredOnFailure: false,
          expectedStandard: "Sin residuos visibles.",
          id: "44444444-4444-4444-8444-444444444444",
          isRequired: true,
          label: "Superficies limpias",
          notes: null,
          result: "PASSED",
          riskLevel: "HIGH",
        },
      ],
      completedAt: "2026-05-21T15:45:00Z",
      evidenceNote: "Foto capturada",
      findingsNotes: null,
      notes: "Cerrada",
    });

    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining(`/v1/admin/sanitary-verifications/${apiItem.id}/complete`),
      expect.objectContaining({
        body: expect.stringContaining('"checklist_results"'),
        method: "POST",
      }),
    );
  });
});
