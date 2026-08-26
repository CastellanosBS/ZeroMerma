import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminCleaningLogDetailPanel } from "./components/AdminCleaningLogDetailPanel";
import { AdminCleaningLogWorkflowPanel } from "./components/AdminCleaningLogWorkflowPanel";
import { AdminCleaningLogsFilters } from "./components/AdminCleaningLogsFilters";
import { AdminCleaningLogsTable } from "./components/AdminCleaningLogsTable";
import { AdminCleaningLogsPage } from "./pages/AdminCleaningLogsPage";
import type {
  AdminCleaningFilterOptions,
  AdminCleaningListFilters,
  AdminCleaningLogDetail,
  AdminCleaningLogListItem,
  AdminCleaningTemplate,
} from "./types";

const filterOptions: AdminCleaningFilterOptions = {
  areaTypes: [{ id: "PRODUCTION_AREA", label: "Produccion" }],
  areas: [{ id: "Cocina", label: "Cocina" }],
  branches: [{ id: "branch-1", label: "Sucursal Centro" }],
  cleaningTypes: [{ id: "SANITATION", label: "Sanitizacion" }],
  evidenceStates: [{ id: "without_evidence", label: "Sin evidencia" }],
  observationStates: [{ id: "with_observations", label: "Con observaciones" }],
  responsibleUsers: [{ id: "user-1", label: "Ana Lopez" }],
  riskLevels: [{ id: "HIGH", label: "Alto" }],
  shifts: [{ id: "MORNING", label: "Matutino" }],
  statuses: [{ id: "PENDING", label: "Pendiente" }],
  templates: [{ id: "template-1", label: "Cocina diaria" }],
};

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

const cleaningLog: AdminCleaningLogListItem = {
  areaId: null,
  areaName: "Cocina",
  branchId: "branch-1",
  branchName: "Sucursal Centro",
  checklistCompletedCount: 1,
  checklistTotalCount: 2,
  cleaningType: "SANITATION",
  completedAt: null,
  equipmentId: null,
  equipmentName: "Mesa fria",
  folio: "CLN-000001",
  hasEvidence: true,
  hasObservations: true,
  id: "cleaning-log-1",
  responsibleUserId: "user-1",
  responsibleUserName: "Ana Lopez",
  riskLevel: "HIGH",
  scheduledAt: "2026-05-21T15:00:00Z",
  shiftCode: "MORNING",
  status: "PENDING",
  taskName: "Sanitizacion de cocina",
  updatedAt: "2026-05-21T15:10:00Z",
  warningState: "high_risk",
  warnings: [{ code: "high_risk", message: "Bitacora de alto riesgo.", severity: "warning" }],
};

const cleaningDetail: AdminCleaningLogDetail = {
  availableActions: {
    canAddEvidence: true,
    canCancel: true,
    canComplete: true,
    canCreateIncident: true,
    canEdit: true,
    canExport: false,
    canPrint: false,
    note: "Incidencias, adjuntos de archivo y exportacion requieren contratos backend dedicados.",
  },
  checklist: [
    {
      displayOrder: 1,
      id: "check-1",
      isCompleted: true,
      isRequired: true,
      label: "Retirar residuos",
      notes: null,
    },
    {
      displayOrder: 2,
      id: "check-2",
      isCompleted: false,
      isRequired: true,
      label: "Sanitizar mesa",
      notes: null,
    },
  ],
  evidence: {
    emptyState: "Esta bitacora no tiene evidencia adjunta.",
    evidenceNote: "Foto capturada en cierre",
    files: [],
    hasEvidence: true,
    isSupported: true,
    uploadSupported: false,
  },
  locationArea: {
    areaName: "Cocina",
    areaType: "PRODUCTION_AREA",
    branchCode: "CENTRO",
    branchId: "branch-1",
    branchName: "Sucursal Centro",
    equipmentName: "Mesa fria",
  },
  observationsIssues: {
    cancellationReason: null,
    correctiveNote: null,
    incompleteRequiredCount: 1,
    issueNotes: "Queda punto pendiente.",
    notes: "Turno matutino",
  },
  overview: {
    ...cleaningLog,
    createdAt: "2026-05-21T14:50:00Z",
    createdByUserId: "admin-1",
    createdByUserName: "Admin",
    startedAt: null,
  },
  relatedDocuments: [],
  taskTemplate: {
    cleaningType: "SANITATION",
    estimatedDurationMinutes: 20,
    frequency: "DAILY",
    methodSummary: "Limpiar y sanitizar superficies.",
    requiredTools: "Sanitizante",
    riskLevel: "HIGH",
    taskName: "Sanitizacion de cocina",
    taskTemplateId: "template-1",
    taskTemplateName: "Cocina diaria",
  },
  warnings: [{ code: "high_risk", message: "Bitacora de alto riesgo.", severity: "warning" }],
};

