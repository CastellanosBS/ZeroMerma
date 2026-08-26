import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminAuditEventDetailPanel } from "./components/AdminAuditEventDetailPanel";
import { AdminAuditEventsTable } from "./components/AdminAuditEventsTable";
import { AdminAuditFilters } from "./components/AdminAuditFilters";
import { AdminAuditPage } from "./pages/AdminAuditPage";
import type {
  AdminAuditEventDetail,
  AdminAuditEventListItem,
  AdminAuditFilterOptions,
  AdminAuditListFilters,
} from "./types";

const filterOptions: AdminAuditFilterOptions = {
  actions: [{ id: "admin.user.updated", label: "Admin User Updated" }],
  branches: [{ id: "branch-1", label: "Main Branch" }],
  entityTypes: [{ id: "user", label: "User" }],
  modules: [{ id: "users", label: "Usuarios" }],
  results: [{ id: "success", label: "Success" }],
  sensitivities: [{ id: "yes", label: "Sensibles" }],
  severities: [{ id: "warning", label: "Warning" }],
  sourceApps: [{ id: "BACKOFFICE", label: "Backoffice" }],
  users: [{ id: "user-1", label: "admin@zeromerma.local" }],
  warningStates: [{ id: "sensitive", label: "Sensitive" }],
};

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

const event: AdminAuditEventListItem = {
  action: "admin.user.updated",
  actionLabel: "Admin User Updated",
  actorEmail: "admin@zeromerma.local",
  actorName: "ZeroMerma Admin",
  actorType: "user",
  actorUserId: "user-1",
  branchId: "branch-1",
  branchName: "Main Branch",
  entityId: "user-2",
  entityReference: "cashier@zeromerma.local",
  entityType: "user",
  id: "audit-1",
  isSensitive: true,
  module: "users",
  moduleLabel: "Usuarios",
  occurredAt: "2026-05-22T10:00:00Z",
  result: "success",
  severity: "warning",
  sourceApp: "BACKOFFICE",
  warningState: "sensitive",
  workstationId: null,
  workstationName: "CAJA-01",
};

const detail: AdminAuditEventDetail = {
  actorContext: {
    branchAssignmentsSummary: "Main Branch",
    canOpenUser: true,
    email: "admin@zeromerma.local",
    fullName: "ZeroMerma Admin",
    rolesSummary: "Administrador",
    userId: "user-1",
    userStatus: "active",
  },
  availableActions: {
    canCopyCorrelationId: true,
    canCopyEventId: true,
    canExportEvent: true,
    canOpenRelatedDocument: false,
    canOpenUser: true,
    canSearchRelatedEvents: true,
  },
  changeSummary: [
    {
      changeType: "updated",
      field: "password_hash",
      newValueMasked: "[masked]",
      oldValueMasked: "[masked]",
    },
  ],
  entityContext: {
    branchId: "branch-1",
    branchName: "Main Branch",
    canOpenRelatedDocument: false,
    cashSessionId: null,
    entityId: "user-2",
    entityReference: "cashier@zeromerma.local",
    entityType: "user",
    relatedModule: "users",
    workstationId: null,
    workstationName: "CAJA-01",
  },
  overview: { ...event, requestId: "request-1" },
  relatedDocuments: [
    {
      canOpen: false,
      documentId: "user-2",
      documentType: "user",
      label: "Documento origen: User",
      module: "users",
      reference: "cashier@zeromerma.local",
    },
  ],
  requestContext: {
    correlationId: "correlation-1",
    durationMs: 10,
    endpoint: "/v1/admin/users",
    errorCode: null,
    ipAddress: null,
    method: "PATCH",
    requestId: "request-1",
    statusCode: 200,
    userAgent: null,
  },
  timelineRelatedEvents: [
    {
      action: "admin.user.created",
      actionLabel: "Admin User Created",
      actorName: "ZeroMerma Admin",
      id: "audit-2",
      isSensitive: true,
      occurredAt: "2026-05-22T09:00:00Z",
      result: "success",
    },
  ],
};

function render(element: ReactElement) {
  return renderToString(element);
}

describe("admin audit UI components", () => {
  it("renders the page shell without create action", () => {
    const queryClient = new QueryClient();
    const html = render(
      <QueryClientProvider client={queryClient}>
        <AdminAuditPage />
      </QueryClientProvider>,
    );

    expect(html).toContain("Auditoria");
    expect(html).toContain("Solo lectura");
    expect(html).not.toContain("Nuevo evento");
  });

  it("renders compact filter toolbar", () => {
    const html = render(
      <AdminAuditFilters
        filters={filters}
        isBackendConnected={true}
        options={filterOptions}
        onChange={() => undefined}
      />,
    );

    expect(html).toContain("Evento, folio, entidad...");
    expect(html).toContain("Filtros");
    expect(html).toContain("Eventos desde backend");
    expect(html).not.toContain("Documento");
  });

  it("renders empty and populated audit table states", () => {
    const emptyHtml = render(
      <AdminAuditEventsTable
        events={[]}
        page={1}
        pageSize={25}
        total={0}
        onCopyEventId={() => undefined}
        onPageChange={() => undefined}
        onSelectEvent={() => undefined}
      />,
    );
    expect(emptyHtml).toContain("No hay eventos de auditoria para los filtros seleccionados.");

    const tableHtml = render(
      <AdminAuditEventsTable
        events={[event]}
        page={1}
        pageSize={25}
        total={1}
        onCopyEventId={() => undefined}
        onPageChange={() => undefined}
        onSelectEvent={() => undefined}
      />,
    );
    expect(tableHtml).toContain("ZeroMerma Admin");
    expect(tableHtml).toContain("Usuarios");
    expect(tableHtml).toContain("CAJA-01");
  });

  it("renders detail sections and masked change values", () => {
    const html = render(
      <AdminAuditEventDetailPanel
        detail={detail}
        selectedEvent={event}
        onCopyCorrelationId={() => undefined}
        onCopyEventId={() => undefined}
        onSearchRelated={() => undefined}
      />,
    );

    expect(html).toContain("Actor / usuario");
    expect(html).toContain("Entidad / documento");
    expect(html).toContain("Detalle de cambios");
    expect(html).toContain("[masked]");
    expect(html).toContain("Contexto tecnico");
    expect(html).toContain("Documentos relacionados");
    expect(html).toContain("Eventos cercanos");
  });

  it("renders required empty detail states", () => {
    const html = render(
      <AdminAuditEventDetailPanel
        detail={{ ...detail, changeSummary: [], relatedDocuments: [], requestContext: null, timelineRelatedEvents: [] }}
        selectedEvent={event}
        onCopyCorrelationId={() => undefined}
        onCopyEventId={() => undefined}
        onSearchRelated={() => undefined}
      />,
    );

    expect(html).toContain("Este evento no tiene detalles de cambios disponibles.");
    expect(html).toContain("Este evento no tiene documentos relacionados.");
    expect(html).toContain("Este evento no tiene contexto tecnico de solicitud disponible.");
    expect(html).toContain("No hay eventos relacionados disponibles para este filtro.");
  });
});
