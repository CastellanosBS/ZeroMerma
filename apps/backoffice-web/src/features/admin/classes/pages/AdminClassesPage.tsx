import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminProductClassesBackendContract,
  createAdminProductClass,
  fetchAdminProductClassDetail,
  fetchAdminProductClasses,
  updateAdminProductClass,
} from "../api";
import { AdminClassFormPanel } from "../components/AdminClassFormPanel";
import { AdminClassesDetailPanel } from "../components/AdminClassesDetailPanel";
import { AdminClassesFilters } from "../components/AdminClassesFilters";
import { AdminClassesTable } from "../components/AdminClassesTable";
import type {
  AdminProductClass,
  AdminProductClassCreatePayload,
  AdminProductClassFilterOptions,
  AdminProductClassListFilters,
  AdminProductClassListResponse,
  AdminProductClassUpdatePayload,
} from "../types";

const initialFilters: AdminProductClassListFilters = {
  page: 1,
  pageSize: 25,
  captureMode: "all",
  productPresence: "all",
  search: "",
  status: "all",
};

const emptyFilterOptions: AdminProductClassFilterOptions = {
  brands: [],
};

const emptyClassList: AdminProductClassListResponse = {
  backendContract: adminProductClassesBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    activeClasses: "0",
    classCapture: "0",
    productDirect: "0",
    totalClasses: "0",
    withWarnings: "0",
    withoutProducts: "0",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

function AdminClassesMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminProductClassListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    { label: "Total", title: "Total de clases", value: loadingValue ?? metrics.totalClasses },
    { label: "Activas", title: "Clases activas", value: loadingValue ?? metrics.activeClasses },
    { label: "Por clase", title: "CLASS_CAPTURE", value: loadingValue ?? metrics.classCapture },
    { label: "Directas", title: "PRODUCT_DIRECT", value: loadingValue ?? metrics.productDirect },
    {
      label: "Sin productos",
      title: "Clases sin productos",
      value: loadingValue ?? metrics.withoutProducts,
    },
    {
      label: "Revisar",
      title: "Clases con advertencias",
      value: loadingValue ?? metrics.withWarnings,
    },
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
          title={`${item.title}: ${item.value}`}
        >
          <span className="truncate text-slate-500">{item.label}</span>
          <span className="truncate font-semibold text-slate-950">{item.value}</span>
        </span>
      ))}
    </section>
  );
}

