import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminSettingBackendContract,
  fetchAdminSettingDetail,
  fetchAdminSettings,
  resetAdminSetting,
  updateAdminSetting,
} from "../api";
import { AdminSettingDetailPanel } from "../components/AdminSettingDetailPanel";
import { AdminSettingsFilters } from "../components/AdminSettingsFilters";
import { AdminSettingsList } from "../components/AdminSettingsList";
import type {
  AdminSettingDefinition,
  AdminSettingFilterOptions,
  AdminSettingListItem,
  AdminSettingsFilters as AdminSettingsFilterState,
  AdminSettingsListResponse,
} from "../types";

const initialFilters: AdminSettingsFilterState = {
  affectedModule: "all",
  category: "all",
  readonly: "all",
  scope: "all",
  search: "",
  sensitivity: "all",
  status: "all",
};

const emptyFilterOptions: AdminSettingFilterOptions = {
  categories: [],
  modules: [],
  readonlyStates: [],
  scopes: [],
  sensitivities: [],
  statuses: [],
};

const emptySettingsList: AdminSettingsListResponse = {
  backendContract: adminSettingBackendContract,
  categories: [],
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    activeSettings: "0",
    incompleteRequired: "0",
    integrationSettings: "0",
    recentChanges: null,
    scopedOverrides: "0",
    sensitiveSettings: "0",
    warningSettings: "0",
  },
  total: 0,
};

function stringValue(value: unknown): string {
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (value === null || value === undefined) {
    return "";
  }
  return String(value);
}

function editorInitialValue(item: AdminSettingListItem | null): string {
  if (!item) {
    return "";
  }
  if (item.definition.isSensitive) {
    return "";
  }
  return stringValue(item.value.effectiveValue);
}

function buildUpdateValue(definition: AdminSettingDefinition, editorValue: string): unknown {
  if (definition.type === "boolean") {
    return editorValue === "true";
  }
  if (definition.type === "number" || definition.type === "duration") {
    return Number(editorValue);
  }
  if (definition.type === "money" || definition.type === "percentage") {
    return editorValue;
  }
  return editorValue;
}

function SettingsMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminSettingsListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    { label: "Configuraciones activas", value: loadingValue ?? metrics.activeSettings },
    { label: "Con advertencias", value: loadingValue ?? metrics.warningSettings },
    { label: "Pendientes de completar", value: loadingValue ?? metrics.incompleteRequired },
    {
      label: "Cambios recientes",
      value: loadingValue ?? metrics.recentChanges ?? "No disponible",
    },
    { label: "Sensibles", value: loadingValue ?? metrics.sensitiveSettings },
    { label: "Por sucursal", value: loadingValue ?? metrics.scopedOverrides },
    { label: "Integraciones", value: loadingValue ?? metrics.integrationSettings },
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