const template: AdminCleaningTemplate = {
  areaType: "PRODUCTION_AREA",
  cleaningType: "SANITATION",
  description: "Cierre de cocina",
  estimatedDurationMinutes: 20,
  frequency: "DAILY",
  id: "template-1",
  isActive: true,
  items: [
    {
      description: null,
      displayOrder: 1,
      id: "template-item-1",
      isRequired: true,
      label: "Retirar residuos",
    },
  ],
  methodSummary: "Limpiar y sanitizar superficies.",
  name: "Cocina diaria",
  requiredTools: "Sanitizante",
  requiresEvidence: true,
  riskLevel: "HIGH",
};

function render(element: ReactElement) {
  return renderToString(element);
}

describe("admin cleaning logs UI components", () => {
  it("renders the page shell with the canonical action", () => {
    const queryClient = new QueryClient();
    const html = render(
      <QueryClientProvider client={queryClient}>
        <AdminCleaningLogsPage />
      </QueryClientProvider>,
    );

    expect(html).toContain("Bitacoras de limpieza");
    expect(html).toContain("Nueva bitacora");
    expect(html).toContain(
      "Selecciona una bitacora para revisar checklist, responsable, evidencia y documentos relacionados.",
    );
  });

  it("renders compact filter toolbar", () => {
    const html = render(
      <AdminCleaningLogsFilters
        filters={filters}
        isBackendConnected={true}
        options={filterOptions}
        onChange={() => undefined}
      />,
    );

    expect(html).toContain("Folio, area, tarea");
    expect(html).toContain("Filtros");
    expect(html).toContain("API conectada");
    expect(html).not.toContain("Responsable");
  });

  it("renders empty and populated cleaning-log table states", () => {
    const emptyHtml = render(
      <AdminCleaningLogsTable
        cleaningLogs={[]}
        page={1}
        pageSize={25}
        total={0}
        onCopyFolio={() => undefined}
        onPageChange={() => undefined}
        onRegisterCompletion={() => undefined}
        onSelectCleaningLog={() => undefined}
      />,
    );
    expect(emptyHtml).toContain("No hay bitacoras de limpieza para los filtros seleccionados.");

    const tableHtml = render(
      <AdminCleaningLogsTable
        cleaningLogs={[cleaningLog]}
        page={1}
        pageSize={25}
        selectedCleaningLogId={cleaningLog.id}
        total={1}
        onCopyFolio={() => undefined}
        onPageChange={() => undefined}
        onRegisterCompletion={() => undefined}
        onSelectCleaningLog={() => undefined}
      />,
    );

    expect(tableHtml).toContain("Folio");
    expect(tableHtml).toContain("CLN-000001");
    expect(tableHtml).toContain("Sanitizacion de cocina");
    expect(tableHtml).toContain("Con evidencia");
    expect(tableHtml).toContain("Completar");
  });

  it("renders detail sections, checklist, evidence and related empty states", () => {
    const html = render(
      <AdminCleaningLogDetailPanel
        detail={cleaningDetail}
        selectedCleaningLog={cleaningLog}
        onCopyFolio={() => undefined}
        onRegisterCompletion={() => undefined}
      />,
    );

    expect(html).toContain("Resumen");
    expect(html).toContain("Ubicacion / area");
    expect(html).toContain("Checklist");
    expect(html).toContain("Retirar residuos");
    expect(html).toContain("Foto capturada en cierre");
    expect(html).toContain("Esta bitacora no tiene documentos relacionados.");
    expect(html).toContain("Crear incidencia");
  });

  it("renders create and completion workflows with validation context", () => {
    const createHtml = render(
      <AdminCleaningLogWorkflowPanel
        detail={null}
        mode="create"
        options={filterOptions}
        templates={[template]}
        onCancel={() => undefined}
        onComplete={() => undefined}
        onCreate={() => undefined}
      />,
    );

    expect(createHtml).toContain("Nueva bitacora");
    expect(createHtml).toContain("Cocina diaria");
    expect(createHtml).toContain("Checklist");
    expect(createHtml).toContain("Crear y completar inmediatamente");

    const completeHtml = render(
      <AdminCleaningLogWorkflowPanel
        detail={cleaningDetail}
        mode="complete"
        options={filterOptions}
        templates={[template]}
        onCancel={() => undefined}
        onComplete={() => undefined}
        onCreate={() => undefined}
      />,
    );

    expect(completeHtml).toContain("Completar CLN-000001");
    expect(completeHtml).toContain("Sanitizar mesa");
    expect(completeHtml).toContain("Completar bitacora");
  });
});
