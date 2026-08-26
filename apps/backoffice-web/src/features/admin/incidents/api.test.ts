import { afterEach, describe, expect, it, vi } from "vitest";

import {
  addAdminIncidentFollowUp,
  buildAdminIncidentsListPath,
  changeAdminIncidentStatus,
  createAdminIncident,
  fetchAdminIncidentDetail,
  fetchAdminIncidents,
  reopenAdminIncident,
  resolveAdminIncident,
} from "./api";
import type { AdminIncidentListFilters } from "./types";

const filters: AdminIncidentListFilters = {
  areaName: "all",
  branchId: "all",
  dateFrom: null,
  dateTo: null,
  dueState: "all",
  evidenceState: "all",
  incidentType: "all",
  page: 1,
  pageSize: 25,
  relatedDocumentState: "all",
  reportedByUserId: "all",
  responsibleUserId: "all",
  search: "",
  severity: "all",
  sourceType: "all",
  status: "all",
  warningState: "all",
};

const apiWarning = {
  code: "high_risk",
  message: "Incidencia de alto riesgo.",
  severity: "warning",
} as const;

const apiItem = {
  area_name: "Cocina",
  branch_id: "11111111-1111-4111-8111-111111111111",
  branch_name: "Sucursal Centro",
  created_at: "2026-05-21T15:00:00Z",
  due_at: "2026-05-22T18:00:00Z",
  folio: "INC-000001",
  has_evidence: true,
  id: "22222222-2222-4222-8222-222222222222",
  incident_type: "SANITATION_ISSUE",
  related_document_count: 1,
  reported_by_user_id: "33333333-3333-4333-8333-333333333333",
  reported_by_user_name: "Ana Lopez",
  responsible_user_id: "44444444-4444-4444-8444-444444444444",
  responsible_user_name: "Luis Perez",
  severity: "HIGH",
  source_reference: "SAN-000001",
  source_type: "SANITARY_VERIFICATION",
  status: "OPEN",
  title: "Sanitizante vencido",
  updated_at: "2026-05-21T15:10:00Z",
  warning_state: "high_risk",
  warnings: [apiWarning],
} as const;

