import { withCapabilities } from "../../../test-support/authorization";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminIncidentDetailPanel } from "./components/AdminIncidentDetailPanel";
import { AdminIncidentsFilters } from "./components/AdminIncidentsFilters";
import { AdminIncidentsTable } from "./components/AdminIncidentsTable";
import { AdminIncidentWorkflowPanel } from "./components/AdminIncidentWorkflowPanel";
import { AdminIncidentsPage } from "./pages/AdminIncidentsPage";
import type {
  AdminIncidentDetail,
  AdminIncidentFilterOptions,
  AdminIncidentListFilters,
  AdminIncidentListItem,
} from "./types";

const filterOptions: AdminIncidentFilterOptions = {
  areas: [{ id: "Cocina", label: "Cocina" }],
  branches: [{ id: "branch-1", label: "Sucursal Centro" }],
  dueStates: [{ id: "overdue", label: "Vencidas" }],
  evidenceStates: [{ id: "without_evidence", label: "Sin evidencia" }],
  incidentTypes: [{ id: "SANITATION_ISSUE", label: "Sanitaria" }],
  relatedDocumentStates: [{ id: "with_related", label: "Con documentos" }],
  reportedByUsers: [{ id: "user-1", label: "Ana Lopez" }],
  responsibleUsers: [{ id: "user-2", label: "Luis Perez" }],
  severities: [{ id: "HIGH", label: "Alta" }],
  sourceTypes: [{ id: "SANITARY_VERIFICATION", label: "Verificacion sanitaria" }],
  statuses: [{ id: "OPEN", label: "Abierta" }],
};

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

const incident: AdminIncidentListItem = {
  areaName: "Cocina",
  branchId: "branch-1",
  branchName: "Sucursal Centro",
  createdAt: "2026-05-21T15:00:00Z",
  dueAt: "2026-05-22T18:00:00Z",
  folio: "INC-000001",
  hasEvidence: true,
  id: "incident-1",
  incidentType: "SANITATION_ISSUE",
  relatedDocumentCount: 1,
  reportedByUserId: "user-1",
  reportedByUserName: "Ana Lopez",
  responsibleUserId: "user-2",
  responsibleUserName: "Luis Perez",
  severity: "HIGH",
  sourceReference: "SAN-000001",
  sourceType: "SANITARY_VERIFICATION",
  status: "OPEN",
  title: "Sanitizante vencido",
  updatedAt: "2026-05-21T15:10:00Z",
  warningState: "high_risk",
  warnings: [{ code: "high_risk", message: "Incidencia de alto riesgo.", severity: "warning" }],
};

const detail: AdminIncidentDetail = {
  availableActions: {
    canAddEvidence: true,
    canAddFollowUp: true,
    canAssign: true,
    canCancel: true,
    canCreateCorrectiveAction: true,
    canCreateMaintenance: false,
    canExport: false,
    canMarkInProgress: true,
    canPrint: false,
    canReopen: false,
    canResolve: true,
    note: "Adjuntos de archivo aun no estan soportados.",
  },
  correctiveAction: {
    correctiveAction: "Cambiar sanitizante y repetir limpieza.",
    currentProgress: "OPEN",
    dueAt: "2026-05-22T18:00:00Z",
    responsibleUserId: "user-2",
    responsibleUserName: "Luis Perez",
    resolutionNote: null,
    resolutionResult: null,
    resolvedAt: null,
  },
  descriptionClassification: {
    description: "Se encontro sanitizante vencido en cocina.",
    foodSafetyImpact: true,
    incidentType: "SANITATION_ISSUE",
    notes: "Requiere seguimiento",
    operationalImpact: "Area detenida temporalmente",
    riskLevel: "HIGH",
    severity: "HIGH",
  },
  evidence: {
    emptyState: "Esta incidencia no tiene evidencia adjunta.",
    evidenceNote: "Foto de etiqueta vencida",
    files: [],
    hasEvidence: true,
    isSupported: true,
    uploadSupported: false,
  },
  followUps: [
    {
      createdAt: "2026-05-21T16:00:00Z",
      createdByUserId: "user-1",
      createdByUserName: "Ana Lopez",
      id: "follow-up-1",
      note: "Se retiro el insumo vencido.",
      statusChange: "IN_PROGRESS",
    },
  ],
  locationScope: {
    areaName: "Cocina",
    branchCode: "CENTRO",
    branchId: "branch-1",
    branchName: "Sucursal Centro",
    equipmentName: "Mesa fria",
    processName: "Limpieza de cierre",
    productReference: null,
    productionReference: null,
  },
  overview: {
    ...incident,
    resolvedAt: null,
  },
  relatedDocuments: [
    {
      documentId: "sanitary-1",
      documentType: "sanitary_verification",
      folio: "SAN-000001",
      routeHint: "/admin/verificaciones-sanitarias",
      status: "REQUIRES_FOLLOW_UP",
    },
  ],
  sourceDocument: {
    emptyState: "Esta incidencia fue registrada manualmente y no tiene documento origen.",
    routeHint: "/admin/verificaciones-sanitarias",
    sourceDocumentId: "sanitary-1",
    sourceReference: "SAN-000001",
    sourceSummary: "Verificacion fallida",
    sourceType: "SANITARY_VERIFICATION",
  },
  timeline: [
    {
      label: "Creada",
      note: "Incidencia creada.",
      occurredAt: "2026-05-21T15:00:00Z",
      userName: "Ana Lopez",
    },
  ],
  warnings: [{ code: "high_risk", message: "Incidencia de alto riesgo.", severity: "warning" }],
};

