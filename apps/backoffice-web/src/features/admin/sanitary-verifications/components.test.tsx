import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminSanitaryVerificationDetailPanel } from "./components/AdminSanitaryVerificationDetailPanel";
import { AdminSanitaryVerificationWorkflowPanel } from "./components/AdminSanitaryVerificationWorkflowPanel";
import { AdminSanitaryVerificationsFilters } from "./components/AdminSanitaryVerificationsFilters";
import { AdminSanitaryVerificationsTable } from "./components/AdminSanitaryVerificationsTable";
import { AdminSanitaryVerificationsPage } from "./pages/AdminSanitaryVerificationsPage";
import type {
  AdminSanitaryFilterOptions,
  AdminSanitaryListFilters,
  AdminSanitaryTemplate,
  AdminSanitaryVerificationDetail,
  AdminSanitaryVerificationListItem,
} from "./types";

const filterOptions: AdminSanitaryFilterOptions = {
  areaTypes: [{ id: "PRODUCTION_AREA", label: "Produccion" }],
  areas: [{ id: "Cocina", label: "Cocina" }],
  branches: [{ id: "branch-1", label: "Sucursal Centro" }],
  evidenceStates: [{ id: "without_evidence", label: "Sin evidencia" }],
  incidentStates: [{ id: "with_incident", label: "Con incidencia" }],
  inspectors: [{ id: "user-1", label: "Ana Lopez" }],
  processTypes: [{ id: "PRODUCTION", label: "Produccion" }],
  processes: [{ id: "Produccion diaria", label: "Produccion diaria" }],
  results: [{ id: "FAILED", label: "Fallida" }],
  riskLevels: [{ id: "HIGH", label: "Alto" }],
  statuses: [{ id: "PENDING", label: "Pendiente" }],
  templates: [{ id: "template-1", label: "Revision sanitaria" }],
};

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

const verification: AdminSanitaryVerificationListItem = {
  areaId: null,
  areaName: "Cocina",
  branchId: "branch-1",
  branchName: "Sucursal Centro",
  checklistTotalCount: 2,
  completedAt: null,
  equipmentId: null,
  equipmentName: "Mesa fria",
  failedCount: 0,
  folio: "SAN-000001",
  hasEvidence: true,
  hasIncident: false,
  id: "verification-1",
  inspectorUserId: "user-1",
  inspectorUserName: "Ana Lopez",
  passedCount: 0,
  processName: "Produccion diaria",
  result: "NOT_EVALUATED",
  riskLevel: "HIGH",
  scheduledAt: "2026-05-21T15:00:00Z",
  status: "PENDING",
  templateName: "Revision sanitaria",
  updatedAt: "2026-05-21T15:10:00Z",
  warningState: "high_risk",
  warnings: [{ code: "high_risk", message: "Verificacion de alto riesgo.", severity: "warning" }],
};

const detail: AdminSanitaryVerificationDetail = {
  availableActions: {
    canAddEvidence: true,
    canCancel: true,
    canComplete: true,
    canCreateIncident: false,
    canEdit: true,
    canExport: false,
    canPrint: false,
    canStart: true,
    note: "Incidencias, adjuntos de archivo y exportacion requieren contratos backend dedicados.",
  },
  checklistResults: [
    {
      displayOrder: 1,
      evidenceRequiredOnFailure: false,
      expectedStandard: "Sin residuos visibles.",
      id: "check-1",
      isRequired: true,
      label: "Superficies limpias",
      notes: null,
      result: "PENDING",
      riskLevel: "HIGH",
    },
    {
      displayOrder: 2,
      evidenceRequiredOnFailure: true,
      expectedStandard: "Sanitizante aplicado.",
      id: "check-2",
      isRequired: true,
      label: "Sanitizante aplicado",
      notes: "Requiere evidencia si falla",
      result: "FAILED",
      riskLevel: "CRITICAL",
    },
  ],
  checklistTemplate: {
    areaType: "PRODUCTION_AREA",
    description: "Revision de produccion",
    failedItems: 1,
    frequency: "DAILY",
    passedItems: 0,
    passThresholdPercent: 80,
    processType: "PRODUCTION",
    riskLevel: "HIGH",
    templateId: "template-1",
    templateName: "Revision sanitaria",
    totalItems: 2,
  },
  evidence: {
    emptyState: "Esta verificacion no tiene evidencia adjunta.",
    evidenceNote: "Foto capturada en cierre",
    files: [],
    hasEvidence: true,
    isSupported: true,
    uploadSupported: false,
  },
  findingsObservations: {
    cancellationReason: null,
    failedRequiredCount: 1,
    findingsNotes: "Sanitizante vencido.",
    followUpDueAt: null,
    followUpRequired: true,
    notes: "Turno matutino",
  },
  overview: {
    ...verification,
    completedAt: "2026-05-21T15:45:00Z",
    createdAt: "2026-05-21T14:50:00Z",
    createdByUserId: "admin-1",
    createdByUserName: "Admin",
    failedCount: 1,
    result: "FAILED",
    startedAt: "2026-05-21T15:10:00Z",
    status: "REQUIRES_FOLLOW_UP",
  },
  relatedCleaningLogs: [
    {
      completedAt: "2026-05-21T14:30:00Z",
      folio: "CLN-000001",
      id: "cleaning-1",
      responsibleUserName: "Ana Lopez",
      routeHint: "/admin/bitacoras-limpieza",
      status: "COMPLETED",
    },
  ],
  relatedDocuments: [],
  scope: {
    areaName: "Cocina",
    areaType: "PRODUCTION_AREA",
    branchCode: "CENTRO",
    branchId: "branch-1",
    branchName: "Sucursal Centro",
    equipmentName: "Mesa fria",
    processName: "Produccion diaria",
    processType: "PRODUCTION",
  },
  scoreResult: {
    maxScore: 2,
    percentage: 50,
    result: "FAILED",
    score: 1,
    thresholdPercent: 80,
  },
  warnings: [{ code: "failed", message: "La verificacion tiene puntos fallidos.", severity: "critical" }],
};