export function AdminClassesPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminProductClassListFilters>(initialFilters);
  const [formMode, setFormMode] = useState<
    { type: "create" } | { type: "edit"; item: AdminProductClass } | null
  >(null);
  const [selectedClassId, setSelectedClassId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const classesQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminProductClasses(accessToken ?? "", filters),
    queryKey: ["admin", "product-classes", "list", filters],
    retry: false,
  });

  const classList = classesQuery.data ?? emptyClassList;
  const selectedClassPreview = useMemo(
    () => classList.items.find((item) => item.id === selectedClassId) ?? null,
    [classList.items, selectedClassId],
  );

  const classDetailQuery = useQuery({
    enabled: Boolean(accessToken && selectedClassId),
    queryFn: () => fetchAdminProductClassDetail(accessToken ?? "", selectedClassId ?? ""),
    queryKey: ["admin", "product-classes", "detail", selectedClassId],
    retry: false,
  });

  const createClassMutation = useMutation({
    mutationFn: (payload: AdminProductClassCreatePayload) =>
      createAdminProductClass(accessToken ?? "", payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo crear la clase."),
      });
    },
    onSuccess: (item) => {
      setFeedback({ tone: "success", message: "Clase creada correctamente." });
      setFormMode(null);
      setSelectedClassId(item.id);
      void queryClient.invalidateQueries({ queryKey: ["admin", "product-classes"] });
    },
  });

  const updateClassMutation = useMutation({
    mutationFn: ({
      classId,
      payload,
    }: {
      classId: string;
      payload: AdminProductClassUpdatePayload;
    }) => updateAdminProductClass(accessToken ?? "", classId, payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo actualizar la clase."),
      });
    },
    onSuccess: (item) => {
      setFeedback({ tone: "success", message: "Clase actualizada correctamente." });
      setFormMode(null);
      setSelectedClassId(item.id);
      void queryClient.invalidateQueries({ queryKey: ["admin", "product-classes"] });
    },
  });

  const detailClass = classDetailQuery.data ?? selectedClassPreview;
  const listErrorMessage = classesQuery.isError
    ? toBackofficeErrorMessage(
        classesQuery.error,
        "No se pudieron cargar las clases. Intenta nuevamente.",
      )
    : null;
  const detailErrorMessage = classDetailQuery.isError
    ? toBackofficeErrorMessage(classDetailQuery.error, "No se pudo cargar el detalle de la clase.")
    : null;
  const formErrorMessage =
    createClassMutation.isError || updateClassMutation.isError
      ? toBackofficeErrorMessage(
          createClassMutation.error ?? updateClassMutation.error,
          "No se pudo guardar la clase.",
        )
      : null;
  const pageStatusLabel = classesQuery.isLoading
    ? "Validando API"
    : classList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";
  const isSaving = createClassMutation.isPending || updateClassMutation.isPending;

  function patchFilters(patch: Partial<AdminProductClassListFilters>) {
    setFilters((current) => ({
      ...current,
      ...patch,
      page: patch.page ?? 1,
    }));
    setSelectedClassId(null);
  }

  function handleSelectClass(item: AdminProductClass) {
    setSelectedClassId(item.id);
  }

  function handlePageChange(page: number) {
    setFilters((current) => ({ ...current, page }));
  }

  function handleSubmitClass(payload: AdminProductClassCreatePayload) {
    if (!accessToken || isSaving) {
      return;
    }

    setFeedback(null);
    if (formMode?.type === "edit") {
      updateClassMutation.mutate({
        classId: formMode.item.id,
        payload,
      });
      return;
    }

    createClassMutation.mutate(payload);
  }

  function handleToggleStatus(item: AdminProductClass) {
    if (!accessToken || updateClassMutation.isPending) {
      return;
    }

    if (
      item.status === "active" &&
      item.activeProductCount > 0 &&
      !window.confirm(
        "Esta clase tiene productos activos. Puedes desactivarla, pero esos productos quedaran asociados a una clase inactiva. Continuar?",
      )
    ) {
      return;
    }

    setFeedback(null);
    updateClassMutation.mutate({
      classId: item.id,
      payload: {
        status: item.status === "active" ? "inactive" : "active",
      },
    });
  }

  function handleMoveClass(item: AdminProductClass, direction: "up" | "down") {
    if (!accessToken || updateClassMutation.isPending) {
      return;
    }

    setFeedback(null);
    updateClassMutation.mutate({
      classId: item.id,
      payload: {
        displayOrder: Math.max(0, item.displayOrder + (direction === "up" ? -10 : 10)),
      },
    });
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionGlobalOnly
        actionCapability="catalog.manage"
        actionLabel="Nueva clase"
        description="Gobierna categorias operativas, modo de captura POS, precio de clase y orden visual."
        meta={[pageStatusLabel]}
        onAction={() => {
          setFeedback(null);
          setFormMode({ type: "create" });
        }}
        title="Categorias / clases"
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminClassesFilters
          filters={filters}
          isBackendConnected={classList.isBackendConnected}
          options={classList.filterOptions}
          onChange={patchFilters}
        />

        <AdminClassesMetricStrip metrics={classList.metrics} isLoading={classesQuery.isLoading} />

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

        {formMode ? (
          <AdminClassFormPanel
            brandOptions={classList.filterOptions.brands}
            classItem={formMode.type === "edit" ? formMode.item : null}
            errorMessage={formErrorMessage}
            isSubmitting={isSaving}
            key={formMode.type === "edit" ? formMode.item.id : "create"}
            onClose={() => setFormMode(null)}
            onSubmit={handleSubmitClass}
          />
        ) : null}

        <div className="grid min-h-0 min-w-0 flex-1 items-stretch gap-2.5 overflow-hidden xl:grid-cols-[minmax(0,1fr)_minmax(15rem,18rem)]">
          <AdminClassesTable
            backendContract={classList.backendContract}
            classes={classList.items}
            errorMessage={listErrorMessage}
            isLoading={classesQuery.isLoading}
            isUpdating={updateClassMutation.isPending}
            page={classList.page}
            pageSize={classList.pageSize}
            selectedClassId={selectedClassId}
            total={classList.total}
            onEditClass={(item) => {
              setFeedback(null);
              setFormMode({ type: "edit", item });
            }}
            onMoveClass={handleMoveClass}
            onPageChange={handlePageChange}
            onSelectClass={handleSelectClass}
            onToggleStatus={handleToggleStatus}
          />
          <AdminClassesDetailPanel
            classItem={detailClass}
            errorMessage={detailErrorMessage}
            isLoading={classDetailQuery.isLoading}
            onEdit={(item) => {
              setFeedback(null);
              setFormMode({ type: "edit", item });
            }}
          />
        </div>
      </div>
    </section>
  );
}
