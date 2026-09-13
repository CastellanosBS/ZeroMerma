import { withCapabilities } from "../../../test-support/authorization";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminEquipmentMaintenanceDetailPanel } from "./components/AdminEquipmentMaintenanceDetailPanel";
import { AdminEquipmentMaintenanceFilters } from "./components/AdminEquipmentMaintenanceFilters";
import { AdminEquipmentMaintenanceTable } from "./components/AdminEquipmentMaintenanceTable";
import { AdminEquipmentMaintenanceWorkflowPanel } from "./components/AdminEquipmentMaintenanceWorkflowPanel";
import { AdminEquipmentMaintenancePage } from "./pages/AdminEquipmentMaintenancePage";
import type {
  AdminEquipmentDetail,
  AdminEquipmentFilterOptions,
  AdminEquipmentListFilters,
  AdminEquipmentListItem,
  AdminMaintenanceRecordListItem,
} from "./types";

const filterOptions: AdminEquipmentFilterOptions = {
  areaTypes: [{ id: "PRODUCTION", label: "Produccion" }],
  areas: [{ id: "Produccion", label: "Produccion" }],
  branches: [{ id: "branch-1", label: "Sucursal Centro" }],
  equipmentTypes: [{ id: "OVEN", label: "Horno" }],
  incidentStates: [{ id: "with_incident", label: "Con incidencia" }],
  maintenanceStatuses: [{ id: "OVERDUE", label: "Vencido" }],
  maintenanceTypes: [
    { id: "PREVENTIVE", label: "Preventivo" },
    { id: "CORRECTIVE", label: "Correctivo" },
  ],
  operationalStatuses: [
    { id: "OPERATIONAL", label: "Operativo" },
    { id: "OUT_OF_SERVICE", label: "Fuera de servicio" },
  ],
  providers: [{ id: "Tecnico Norte", label: "Tecnico Norte" }],
  riskLevels: [{ id: "HIGH", label: "Alto" }],
  technicians: [{ id: "Luis Perez", label: "Luis Perez" }],
};

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

const equipment: AdminEquipmentListItem = {
  areaId: null,
  areaName: "Produccion",
  branchId: "branch-1",
  branchName: "Sucursal Centro",
  code: "EQ-HOR-01",
  equipmentType: "OVEN",
  id: "equipment-1",
  lastMaintenanceAt: "2026-05-01T10:00:00Z",
  maintenanceStatus: "OVERDUE",
  name: "Horno principal",
  nextMaintenanceAt: "2026-05-20T10:00:00Z",
  openIncidentCount: 1,
  operationalStatus: "OUT_OF_SERVICE",
  periodCost: "1200.50",
  riskLevel: "HIGH",
  updatedAt: "2026-05-21T15:10:00Z",
  warningState: "high_risk",
  warnings: [
    {
      code: "high_risk",
      message: "Equipo critico con mantenimiento vencido.",
      severity: "critical",
    },
  ],
};

const maintenanceRecord: AdminMaintenanceRecordListItem = {
  completedAt: null,
  cost: null,
  evidenceNote: null,
  folio: "MNT-000001",
  hasEvidence: false,
  id: "maintenance-1",
  maintenanceType: "CORRECTIVE",
  notes: "Ruido en motor.",
  providerName: "Tecnico Norte",
  relatedIncidentReference: "INC-000010",
  result: "NOT_COMPLETED",
  scheduledAt: "2026-05-21T16:00:00Z",
  startedAt: null,
  status: "PENDING",
  technicianName: "Luis Perez",
  warningState: "high_risk",
};

const detail: AdminEquipmentDetail = {
  availableActions: {
    canCancelMaintenance: true,
    canCompleteMaintenance: true,
    canCreateCorrective: true,
    canCreatePreventive: true,
    canEditEquipment: true,
    canExport: false,
    canMarkOperational: false,
    canMarkOutOfService: true,
    canPrint: false,
    canStartMaintenance: true,
    note: "Incidencias y evidencia de archivo requieren contratos dedicados.",
  },
  costContext: {
    lastServiceCost: "1200.50",
    periodCost: "1200.50",
    totalLifetimeCost: "2400.00",
    warrantyNote: "Garantia vigente.",
  },
  currentMaintenanceStatus: {
    currentLinkedIncident: "INC-000010",
    currentOpenMaintenance: maintenanceRecord,
    downtimeState: "out_of_service",
    lastMaintenanceAt: "2026-05-01T10:00:00Z",
    lastMaintenanceResult: "COMPLETED_WITH_OBSERVATIONS",
    lastMaintenanceType: "PREVENTIVE",
    nextScheduledMaintenanceAt: "2026-05-20T10:00:00Z",
    overdue: true,
  },
  evidence: {
    emptyState: "Este mantenimiento no tiene evidencia adjunta.",
    files: [],
    hasEvidence: true,
    isSupported: true,
    latestEvidenceNote: "Reporte tecnico adjunto en archivo interno.",
    uploadSupported: false,
  },
  incidentsRelated: [
    {
      folio: "INC-000010",
      routeHint: "/admin/incidencias",
      severity: "HIGH",
      status: "OPEN",
    },
  ],
  locationContext: {
    areaName: "Produccion",
    areaType: "PRODUCTION",
    branchCode: "CENTRO",
    branchId: "branch-1",
    branchName: "Sucursal Centro",
    foodSafetyCritical: true,
    isCritical: true,
  },
  maintenanceHistory: [maintenanceRecord],
  metadata: {
    brand: "BakeTech",
    maintenanceFrequencyDays: 30,
    model: "BT-900",
    notes: "Equipo critico para produccion.",
    providerName: "Tecnico Norte",
    purchaseDate: "2025-01-10",
    serialNumber: "SER-900",
    warrantyExpiresAt: "2027-01-10",
  },
  overview: {
    ...equipment,
    createdAt: "2026-01-10T09:00:00Z",
  },
  relatedDocuments: [
    {
      documentId: "cleaning-1",
      documentType: "cleaning_log",
      folio: "CLN-000100",
      routeHint: "/admin/bitacoras-limpieza",
      status: "COMPLETED",
    },
  ],
  warnings: equipment.warnings,
};

