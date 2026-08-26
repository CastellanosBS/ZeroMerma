import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminAuditBackendContract,
  exportAdminAuditEvents,
  fetchAdminAuditEventDetail,
  fetchAdminAuditEvents,
} from "../api";
import { AdminAuditEventDetailPanel } from "../components/AdminAuditEventDetailPanel";
import { AdminAuditEventsTable } from "../components/AdminAuditEventsTable";
import { AdminAuditFilters } from "../components/AdminAuditFilters";
import type {
  AdminAuditFilterOptions,
  AdminAuditListFilters,
  AdminAuditListResponse,
} from "../types";

const initialFilters: AdminAuditListFilters = {
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

const emptyFilterOptions: AdminAuditFilterOptions = {
  actions: [],
  branches: [],
  entityTypes: [],
  modules: [],
  results: [],
  sensitivities: [],
  severities: [],
  sourceApps: [],
  users: [],
  warningStates: [],
};

const emptyAuditList: AdminAuditListResponse = {
  backendContract: adminAuditBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    accessEvents: "0",
    activeActors: "0",
    failedEvents: "0",
    financialEvents: "0",
    inventoryEvents: "0",
    sensitiveEvents: "0",
    systemEvents: "0",
    totalEvents: "0",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

function AuditMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminAuditListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    { label: "Eventos del periodo", value: loadingValue ?? metrics.totalEvents },
    { label: "Acciones sensibles", value: loadingValue ?? metrics.sensitiveEvents },
    { label: "Cambios financieros", value: loadingValue ?? metrics.financialEvents },
    { label: "Cambios de inventario", value: loadingValue ?? metrics.inventoryEvents },
    { label: "Cambios de acceso", value: loadingValue ?? metrics.accessEvents },
    { label: "Fallidos / bloqueados", value: loadingValue ?? metrics.failedEvents },
    { label: "Sistema", value: loadingValue ?? metrics.systemEvents },
    { label: "Usuarios activos", value: loadingValue ?? metrics.activeActors },
  ];

  return (
    <section className="flex min-w-0 flex-wrap items-center gap-2 rounded-[18px] border border-[var(--ui-color-border)] bg-white px-3 py-2 text-xs text-slate-600">
      <span className="shrink-0 font-semibold uppercase tracking-[0.12em] text-slate-500">
        Resumen
      </span>
      {items.map((item) => (
        <span
          className="inline-flex min-w-0 max-w-full items-center gap-1.5 rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-2.5 py-1"
          key={item.label}
          title={`${item.label}: ${item.value}`}
        >
          <span className="truncate text-slate-500">{item.label}</span>
          <span className="truncate font-semibold text-slate-950">{item.value}</span>
        </span>
      ))}
    </section>
  );
}

function downloadJson(filename: string, value: unknown) {
  const blob = new Blob([JSON.stringify(value, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function AdminAuditPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const [filters, setFilters] = useState<AdminAuditListFilters>(initialFilters);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const auditQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminAuditEvents(accessToken ?? "", filters),
    queryKey: ["admin", "audit", "list", filters],
    retry: false,
  });

  const auditList = auditQuery.data ?? emptyAuditList;
  const selectedEvent = useMemo(
    () => auditList.items.find((item) => item.id === selectedEventId) ?? null,
    [auditList.items, selectedEventId],
  );

  const detailQuery = useQuery({
    enabled: Boolean(accessToken && selectedEventId),
    queryFn: () => fetchAdminAuditEventDetail(accessToken ?? "", selectedEventId ?? ""),
    queryKey: ["admin", "audit", "detail", selectedEventId],
    retry: false,
  });

  const exportMutation = useMutation({
    mutationFn: () => exportAdminAuditEvents(accessToken ?? "", filters),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo exportar auditoria."),
      });
    },
    onSuccess: (payload) => {
      downloadJson(`auditoria-${new Date().toISOString().slice(0, 10)}.json`, payload);
      setFeedback({ tone: "success", message: `${payload.total} eventos preparados para exportar.` });
    },
  });

  const listErrorMessage = auditQuery.isError
    ? toBackofficeErrorMessage(auditQuery.error, "No se pudieron cargar los eventos de auditoria.")
    : null;
  const detailErrorMessage = detailQuery.isError
    ? toBackofficeErrorMessage(detailQuery.error, "No se pudo cargar el detalle de auditoria.")
    : null;
  const pageStatusLabel = auditQuery.isLoading
    ? "Validando API"
    : auditList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminAuditListFilters>) {
    setFilters((current) => ({ ...current, ...patch, page: patch.page ?? 1 }));
    setSelectedEventId(null);
  }

  function copyText(value: string, label: string) {
    void navigator.clipboard?.writeText(value);
    setFeedback({ tone: "success", message: `${label} copiado.` });
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        description="Consulta acciones sensibles, cambios de datos, eventos de seguridad y trazabilidad operativa del sistema."
        meta={[pageStatusLabel, "Solo lectura"]}
        title="Auditoria"
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminAuditFilters
          filters={filters}
          isBackendConnected={auditList.isBackendConnected}
          options={auditList.filterOptions}
          onChange={patchFilters}
        />

        <AuditMetricStrip isLoading={auditQuery.isLoading} metrics={auditList.metrics} />

        <div className="flex min-w-0 flex-wrap gap-2">
          <button
            className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
            type="button"
            onClick={() => auditQuery.refetch()}
          >
            Actualizar
          </button>
          <button
            className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] disabled:cursor-not-allowed disabled:opacity-40"
            disabled={!auditList.backendContract.exportSupported || exportMutation.isPending}
            type="button"
            onClick={() => exportMutation.mutate()}
          >
            Exportar
          </button>
        </div>

        {feedback ? (
          <p
            className={`rounded-[18px] border px-4 py-3 text-sm font-semibold ${
              feedback.tone === "success"
                ? "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]"
                : "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]"
            }`}
          >
            {feedback.message}
          </p>
        ) : null}

        <div className="grid min-h-0 min-w-0 flex-1 gap-2.5 xl:grid-cols-[minmax(0,1fr)_minmax(24rem,0.44fr)]">
          <AdminAuditEventsTable
            errorMessage={listErrorMessage}
            events={auditList.items}
            isLoading={auditQuery.isLoading}
            page={filters.page}
            pageSize={filters.pageSize}
            selectedEventId={selectedEventId}
            total={auditList.total}
            onCopyEventId={(item) => copyText(item.id, "Evento")}
            onPageChange={(page) => setFilters((current) => ({ ...current, page }))}
            onSelectEvent={(item) => setSelectedEventId(item.id)}
          />

          <AdminAuditEventDetailPanel
            detail={detailQuery.data ?? null}
            errorMessage={detailErrorMessage}
            isLoading={detailQuery.isLoading}
            selectedEvent={selectedEvent}
            onCopyCorrelationId={(value) => copyText(value, "Correlacion")}
            onCopyEventId={(value) => copyText(value, "Evento")}
            onSearchRelated={(item) =>
              patchFilters({
                entityId: item.entityId ?? "",
                entityType: item.entityType,
                relatedReference: item.entityReference ?? "",
              })
            }
          />
        </div>
      </div>
    </section>
  );
}