function render(element: ReactElement) {
  return renderToString(withCapabilities(element, ["quality_hygiene.manage"]));
}

describe("admin incidents UI components", () => {
  it("renders the page shell with the canonical action", () => {
    const queryClient = new QueryClient();
    const html = render(
      <QueryClientProvider client={queryClient}>
        <AdminIncidentsPage />
      </QueryClientProvider>,
    );

    expect(html).toContain("Incidencias");
    expect(html).toContain("Nueva incidencia");
    expect(html).toContain(
      "Selecciona una incidencia para revisar origen, severidad, seguimiento y documentos relacionados.",
    );
  });

  it("renders compact search and filter entry point", () => {
    const html = render(
      <AdminIncidentsFilters
        filters={filters}
        isBackendConnected={true}
        options={filterOptions}
        onChange={() => undefined}
      />,
    );

    expect(html).toContain("Buscar");
    expect(html).toContain("Folio, titulo, descripcion");
    expect(html).toContain("Filtros");
    expect(html).toContain("API conectada");
  });

  it("renders empty and populated incident table states", () => {
    const emptyHtml = render(
      <AdminIncidentsTable
        incidents={[]}
        page={1}
        pageSize={25}
        total={0}
        onAddFollowUp={() => undefined}
        onCopyFolio={() => undefined}
        onPageChange={() => undefined}
        onResolve={() => undefined}
        onSelectIncident={() => undefined}
      />,
    );
    expect(emptyHtml).toContain("No hay incidencias para los filtros seleccionados.");

    const tableHtml = render(
      <AdminIncidentsTable
        incidents={[incident]}
        page={1}
        pageSize={25}
        selectedIncidentId={incident.id}
        total={1}
        onAddFollowUp={() => undefined}
        onCopyFolio={() => undefined}
        onPageChange={() => undefined}
        onResolve={() => undefined}
        onSelectIncident={() => undefined}
      />,
    );

    expect(tableHtml).toContain("INC-000001");
    expect(tableHtml).toContain("Sanitaria");
    expect(tableHtml).toContain("Con evidencia");
    expect(tableHtml).toContain("Resolver");
  });

  it("renders detail sections, source document, evidence and follow-up", () => {
    const html = render(
      <AdminIncidentDetailPanel
        detail={detail}
        selectedIncident={incident}
        onAddFollowUp={() => undefined}
        onCopyFolio={() => undefined}
        onMarkInProgress={() => undefined}
        onReopen={() => undefined}
        onResolve={() => undefined}
      />,
    );

    expect(html).toContain("Detalle de incidencia");
    expect(html).toContain("Documento origen");
    expect(html).toContain("SAN-000001");
    expect(html).toContain("Accion correctiva / seguimiento");
    expect(html).toContain("Se retiro el insumo vencido.");
    expect(html).toContain("Documentos relacionados");
  });

  it("renders create, follow-up and resolve workflow surfaces", () => {
    const baseProps = {
      errorMessage: null,
      incident,
      options: filterOptions,
      onAddFollowUp: () => undefined,
      onCancel: () => undefined,
      onCreate: () => undefined,
      onResolve: () => undefined,
    };

    const createHtml = render(<AdminIncidentWorkflowPanel {...baseProps} mode="create" />);
    expect(createHtml).toContain("Nueva incidencia");
    expect(createHtml).toContain("Documento origen");
    expect(createHtml).toContain("Guardar incidencia");

    const followUpHtml = render(<AdminIncidentWorkflowPanel {...baseProps} mode="followUp" />);
    expect(followUpHtml).toContain("Seguimiento INC-000001");
    expect(followUpHtml).toContain("Nota de seguimiento");
    expect(followUpHtml).toContain("Guardar seguimiento");

    const resolveHtml = render(<AdminIncidentWorkflowPanel {...baseProps} mode="resolve" />);
    expect(resolveHtml).toContain("Resolver INC-000001");
    expect(resolveHtml).toContain("Nota de resolucion");
    expect(resolveHtml).toContain("Resolver incidencia");
  });
});