const template: AdminSanitaryTemplate = {
  areaType: "PRODUCTION_AREA",
  description: "Revision de produccion",
  frequency: "DAILY",
  id: "template-1",
  isActive: true,
  items: [
    {
      description: null,
      displayOrder: 1,
      evidenceRequiredOnFailure: false,
      expectedStandard: "Sin residuos visibles.",
      id: "template-item-1",
      isRequired: true,
      label: "Superficies limpias",
      riskLevel: "HIGH",
    },
  ],
  name: "Revision sanitaria",
  passThresholdPercent: 80,
  processType: "PRODUCTION",
  requiresEvidenceOnFailure: true,
  riskLevel: "HIGH",
};

function render(element: ReactElement) {
  return renderToString(element);
}

describe("admin sanitary verification UI components", () => {
  it("renders the page shell with the canonical action", () => {
    const queryClient = new QueryClient();
    const html = render(
      <QueryClientProvider client={queryClient}>
        <AdminSanitaryVerificationsPage />
      </QueryClientProvider>,
    );

    expect(html).toContain("Verificaciones sanitarias");
    expect(html).toContain("Nueva verificacion");
    expect(html).toContain(
      "Selecciona una verificacion para revisar checklist, resultado, evidencia e incidencias relacionadas.",
    );
  });

  it("renders compact search and filter entry point", () => {
    const html = render(
      <AdminSanitaryVerificationsFilters
        filters={filters}
        isBackendConnected={true}
        options={filterOptions}
        onChange={() => undefined}
      />,
    );

    expect(html).toContain("Buscar");
    expect(html).toContain("Folio, area, inspector");
    expect(html).toContain("Filtros");
    expect(html).toContain("API conectada");
  });

  it("renders empty and populated sanitary verification table states", () => {
    const emptyHtml = render(
      <AdminSanitaryVerificationsTable
        page={1}
        pageSize={25}
        total={0}
        verifications={[]}
        onCopyFolio={() => undefined}
        onExecute={() => undefined}
        onPageChange={() => undefined}
        onSelectVerification={() => undefined}
      />,
    );
    expect(emptyHtml).toContain("No hay verificaciones sanitarias para los filtros seleccionados.");

    const tableHtml = render(
      <AdminSanitaryVerificationsTable
        page={1}
        pageSize={25}
        selectedVerificationId={verification.id}
        total={1}
        verifications={[verification]}
        onCopyFolio={() => undefined}
        onExecute={() => undefined}
        onPageChange={() => undefined}
        onSelectVerification={() => undefined}
      />,
    );

    expect(tableHtml).toContain("SAN-000001");
    expect(tableHtml).toContain("Revision sanitaria");
    expect(tableHtml).toContain("Con evidencia");
    expect(tableHtml).toContain("Ejecutar");
  });

  it("renders detail sections, checklist, evidence and related cleaning logs", () => {
    const html = render(
      <AdminSanitaryVerificationDetailPanel
        detail={detail}
        selectedVerification={verification}
        onCopyFolio={() => undefined}
        onExecute={() => undefined}
        onStart={() => undefined}
      />,
    );

    expect(html).toContain("Detalle sanitario");
    expect(html).toContain("Resultados del checklist");
    expect(html).toContain("Sanitizante aplicado");
    expect(html).toContain("Bitacoras de limpieza relacionadas");
    expect(html).toContain("CLN-000001");
    expect(html).toContain("Crear incidencia");
  });

  it("renders create and execute workflow validation surfaces", () => {
    const createHtml = render(
      <AdminSanitaryVerificationWorkflowPanel
        detail={null}
        mode="create"
        options={filterOptions}
        templates={[template]}
        onCancel={() => undefined}
        onComplete={() => undefined}
        onCreate={() => undefined}
      />,
    );
    expect(createHtml).toContain("Nueva verificacion");
    expect(createHtml).toContain("Checklist sanitario");
    expect(createHtml).toContain("Crear y completar inmediatamente");

    const executeHtml = render(
      <AdminSanitaryVerificationWorkflowPanel
        detail={detail}
        mode="execute"
        options={filterOptions}
        templates={[template]}
        onCancel={() => undefined}
        onComplete={() => undefined}
        onCreate={() => undefined}
      />,
    );
    expect(executeHtml).toContain("Ejecutar SAN-000001");
    expect(executeHtml).toContain("No cumple");
    expect(executeHtml).toContain("Completar verificacion");
  });
});
