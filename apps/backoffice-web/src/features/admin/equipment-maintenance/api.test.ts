import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildAdminEquipmentListPath,
  completeAdminMaintenance,
  createAdminEquipment,
  createAdminMaintenance,
  fetchAdminEquipment,
  fetchAdminEquipmentDetail,
  startAdminMaintenance,
  updateAdminEquipmentStatus,
} from "./api";
import type { AdminEquipmentListFilters } from "./types";

const filters: AdminEquipmentListFilters = {
  areaName: "all",
  areaType: "all",
  branchId: "all",
  dateFrom: null,
  dateTo: null,
  equipmentType: "all",
  incidentState: "all",
  maintenanceStatus: "all",
  maintenanceType: "all",
  operationalStatus: "all",
  overdueState: "all",
  page: 1,
  pageSize: 25,
  providerName: "all",
  riskLevel: "all",
  search: "",
  technicianName: "all",
};

const apiWarning = {
  code: "high_risk",
  message: "Equipo critico con mantenimiento vencido.",
  severity: "critical",
} as const;

const apiMaintenance = {
  completed_at: null,
  cost: null,
  evidence_note: null,
  folio: "MNT-000001",
  has_evidence: false,
  id: "33333333-3333-4333-8333-333333333333",
  maintenance_type: "CORRECTIVE",
  notes: "Ruido en motor.",
  provider_name: "Tecnico Norte",
  related_incident_reference: "INC-000010",
  result: "NOT_COMPLETED",
  scheduled_at: "2026-05-21T16:00:00Z",
  started_at: null,
  status: "PENDING",
  technician_name: "Luis Perez",
  warning_state: "high_risk",
} as const;

const apiItem = {
  area_id: null,
  area_name: "Produccion",
  branch_id: "11111111-1111-4111-8111-111111111111",
  branch_name: "Sucursal Centro",
  code: "EQ-HOR-01",
  equipment_type: "OVEN",
  id: "22222222-2222-4222-8222-222222222222",
  last_maintenance_at: "2026-05-01T10:00:00Z",
  maintenance_status: "OVERDUE",
  name: "Horno principal",
  next_maintenance_at: "2026-05-20T10:00:00Z",
  open_incident_count: 1,
  operational_status: "OUT_OF_SERVICE",
  period_cost: "1200.50",
  risk_level: "HIGH",
  updated_at: "2026-05-21T15:10:00Z",
  warning_state: "high_risk",
  warnings: [apiWarning],
} as const;