function render(element: ReactElement) {
  return renderToString(withCapabilities(element, ["quality_hygiene.manage"]));
}

describe("admin equipment maintenance UI components", () => {
  it("renders the page shell with the canonical action", () => {
    const queryClient = new QueryClient();
    const html = render(
      <QueryClientProvider client={queryClient}>
        <AdminEquipmentMaintenancePage />
      </QueryClientProvider>,
    );

    expect(html).toContain("Mantenimiento de equipos");
    expect(html).toContain("Nuevo equipo");
    expect(html).toContain(
      "Selecciona un equipo para revisar mantenimiento, incidencias, estado operativo y documentos relacionados.",
    );
  });

  it("renders compact search and filter entry point", () => {
    const html = render(
      <AdminEquipmentMaintenanceFilters
        filters={filters}
        isBackendConnected={true}
        options={filterOptions}
        onChange={() => undefined}
      />,
    );

    expect(html).toContain("Buscar");
    expect(html).toContain("Equipo, codigo, tecnico");
    expect(html).toContain("Filtros");
    expect(html).toContain("API conectada");
  });

  it("renders empty and populated equipment table states", () => {
    const emptyHtml = render(
      <AdminEquipmentMaintenanceTable
        equipment={[]}
        page={1}
        pageSize={25}
        total={0}
        onCopyCode={() => undefined}
        onCreateMaintenance={() => undefined}
        onPageChange={() => undefined}
        onSelectEquipment={() => undefined}
      />,
    );
    expect(emptyHtml).toContain("No hay equipos registrados para los filtros seleccionados.");

    const tableHtml = render(
      <AdminEquipmentMaintenanceTable
        equipment={[equipment]}
        page={1}
        pageSize={25}
        selectedEquipmentId={equipment.id}
        total={1}
        onCopyCode={() => undefined}
        onCreateMaintenance={() => undefined}
        onPageChange={() => undefined}
        onSelectEquipment={() => undefined}
      />,
    );

    expect(tableHtml).toContain("EQ-HOR-01");
    expect(tableHtml).toContain("Horno principal");
    expect(tableHtml).toContain("Fuera de servicio");
    expect(tableHtml).toContain("Mantto.");
  });

  it("renders equipment detail sections, history, incidents and evidence", () => {
    const html = render(
      <AdminEquipmentMaintenanceDetailPanel
        detail={detail}
        selectedEquipment={equipment}
        onCompleteMaintenance={() => undefined}
        onCopyCode={() => undefined}
        onCreateMaintenance={() => undefined}
        onMarkOperational={() => undefined}
        onMarkOutOfService={() => undefined}
        onStartMaintenance={() => undefined}
      />,
    );

    expect(html).toContain("Resumen del equipo");
    expect(html).toContain("Estado de mantenimiento actual");
    expect(html).toContain("Historial de mantenimiento");
    expect(html).toContain("MNT-000001");
    expect(html).toContain("INC-000010");
    expect(html).toContain("Reporte tecnico adjunto");
    expect(html).toContain("CLN-000100");
  });

  it("renders create, maintenance and completion workflows", () => {
    const createHtml = render(
      <AdminEquipmentMaintenanceWorkflowPanel
        equipment={[equipment]}
        maintenanceRecord={null}
        mode="equipment"
        options={filterOptions}
        selectedEquipment={null}
        onCancel={() => undefined}
        onCompleteMaintenance={() => undefined}
        onCreateEquipment={() => undefined}
        onCreateMaintenance={() => undefined}
      />,
    );
    expect(createHtml).toContain("Nuevo equipo");
    expect(createHtml).toContain("Codigo / activo");
    expect(createHtml).toContain("Guardar equipo");

    const maintenanceHtml = render(
      <AdminEquipmentMaintenanceWorkflowPanel
        equipment={[equipment]}
        maintenanceRecord={null}
        mode="maintenance"
        options={filterOptions}
        selectedEquipment={equipment}
        onCancel={() => undefined}
        onCompleteMaintenance={() => undefined}
        onCreateEquipment={() => undefined}
        onCreateMaintenance={() => undefined}
      />,
    );
    expect(maintenanceHtml).toContain("Nuevo mantenimiento");
    expect(maintenanceHtml).toContain("Iniciar ahora");
    expect(maintenanceHtml).toContain("Guardar mantenimiento");

    const completeHtml = render(
      <AdminEquipmentMaintenanceWorkflowPanel
        equipment={[equipment]}
        maintenanceRecord={maintenanceRecord}
        mode="complete"
        options={filterOptions}
        selectedEquipment={equipment}
        onCancel={() => undefined}
        onCompleteMaintenance={() => undefined}
        onCreateEquipment={() => undefined}
        onCreateMaintenance={() => undefined}
      />,
    );
    expect(completeHtml).toContain("Completar MNT-000001");
    expect(completeHtml).toContain("Estado posterior");
    expect(completeHtml).toContain("Completar mantenimiento");
  });
});
