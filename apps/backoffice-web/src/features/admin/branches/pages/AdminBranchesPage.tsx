import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminEntityDrawer } from "../../components/AdminEntityDrawer";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminBranchesBackendContract,
  createAdminBranch,
  fetchAdminBranchDetail,
  fetchAdminBranches,
  updateAdminBranch,
} from "../api";
import { AdminBranchDetailPanel } from "../components/AdminBranchDetailPanel";
import { AdminBranchFormPanel } from "../components/AdminBranchFormPanel";
import { AdminBranchesFilters } from "../components/AdminBranchesFilters";
import { AdminBranchesTable } from "../components/AdminBranchesTable";
import type {
  AdminBranchCreatePayload,
  AdminBranchDetail,
  AdminBranchFilterOptions,
  AdminBranchListFilters,
  AdminBranchListItem,
  AdminBranchListResponse,
  AdminBranchUpdatePayload,
} from "../types";

const initialFilters: AdminBranchListFilters = {
  hasActiveWorkstations: "all",
  page: 1,
  pageSize: 25,
  search: "",
  status: "all",
  warningState: "all",
};

const emptyFilterOptions: AdminBranchFilterOptions = {
  brands: [],
};

const emptyBranchList: AdminBranchListResponse = {
  backendContract: adminBranchesBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    activeBranches: "0",
    inactiveBranches: "0",
    totalBranches: "0",
    withWarnings: "0",
    withWorkstations: "0",
    withoutActiveWorkstation: "0",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

function AdminBranchesMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminBranchListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    { label: "Total", title: "Sucursales totales", value: loadingValue ?? metrics.totalBranches },
    { label: "Activas", title: "Sucursales activas", value: loadingValue ?? metrics.activeBranches },
    { label: "Inactivas", title: "Sucursales inactivas", value: loadingValue ?? metrics.inactiveBranches },
    { label: "Con estaciones", title: "Sucursales con estaciones", value: loadingValue ?? metrics.withWorkstations },
    {
      label: "Sin estacion",
      title: "Sucursales sin estacion activa",
      value: loadingValue ?? metrics.withoutActiveWorkstation,
    },
    { label: "Revisar", title: "Sucursales con advertencias", value: loadingValue ?? metrics.withWarnings },
  ];

  return (
    <section className="flex min-w-0 flex-wrap items-center gap-2 rounded-[18px] border border-[var(--ui-color-border)] bg-white px-3 py-2 text-xs text-slate-600">
      <span className="shrink-0 font-semibold uppercase tracking-[0.12em] text-slate-500">Resumen</span>
      {items.map((item) => (
        <span
          className="inline-flex min-w-0 max-w-full items-center gap-1.5 rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-2.5 py-1"
          key={item.label}
          title={`${item.title}: ${item.value}`}
        >
          <span className="truncate text-slate-500">{item.label}</span>
          <span className="truncate font-semibold text-slate-950">{item.value}</span>
        </span>
      ))}
    </section>
  );
}

function toUpdatePayload(payload: AdminBranchCreatePayload | AdminBranchUpdatePayload): AdminBranchUpdatePayload {
  return {
    addressLine: payload.addressLine ?? null,
    brandId: payload.brandId ?? null,
    city: payload.city ?? null,
    code: payload.code ?? null,
    contactEmail: payload.contactEmail ?? null,
    country: payload.country ?? null,
    isActive: payload.isActive ?? null,
    name: payload.name ?? null,
    notes: payload.notes ?? null,
    phone: payload.phone ?? null,
    postalCode: payload.postalCode ?? null,
    state: payload.state ?? null,
    timezone: payload.timezone ?? null,
  };
}

function getBranchId(branch: AdminBranchDetail | AdminBranchListItem): string {
  return "overview" in branch ? branch.overview.id : branch.id;
}

function getBranchStatus(branch: AdminBranchDetail | AdminBranchListItem): "active" | "inactive" {
  return "overview" in branch ? branch.overview.status : branch.status;
}

function getBranchName(branch: AdminBranchDetail | AdminBranchListItem): string {
  return "overview" in branch ? branch.overview.name : branch.name;
}

function getBranchWarnings(branch: AdminBranchDetail | AdminBranchListItem) {
  return "overview" in branch ? branch.warnings : branch.warnings;
}