const apiDetail = {
  available_actions: {
    can_add_evidence: true,
    can_add_follow_up: true,
    can_assign: true,
    can_cancel: true,
    can_create_corrective_action: true,
    can_create_maintenance: false,
    can_export: false,
    can_mark_in_progress: true,
    can_print: false,
    can_reopen: false,
    can_resolve: true,
    note: "Adjuntos de archivo aun no estan soportados.",
  },
  corrective_action: {
    corrective_action: "Cambiar sanitizante y repetir limpieza.",
    current_progress: "OPEN",
    due_at: "2026-05-22T18:00:00Z",
    responsible_user_id: "44444444-4444-4444-8444-444444444444",
    responsible_user_name: "Luis Perez",
    resolution_note: null,
    resolution_result: null,
    resolved_at: null,
  },
  description_classification: {
    description: "Se encontro sanitizante vencido en cocina.",
    food_safety_impact: true,
    incident_type: "SANITATION_ISSUE",
    notes: "Requiere seguimiento",
    operational_impact: "Area detenida temporalmente",
    risk_level: "HIGH",
    severity: "HIGH",
  },
  evidence: {
    empty_state: "Esta incidencia no tiene evidencia adjunta.",
    evidence_note: "Foto de etiqueta vencida",
    files: [],
    has_evidence: true,
    is_supported: true,
    upload_supported: false,
  },
  follow_ups: [
    {
      created_at: "2026-05-21T16:00:00Z",
      created_by_user_id: "33333333-3333-4333-8333-333333333333",
      created_by_user_name: "Ana Lopez",
      id: "55555555-5555-4555-8555-555555555555",
      note: "Se retiro el insumo vencido.",
      status_change: "IN_PROGRESS",
    },
  ],
  location_scope: {
    area_name: "Cocina",
    branch_code: "CENTRO",
    branch_id: "11111111-1111-4111-8111-111111111111",
    branch_name: "Sucursal Centro",
    equipment_name: null,
    process_name: "Limpieza de cierre",
    product_reference: null,
    production_reference: null,
  },
  overview: {
    ...apiItem,
    resolved_at: null,
  },
  related_documents: [
    {
      document_id: "66666666-6666-4666-8666-666666666666",
      document_type: "sanitary_verification",
      folio: "SAN-000001",
      route_hint: "/admin/verificaciones-sanitarias",
      status: "REQUIRES_FOLLOW_UP",
    },
  ],
  source_document: {
    empty_state: "Esta incidencia fue registrada manualmente y no tiene documento origen.",
    route_hint: "/admin/verificaciones-sanitarias",
    source_document_id: "66666666-6666-4666-8666-666666666666",
    source_reference: "SAN-000001",
    source_summary: "Verificacion fallida",
    source_type: "SANITARY_VERIFICATION",
  },
  timeline: [
    {
      label: "Creada",
      note: "Incidencia creada.",
      occurred_at: "2026-05-21T15:00:00Z",
      user_name: "Ana Lopez",
    },
  ],
  warnings: [apiWarning],
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

describe("admin incidents API boundary", () => {
  it("builds incident query parameters", () => {
    const path = buildAdminIncidentsListPath({
      ...filters,
      branchId: "branch-1",
      dateFrom: "2026-05-21",
      dueState: "overdue",
      evidenceState: "without_evidence",
      incidentType: "SANITATION_ISSUE",
      relatedDocumentState: "with_related",
      responsibleUserId: "unassigned",
      search: "sanitizante",
      severity: "HIGH",
      sourceType: "SANITARY_VERIFICATION",
      status: "OPEN",
      warningState: "high_risk",
    });

    expect(path).toContain("/v1/admin/incidents?");
    expect(path).toContain("branch_id=branch-1");
    expect(path).toContain("date_from=2026-05-21T00%3A00%3A00.000Z");
    expect(path).toContain("due_state=overdue");
    expect(path).toContain("incident_type=SANITATION_ISSUE");
    expect(path).toContain("related_document_state=with_related");
    expect(path).toContain("responsible_user_id=unassigned");
    expect(path).toContain("search=sanitizante");
    expect(path).toContain("severity=HIGH");
    expect(path).toContain("source_type=SANITARY_VERIFICATION");
    expect(path).toContain("status=OPEN");
    expect(path).toContain("warning_state=high_risk");
  });

  it("fetches list and detail from backend", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes(apiItem.id)) {
        return mockJsonResponse(apiDetail);
      }
      return mockJsonResponse({
        backend_contract: undefined,
        filter_options: {
          areas: [{ id: "Cocina", label: "Cocina" }],
          branches: [{ id: "branch-1", label: "Sucursal Centro" }],
          due_states: [{ id: "overdue", label: "Vencidas" }],
          evidence_states: [{ id: "with_evidence", label: "Con evidencia" }],
          incident_types: [{ id: "SANITATION_ISSUE", label: "Sanitaria" }],
          related_document_states: [{ id: "with_related", label: "Con documentos" }],
          reported_by_users: [{ id: "user-1", label: "Ana Lopez" }],
          responsible_users: [{ id: "user-2", label: "Luis Perez" }],
          severities: [{ id: "HIGH", label: "Alta" }],
          source_types: [{ id: "SANITARY_VERIFICATION", label: "Verificacion" }],
          statuses: [{ id: "OPEN", label: "Abierta" }],
        },
        is_backend_connected: true,
        items: [apiItem],
        metrics: {
          high_risk_count: 1,
          in_progress_count: 0,
          open_count: 1,
          overdue_count: 0,
          resolved_count: 0,
          sanitary_generated_count: 1,
          total_count: 1,
          with_evidence_count: 1,
        },
        page: 1,
        page_size: 25,
        total: 1,
      });
    });

    const list = await fetchAdminIncidents("token-1", filters);
    const detail = await fetchAdminIncidentDetail("token-1", apiItem.id);

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/incidents?page=1&page_size=25"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(list.items[0]?.folio).toBe("INC-000001");
    expect(list.metrics.highRiskCount).toBe("1");
    expect(detail.sourceDocument.sourceReference).toBe("SAN-000001");
    expect(detail.followUps[0]?.note).toBe("Se retiro el insumo vencido.");
  });

  it("creates, follows up, changes status, resolves and reopens incidents", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() => mockJsonResponse(apiDetail, 201));

    await createAdminIncident("token-1", {
      areaName: "Cocina",
      branchId: "11111111-1111-4111-8111-111111111111",
      correctiveAction: "Retirar insumo vencido.",
      description: "Se encontro sanitizante vencido.",
      dueAt: "2026-05-22T18:00:00Z",
      equipmentName: null,
      evidenceNote: "Foto capturada",
      foodSafetyImpact: true,
      incidentType: "SANITATION_ISSUE",
      notes: "Seguimiento requerido",
      operationalImpact: "Area detenida",
      processName: "Limpieza",
      productReference: null,
      productionReference: null,
      responsibleUserId: "44444444-4444-4444-8444-444444444444",
      severity: "HIGH",
      sourceDocumentId: "66666666-6666-4666-8666-666666666666",
      sourceReference: "SAN-000001",
      sourceSummary: "Verificacion fallida",
      sourceType: "SANITARY_VERIFICATION",
      title: "Sanitizante vencido",
    });
    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining("/v1/admin/incidents"),
      expect.objectContaining({
        body: expect.stringContaining('"food_safety_impact":true'),
        method: "POST",
      }),
    );

    await addAdminIncidentFollowUp("token-1", apiItem.id, {
      note: "Seguimiento registrado.",
      statusChange: "IN_PROGRESS",
    });
    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining(`/v1/admin/incidents/${apiItem.id}/follow-ups`),
      expect.objectContaining({ method: "POST" }),
    );

    await changeAdminIncidentStatus("token-1", apiItem.id, {
      cancellationReason: null,
      note: "Cambio de estado.",
      status: "IN_PROGRESS",
    });
    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining(`/v1/admin/incidents/${apiItem.id}/status`),
      expect.objectContaining({ method: "POST" }),
    );

    await resolveAdminIncident("token-1", apiItem.id, {
      evidenceNote: "Foto final",
      resolutionNote: "Se repuso sanitizante.",
      resolvedAt: "2026-05-21T18:00:00Z",
      result: "Corregida",
    });
    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining(`/v1/admin/incidents/${apiItem.id}/resolve`),
      expect.objectContaining({ method: "POST" }),
    );

    await reopenAdminIncident("token-1", apiItem.id, "Reabrir seguimiento.");
    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining(`/v1/admin/incidents/${apiItem.id}/reopen`),
      expect.objectContaining({ method: "POST" }),
    );
  });
});