export function AdminSettingsPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminSettingsFilterState>(initialFilters);
  const [selectedSettingKey, setSelectedSettingKey] = useState<string | null>(null);
  const [editorValue, setEditorValue] = useState("");
  const [changeNote, setChangeNote] = useState("");
  const [confirmSensitive, setConfirmSensitive] = useState(false);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const settingsQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminSettings(accessToken ?? "", filters),
    queryKey: ["admin", "settings", "list", filters],
    retry: false,
  });

  const settingsList = settingsQuery.data ?? emptySettingsList;
  const selectedSetting = useMemo(
    () => settingsList.items.find((item) => item.definition.key === selectedSettingKey) ?? null,
    [selectedSettingKey, settingsList.items],
  );

  const detailQuery = useQuery({
    enabled: Boolean(accessToken && selectedSettingKey),
    queryFn: () => fetchAdminSettingDetail(accessToken ?? "", selectedSettingKey ?? ""),
    queryKey: ["admin", "settings", "detail", selectedSettingKey],
    retry: false,
  });

  useEffect(() => {
    if (selectedSetting) {
      setEditorValue(editorInitialValue(selectedSetting));
      setChangeNote("");
      setConfirmSensitive(false);
    }
  }, [selectedSetting]);

  const updateMutation = useMutation({
    mutationFn: () => {
      if (!detailQuery.data) {
        throw new Error("Selecciona una configuracion primero.");
      }
      return updateAdminSetting(accessToken ?? "", detailQuery.data.definition.key, {
        changeNote: changeNote || null,
        confirmSensitive,
        value: buildUpdateValue(detailQuery.data.definition, editorValue),
      });
    },
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo actualizar la configuracion."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({
        tone: "success",
        message: `Configuracion ${detail.definition.key} actualizada.`,
      });
      setSelectedSettingKey(detail.definition.key);
      await queryClient.invalidateQueries({ queryKey: ["admin", "settings"] });
    },
  });

  const resetMutation = useMutation({
    mutationFn: () => {
      if (!detailQuery.data) {
        throw new Error("Selecciona una configuracion primero.");
      }
      return resetAdminSetting(accessToken ?? "", detailQuery.data.definition.key, {
        changeNote: changeNote || null,
        confirmSensitive,
      });
    },
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo restablecer la configuracion."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({
        tone: "success",
        message: `Configuracion ${detail.definition.key} restablecida.`,
      });
      await queryClient.invalidateQueries({ queryKey: ["admin", "settings"] });
    },
  });

  const listErrorMessage = settingsQuery.isError
    ? toBackofficeErrorMessage(settingsQuery.error, "No se pudieron cargar configuraciones.")
    : null;
  const detailErrorMessage = detailQuery.isError
    ? toBackofficeErrorMessage(detailQuery.error, "No se pudo cargar la configuracion.")
    : null;
  const pageStatusLabel = settingsQuery.isLoading
    ? "Validando API"
    : settingsList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminSettingsFilterState>) {
    setFilters((current) => ({ ...current, ...patch }));
  }

  function selectSetting(item: AdminSettingListItem) {
    setSelectedSettingKey(item.definition.key);
    setFeedback(null);
  }

  async function copyKey(key: string) {
    await navigator.clipboard.writeText(key);
    setFeedback({ tone: "success", message: `Clave ${key} copiada.` });
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        description="Define reglas globales, comportamiento operativo, parametros del POS, caja, inventario, pedidos, comprobantes y notificaciones."
        meta={[pageStatusLabel, "Cambios auditables", "Alcance global"]}
        title="Configuración"
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminSettingsFilters
          filters={filters}
          isBackendConnected={settingsList.isBackendConnected}
          options={settingsList.filterOptions}
          onChange={patchFilters}
        />

        <SettingsMetricStrip isLoading={settingsQuery.isLoading} metrics={settingsList.metrics} />

        <div className="flex min-w-0 flex-wrap gap-2">
          <button
            className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
            type="button"
            onClick={() => settingsQuery.refetch()}
          >
            Actualizar
          </button>
          <a
            className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
            href="/admin/auditoria"
          >
            Ver cambios recientes
          </a>
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

        <div className="grid min-h-0 min-w-0 flex-1 gap-2.5 xl:grid-cols-[minmax(22rem,0.45fr)_minmax(0,1fr)]">
          <AdminSettingsList
            categories={settingsList.categories}
            errorMessage={listErrorMessage}
            isLoading={settingsQuery.isLoading}
            items={settingsList.items}
            selectedCategory={filters.category}
            selectedSettingKey={selectedSettingKey}
            total={settingsList.total}
            onSelectCategory={(category) => patchFilters({ category })}
            onSelectSetting={selectSetting}
          />

          <AdminSettingDetailPanel
            changeNote={changeNote}
            confirmSensitive={confirmSensitive}
            detail={detailQuery.data ?? null}
            editorValue={editorValue}
            errorMessage={detailErrorMessage}
            isLoading={detailQuery.isLoading}
            resetPending={resetMutation.isPending}
            savePending={updateMutation.isPending}
            selectedSetting={selectedSetting}
            onChangeEditorValue={setEditorValue}
            onCopyKey={copyKey}
            onReset={() => resetMutation.mutate()}
            onSave={() => updateMutation.mutate()}
            onSetChangeNote={setChangeNote}
            onSetConfirmSensitive={setConfirmSensitive}
          />
        </div>
      </div>
    </section>
  );
}