function getInitialSelectedBranchId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return new URLSearchParams(window.location.search).get("branchId");
}

export function AdminBranchesPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminBranchListFilters>(initialFilters);
  const [formMode, setFormMode] = useState<"create" | { type: "edit"; detail: AdminBranchDetail } | null>(null);
  const [pendingEditBranchId, setPendingEditBranchId] = useState<string | null>(null);
  const [selectedBranchId, setSelectedBranchId] = useState<string | null>(getInitialSelectedBranchId);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(null);

  const branchesQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminBranches(accessToken ?? "", filters),
    queryKey: ["admin", "branches", "list", filters],
    retry: false,
  });

  const branchList = branchesQuery.data ?? emptyBranchList;
  const selectedBranchPreview = useMemo(
    () => branchList.items.find((item) => item.id === selectedBranchId) ?? null,
    [branchList.items, selectedBranchId],
  );

  const branchDetailQuery = useQuery({
    enabled: Boolean(accessToken && selectedBranchId),
    queryFn: () => fetchAdminBranchDetail(accessToken ?? "", selectedBranchId ?? ""),
    queryKey: ["admin", "branches", "detail", selectedBranchId],
    retry: false,
  });

  const createBranchMutation = useMutation({
    mutationFn: (payload: AdminBranchCreatePayload) => createAdminBranch(accessToken ?? "", payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo crear la sucursal."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Sucursal creada correctamente." });
      setFormMode(null);
      setSelectedBranchId(detail.overview.id);
      void queryClient.invalidateQueries({ queryKey: ["admin", "branches"] });
    },
  });

  const updateBranchMutation = useMutation({
    mutationFn: ({ branchId, payload }: { branchId: string; payload: AdminBranchUpdatePayload }) =>
      updateAdminBranch(accessToken ?? "", branchId, payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo actualizar la sucursal."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Sucursal actualizada correctamente." });
      setFormMode(null);
      setPendingEditBranchId(null);
      setSelectedBranchId(detail.overview.id);
      void queryClient.invalidateQueries({ queryKey: ["admin", "branches"] });
    },
  });

  useEffect(() => {
    if (pendingEditBranchId && branchDetailQuery.data?.overview.id === pendingEditBranchId) {
      setFormMode({ type: "edit", detail: branchDetailQuery.data });
      setPendingEditBranchId(null);
    }
  }, [branchDetailQuery.data, pendingEditBranchId]);

  const detailBranch = branchDetailQuery.data ?? null;
  const listErrorMessage = branchesQuery.isError
    ? toBackofficeErrorMessage(branchesQuery.error, "No se pudieron cargar las sucursales. Intenta nuevamente.")
    : null;
  const detailErrorMessage = branchDetailQuery.isError
    ? toBackofficeErrorMessage(branchDetailQuery.error, "No se pudo cargar el detalle de la sucursal.")
    : null;
  const formErrorMessage =
    createBranchMutation.isError || updateBranchMutation.isError
      ? toBackofficeErrorMessage(createBranchMutation.error ?? updateBranchMutation.error, "No se pudo guardar.")
      : null;
  const pageStatusLabel = branchesQuery.isLoading
    ? "Validando API"
    : branchList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";
  const isSaving = createBranchMutation.isPending || updateBranchMutation.isPending;

  function patchFilters(patch: Partial<AdminBranchListFilters>) {
    setFilters((current) => ({
      ...current,
      ...patch,
      page: patch.page ?? 1,
    }));
    setSelectedBranchId(null);
  }

  function handleSelectBranch(item: AdminBranchListItem) {
    setSelectedBranchId(item.id);
  }

  function handlePageChange(page: number) {
    setFilters((current) => ({ ...current, page }));
  }

  function handleEditBranch(branch: AdminBranchDetail | AdminBranchListItem) {
    const branchId = getBranchId(branch);
    setFeedback(null);
    setSelectedBranchId(branchId);
    if ("overview" in branch) {
      setFormMode({ type: "edit", detail: branch });
      return;
    }
    if (detailBranch?.overview.id === branchId) {
      setFormMode({ type: "edit", detail: detailBranch });
      return;
    }
    setPendingEditBranchId(branchId);
  }

  function handleSubmitBranch(payload: AdminBranchCreatePayload | AdminBranchUpdatePayload) {
    if (!accessToken || isSaving) {
      return;
    }

    setFeedback(null);
    if (formMode && formMode !== "create") {
      updateBranchMutation.mutate({
        branchId: formMode.detail.overview.id,
        payload: toUpdatePayload(payload),
      });
      return;
    }

    createBranchMutation.mutate(payload as AdminBranchCreatePayload);
  }

  function handleToggleStatus(branch: AdminBranchDetail | AdminBranchListItem) {
    if (!accessToken || updateBranchMutation.isPending) {
      return;
    }

    const branchId = getBranchId(branch);
    const currentStatus = getBranchStatus(branch);
    const nextStatus = currentStatus === "active" ? "inactive" : "active";
    const warnings = getBranchWarnings(branch);
    const warningText =
      currentStatus === "active" && warnings.length > 0
        ? `\n\nAdvertencias actuales: ${warnings.map((warning) => warning.message).join(" ")}`
        : "";

    if (
      !window.confirm(
        `${nextStatus === "active" ? "Activar" : "Desactivar"} ${getBranchName(branch)}?${warningText}`,
      )
    ) {
      return;
    }

    setFeedback(null);
    updateBranchMutation.mutate({
      branchId,
      payload: { isActive: nextStatus === "active" },
    });
  }

  function handleCopyCode(item: AdminBranchListItem) {
    void navigator.clipboard?.writeText(item.code);
    setFeedback({ tone: "success", message: `Codigo copiado: ${item.code}` });
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionLabel="Nueva sucursal"
        description="Administra las sucursales, su estado operativo, marca, estaciones asociadas y preparacion multisucursal."
        meta={[pageStatusLabel]}
        onAction={() => {
          setFeedback(null);
          setFormMode("create");
        }}
        title="Sucursales"
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminBranchesFilters
          filters={filters}
          isBackendConnected={branchList.isBackendConnected}
          options={branchList.filterOptions}
          onChange={patchFilters}
        />

        <AdminBranchesMetricStrip metrics={branchList.metrics} isLoading={branchesQuery.isLoading} />

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

        {pendingEditBranchId && branchDetailQuery.isLoading ? (
          <p className="rounded-[18px] border border-[var(--ui-color-border)] bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-600">
            Cargando detalle para editar.
          </p>
        ) : null}

        <AdminEntityDrawer
          description="Edita datos seguros de sucursal sin desplazar la tabla."
          isOpen={Boolean(formMode)}
          title={formMode === "create" ? "Nueva sucursal" : "Editar sucursal"}
          onClose={() => {
            setFormMode(null);
            setPendingEditBranchId(null);
          }}
        >
          {formMode ? (
          <AdminBranchFormPanel
            branchDetail={formMode === "create" ? null : formMode.detail}
            brandOptions={branchList.filterOptions.brands}
            errorMessage={formErrorMessage}
            isSubmitting={isSaving}
            key={formMode === "create" ? "create" : formMode.detail.overview.id}
            onClose={() => {
              setFormMode(null);
              setPendingEditBranchId(null);
            }}
            onSubmit={handleSubmitBranch}
          />
          ) : null}
        </AdminEntityDrawer>

        <div className="grid min-h-0 min-w-0 flex-1 items-stretch gap-2.5 overflow-hidden xl:grid-cols-[minmax(0,1fr)_minmax(15rem,19rem)]">
          <AdminBranchesTable
            backendContract={branchList.backendContract}
            branches={branchList.items}
            errorMessage={listErrorMessage}
            isLoading={branchesQuery.isLoading}
            isUpdating={updateBranchMutation.isPending}
            page={branchList.page}
            pageSize={branchList.pageSize}
            selectedBranchId={selectedBranchId}
            total={branchList.total}
            onCopyCode={handleCopyCode}
            onEditBranch={handleEditBranch}
            onPageChange={handlePageChange}
            onSelectBranch={handleSelectBranch}
            onToggleStatus={handleToggleStatus}
          />
          <AdminBranchDetailPanel
            branchDetail={detailBranch}
            branchPreview={selectedBranchPreview}
            errorMessage={detailErrorMessage}
            isLoading={branchDetailQuery.isLoading}
            onEdit={handleEditBranch}
            onToggleStatus={handleToggleStatus}
          />
        </div>
      </div>
    </section>
  );
}