const apiDetail = {
  available_actions: {
    can_cancel_maintenance: true,
    can_complete_maintenance: true,
    can_create_corrective: true,
    can_create_preventive: true,
    can_edit_equipment: true,
    can_export: false,
    can_mark_operational: false,
    can_mark_out_of_service: true,
    can_print: false,
    can_start_maintenance: true,
    note: "Incidencias y evidencia de archivo requieren contratos dedicados.",
  },
  cost_context: {
    last_service_cost: "1200.50",
    period_cost: "1200.50",
    total_lifetime_cost: "2400.00",
    warranty_note: "Garantia vigente.",
  },
  current_maintenance_status: {
    current_linked_incident: "INC-000010",
    current_open_maintenance: apiMaintenance,
    downtime_state: "out_of_service",
    last_maintenance_at: "2026-05-01T10:00:00Z",
    last_maintenance_result: "COMPLETED_WITH_OBSERVATIONS",
    last_maintenance_type: "PREVENTIVE",
    next_scheduled_maintenance_at: "2026-05-20T10:00:00Z",
    overdue: true,
  },
  evidence: {
    empty_state: "Este mantenimiento no tiene evidencia adjunta.",
    files: [],
    has_evidence: true,
    is_supported: true,
    latest_evidence_note: "Reporte tecnico adjunto en archivo interno.",
    upload_supported: false,
  },
  incidents_related: [
    {
      folio: "INC-000010",
      route_hint: "/admin/incidencias",
      severity: "HIGH",
      status: "OPEN",
    },
  ],
  location_context: {
    area_name: "Produccion",
    area_type: "PRODUCTION",
    branch_code: "CENTRO",
    branch_id: "11111111-1111-4111-8111-111111111111",
    branch_name: "Sucursal Centro",
    food_safety_critical: true,
    is_critical: true,
  },
  maintenance_history: [apiMaintenance],
  metadata: {
    brand: "BakeTech",
    maintenance_frequency_days: 30,
    model: "BT-900",
    notes: "Equipo critico para produccion.",
    provider_name: "Tecnico Norte",
    purchase_date: "2025-01-10",
    serial_number: "SER-900",
    warranty_expires_at: "2027-01-10",
  },
  overview: {
    ...apiItem,
    created_at: "2026-01-10T09:00:00Z",
  },
  related_documents: [
    {
      document_id: "44444444-4444-4444-8444-444444444444",
      document_type: "cleaning_log",
      folio: "CLN-000100",
      route_hint: "/admin/bitacoras-limpieza",
      status: "COMPLETED",
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

describe("admin equipment maintenance API boundary", () => {
  it("builds equipment maintenance query parameters", () => {
    const path = buildAdminEquipmentListPath({
      ...filters,
      branchId: "branch-1",
      dateFrom: "2026-05-21",
      equipmentType: "OVEN",
      incidentState: "with_incident",
      maintenanceStatus: "OVERDUE",
      maintenanceType: "CORRECTIVE",
      operationalStatus: "OUT_OF_SERVICE",
      overdueState: "overdue",
      providerName: "Tecnico Norte",
      riskLevel: "HIGH",
      search: "horno",
      technicianName: "Luis",
    });

    expect(path).toContain("/v1/admin/equipment-maintenance/equipment?");
    expect(path).toContain("branch_id=branch-1");
    expect(path).toContain("date_from=2026-05-21T00%3A00%3A00.000Z");
    expect(path).toContain("equipment_type=OVEN");
    expect(path).toContain("incident_state=with_incident");
    expect(path).toContain("maintenance_status=OVERDUE");
    expect(path).toContain("maintenance_type=CORRECTIVE");
    expect(path).toContain("operational_status=OUT_OF_SERVICE");
    expect(path).toContain("overdue_state=overdue");
    expect(path).toContain("provider_name=Tecnico+Norte");
    expect(path).toContain("risk_level=HIGH");
    expect(path).toContain("search=horno");
    expect(path).toContain("technician_name=Luis");
  });

  it("fetches equipment list and detail from backend", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes(apiItem.id)) {
        return mockJsonResponse(apiDetail);
      }
      return mockJsonResponse({
        backend_contract: undefined,
        filter_options: {
          area_types: [{ id: "PRODUCTION", label: "Produccion" }],
          areas: [{ id: "Produccion", label: "Produccion" }],
          branches: [{ id: "branch-1", label: "Sucursal Centro" }],
          equipment_types: [{ id: "OVEN", label: "Horno" }],
          incident_states: [{ id: "with_incident", label: "Con incidencia" }],
          maintenance_statuses: [{ id: "OVERDUE", label: "Vencido" }],
          maintenance_types: [{ id: "CORRECTIVE", label: "Correctivo" }],
          operational_statuses: [{ id: "OUT_OF_SERVICE", label: "Fuera de servicio" }],
          providers: [{ id: "Tecnico Norte", label: "Tecnico Norte" }],
          risk_levels: [{ id: "HIGH", label: "Alto" }],
          technicians: [{ id: "Luis Perez", label: "Luis Perez" }],
        },
        is_backend_connected: true,
        items: [apiItem],
        metrics: {
          corrective_open_count: 1,
          high_risk_count: 1,
          operational_count: 0,
          out_of_service_count: 1,
          overdue_count: 1,
          pending_maintenance_count: 1,
          period_cost: "1200.50",
          total_equipment_count: 1,
        },
        page: 1,
        page_size: 25,
        total: 1,
      });
    });

    const list = await fetchAdminEquipment("token-1", filters);
    const detail = await fetchAdminEquipmentDetail("token-1", apiItem.id);

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/equipment-maintenance/equipment?page=1&page_size=25"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(list.items[0]?.code).toBe("EQ-HOR-01");
    expect(list.metrics.periodCost).toContain("$1,200.50");
    expect(detail.currentMaintenanceStatus.currentOpenMaintenance?.folio).toBe("MNT-000001");
    expect(detail.evidence.uploadSupported).toBe(false);
    expect(detail.relatedDocuments[0]?.folio).toBe("CLN-000100");
  });

  it("creates equipment and maintenance through canonical endpoints", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() => mockJsonResponse(apiDetail, 201));

    await createAdminEquipment("token-1", {
      areaName: "Produccion",
      areaType: "PRODUCTION",
      branchId: "11111111-1111-4111-8111-111111111111",
      brand: "BakeTech",
      code: "EQ-HOR-01",
      equipmentType: "OVEN",
      foodSafetyCritical: true,
      isCritical: true,
      maintenanceFrequencyDays: 30,
      model: "BT-900",
      name: "Horno principal",
      notes: "Equipo critico.",
      operationalStatus: "OPERATIONAL",
      providerName: "Tecnico Norte",
      purchaseDate: "2025-01-10",
      riskLevel: "HIGH",
      serialNumber: "SER-900",
      warrantyExpiresAt: "2027-01-10",
    });

    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining("/v1/admin/equipment-maintenance/equipment"),
      expect.objectContaining({
        body: expect.stringContaining('"code":"EQ-HOR-01"'),
        method: "POST",
      }),
    );

    await updateAdminEquipmentStatus("token-1", apiItem.id, {
      operationalStatus: "OUT_OF_SERVICE",
      reason: "Falla de motor.",
    });

    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining(`/v1/admin/equipment-maintenance/equipment/${apiItem.id}/status`),
      expect.objectContaining({
        body: expect.stringContaining('"operational_status":"OUT_OF_SERVICE"'),
        method: "POST",
      }),
    );

    await createAdminMaintenance("token-1", {
      description: "Revision correctiva por ruido.",
      equipmentId: apiItem.id,
      expectedCost: "1000",
      maintenanceType: "CORRECTIVE",
      providerName: "Tecnico Norte",
      relatedIncidentReference: "INC-000010",
      scheduledAt: "2026-05-21T16:00:00Z",
      sourceDocumentReference: "SAN-000010",
      sourceDocumentType: "sanitary_verification",
      startImmediately: true,
      status: "PENDING",
      technicianName: "Luis Perez",
    });

    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining("/v1/admin/equipment-maintenance/maintenance"),
      expect.objectContaining({
        body: expect.stringContaining('"maintenance_type":"CORRECTIVE"'),
        method: "POST",
      }),
    );
  });

  it("starts and completes maintenance through canonical endpoints", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() => mockJsonResponse(apiDetail, 200));

    await startAdminMaintenance("token-1", apiMaintenance.id);
    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining(`/v1/admin/equipment-maintenance/maintenance/${apiMaintenance.id}/start`),
      expect.objectContaining({ method: "POST" }),
    );

    await completeAdminMaintenance("token-1", apiMaintenance.id, {
      completedAt: "2026-05-21T18:00:00Z",
      cost: "1200.50",
      equipmentStatusAfterService: "OPERATIONAL",
      evidenceNote: "Reporte tecnico interno.",
      notes: "Cambio de banda.",
      result: "COMPLETED_SUCCESSFULLY",
      technicianName: "Luis Perez",
    });

    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining(
        `/v1/admin/equipment-maintenance/maintenance/${apiMaintenance.id}/complete`,
      ),
      expect.objectContaining({
        body: expect.stringContaining('"result":"COMPLETED_SUCCESSFULLY"'),
        method: "POST",
      }),
    );
  });
});
