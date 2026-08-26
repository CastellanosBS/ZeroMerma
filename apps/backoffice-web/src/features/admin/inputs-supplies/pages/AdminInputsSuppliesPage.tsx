import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminInputSupplyBackendContract,
  changeAdminInputSupplyStatus,
  createAdminInputSupply,
  fetchAdminInputSupplies,
  fetchAdminInputSupplyDetail,
  updateAdminInputSupply,
} from "../api";
import { AdminInputSupplyDetailPanel } from "../components/AdminInputSupplyDetailPanel";
import { AdminInputSuppliesFilters } from "../components/AdminInputSuppliesFilters";
import { AdminInputSupplyFormPanel } from "../components/AdminInputSupplyFormPanel";
import { AdminInputSuppliesTable } from "../components/AdminInputSuppliesTable";
import type {
  AdminInputSupplyDetail,
  AdminInputSupplyFilterOptions,
  AdminInputSupplyListFilters,
  AdminInputSupplyListItem,
  AdminInputSupplyListResponse,
  AdminInputSupplyPayload,
} from "../types";

const defaultFilters: AdminInputSupplyListFilters = {
  classId: null,
  costState: "all",
  inventoryTracked: "all",
  page: 1,
  pageSize: 25,
  productKind: "all",
  purchasable: "all",
  recipeUsage: "all",
  search: "",
  status: "all",
  stockState: "all",
  supplierId: null,
  usageType: null,
  warningState: "all",
  withoutSupplier: "all",
};

const emptyFilterOptions: AdminInputSupplyFilterOptions = {
  classes: [],
  costStates: [],
  productKinds: [],
  recipeUsageStates: [],
  statuses: [],
  stockStates: [],
  suppliers: [],
  usageTypes: [],
  warningStates: [],
};

const emptyInputSupplyList: AdminInputSupplyListResponse = {
  backendContract: adminInputSupplyBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    activeConsumables: "0",
    activeDisposables: "0",
    activeRawMaterials: "0",
    lowStock: "0",
    missingCost: "0",
    usedInRecipes: "0",
    withoutSupplier: "0",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

function getInitialFilters(): AdminInputSupplyListFilters {
  if (typeof window === "undefined") {
    return defaultFilters;
  }
  const params = new URLSearchParams(window.location.search);
  return {
    ...defaultFilters,
    classId: params.get("classId") ?? params.get("class_id"),
    productKind: (params.get("productKind") ?? "all") as AdminInputSupplyListFilters["productKind"],
    supplierId: params.get("supplierId") ?? params.get("supplier_id"),
  };
}

function AdminInputSupplyMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminInputSupplyListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    {
      label: "Materia prima",
      title: "Insumos activos",
      value: loadingValue ?? metrics.activeRawMaterials,
    },
    {
      label: "Consumibles",
      title: "Consumibles activos",
      value: loadingValue ?? metrics.activeConsumables,
    },
    {
      label: "Desechables",
      title: "Desechables / empaques",
      value: loadingValue ?? metrics.activeDisposables,
    },
    {
      label: "Sin proveedor",
      title: "Sin proveedor",
      value: loadingValue ?? metrics.withoutSupplier,
    },
    { label: "Sin costo", title: "Sin costo", value: loadingValue ?? metrics.missingCost },
    { label: "Stock bajo", title: "Stock bajo", value: loadingValue ?? metrics.lowStock },
    {
      label: "En recetas",
      title: "Usados en recetas",
      value: loadingValue ?? metrics.usedInRecipes,
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

export function AdminInputsSuppliesPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminInputSupplyListFilters>(getInitialFilters);
  const [selectedInputId, setSelectedInputId] = useState<string | null>(() => {
    if (typeof window === "undefined") {
      return null;
    }
    return new URLSearchParams(window.location.search).get("productId");
  });
  const [editingInput, setEditingInput] = useState<AdminInputSupplyDetail | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const inputsQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminInputSupplies(accessToken ?? "", filters),
    queryKey: ["admin", "inputs-supplies", "list", filters],
    retry: false,
  });

  const inputList = inputsQuery.data ?? emptyInputSupplyList;
  const selectedInputPreview = useMemo(
    () => inputList.items.find((item) => item.id === selectedInputId) ?? null,
    [inputList.items, selectedInputId],
  );

  const inputDetailQuery = useQuery({
    enabled: Boolean(accessToken && selectedInputId),
    queryFn: () => fetchAdminInputSupplyDetail(accessToken ?? "", selectedInputId ?? ""),
    queryKey: ["admin", "inputs-supplies", "detail", selectedInputId],
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: (payload: AdminInputSupplyPayload) =>
      createAdminInputSupply(accessToken ?? "", payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo guardar el insumo."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Insumo guardado correctamente." });
      setSelectedInputId(detail.overview.id);
      setIsFormOpen(false);
      setEditingInput(null);
      void queryClient.invalidateQueries({ queryKey: ["admin", "inputs-supplies"] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ payload, productId }: { payload: AdminInputSupplyPayload; productId: string }) =>
      updateAdminInputSupply(accessToken ?? "", productId, payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo actualizar el insumo."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Insumo actualizado correctamente." });
      setSelectedInputId(detail.overview.id);
      setIsFormOpen(false);
      setEditingInput(null);
      void queryClient.invalidateQueries({ queryKey: ["admin", "inputs-supplies"] });
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({ isActive, productId }: { isActive: boolean; productId: string }) =>
      changeAdminInputSupplyStatus(accessToken ?? "", productId, {
        isActive,
        notes: isActive ? "Activado desde Backoffice." : "Desactivado desde Backoffice.",
      }),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo cambiar el estado."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Estado del insumo actualizado." });
      setSelectedInputId(detail.overview.id);
      void queryClient.invalidateQueries({ queryKey: ["admin", "inputs-supplies"] });
    },
  });

  const listErrorMessage = inputsQuery.isError
    ? toBackofficeErrorMessage(inputsQuery.error, "No se pudieron cargar insumos.")
    : null;
  const detailErrorMessage = inputDetailQuery.isError
    ? toBackofficeErrorMessage(inputDetailQuery.error, "No se pudo cargar el detalle del insumo.")
    : null;
  const formErrorMessage =
    (createMutation.isError || updateMutation.isError) && feedback?.tone === "error"
      ? feedback.message
      : null;
  const isSubmitting =
    createMutation.isPending || updateMutation.isPending || statusMutation.isPending;
  const pageStatusLabel = inputsQuery.isLoading
    ? "Validando API"
    : inputList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminInputSupplyListFilters>) {
    setFilters((current) => ({ ...current, ...patch, page: patch.page ?? 1 }));
    setSelectedInputId(null);
  }

  function handleSubmit(payload: AdminInputSupplyPayload) {
    if (!accessToken || isSubmitting) {
      return;
    }
    setFeedback(null);
    if (editingInput) {
      updateMutation.mutate({ payload, productId: editingInput.overview.id });
      return;
    }
    createMutation.mutate(payload);
  }

  function handleChangeStatus(item: AdminInputSupplyListItem, isActive: boolean) {
    if (!accessToken || isSubmitting) {
      return;
    }
    if (!isActive && item.warnings.length > 0 && typeof window !== "undefined") {
      const shouldContinue = window.confirm(
        "Desactivar este insumo puede afectar compras, recetas o inventario. El historial se conserva. Continuar?",
      );
      if (!shouldContinue) {
        return;
      }
    }
    setFeedback(null);
    statusMutation.mutate({ isActive, productId: item.id });
  }

  function handleEditCurrent() {
    if (!inputDetailQuery.data) {
      return;
    }
    setEditingInput(inputDetailQuery.data);
    setIsFormOpen(true);
    setFeedback(null);
  }

  function handleOpenProduct(productId: string) {
    window.location.href = `/admin/productos?productId=${productId}`;
  }

  function handleOpenSuppliers(productId: string) {
    window.location.href = `/admin/proveedores?productId=${productId}`;
  }

  function handleOpenSupplier(supplierId: string) {
    window.location.href = `/admin/proveedores?supplierId=${supplierId}`;
  }

  function handleOpenInventory(productId: string) {
    window.location.href = `/admin/inventario?productId=${productId}`;
  }

  function handleOpenRecipes(productId: string) {
    window.location.href = `/admin/recetas-costos?productId=${productId}`;
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionLabel="Nuevo insumo"
        description="Administra materias primas, consumibles, desechables y materiales de operacion usados en compras, inventario, recetas y produccion."
        meta={[pageStatusLabel, "Catalogo canonico"]}
        onAction={() => {
          setFeedback(null);
          setEditingInput(null);
          setIsFormOpen(true);
        }}
        title="Insumos y consumibles"
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminInputSuppliesFilters
          filters={filters}
          isBackendConnected={inputList.isBackendConnected}
          options={inputList.filterOptions}
          onChange={patchFilters}
        />
        <AdminInputSupplyMetricStrip
          isLoading={inputsQuery.isLoading}
          metrics={inputList.metrics}
        />

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

        {isFormOpen ? (
          <AdminInputSupplyFormPanel
            classOptions={inputList.filterOptions.classes}
            errorMessage={formErrorMessage}
            initialInput={editingInput}
            isSubmitting={isSubmitting}
            supplierOptions={inputList.filterOptions.suppliers}
            usageTypeOptions={inputList.filterOptions.usageTypes}
            onClose={() => {
              setIsFormOpen(false);
              setEditingInput(null);
            }}
            onSubmit={handleSubmit}
          />
        ) : null}

        <div className="grid min-h-0 min-w-0 flex-1 items-stretch gap-2.5 overflow-hidden xl:grid-cols-[minmax(0,1fr)_minmax(22rem,0.42fr)]">
          <AdminInputSuppliesTable
            backendContract={inputList.backendContract}
            errorMessage={listErrorMessage}
            inputs={inputList.items}
            isLoading={inputsQuery.isLoading}
            isSubmitting={isSubmitting}
            page={inputList.page}
            pageSize={inputList.pageSize}
            selectedInputId={selectedInputId}
            total={inputList.total}
            onChangeStatus={handleChangeStatus}
            onOpenInventory={handleOpenInventory}
            onOpenProduct={handleOpenProduct}
            onOpenSuppliers={handleOpenSuppliers}
            onPageChange={(page) => setFilters((current) => ({ ...current, page }))}
            onSelectInput={(item) => {
              setSelectedInputId(item.id);
              setIsFormOpen(false);
              setEditingInput(null);
            }}
          />
          <div className="flex min-h-0 flex-col gap-2.5 overflow-hidden">
            {inputDetailQuery.data ? (
              <button
                className="rounded-[16px] border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700"
                type="button"
                onClick={handleEditCurrent}
              >
                Editar insumo
              </button>
            ) : null}
            <AdminInputSupplyDetailPanel
              errorMessage={detailErrorMessage}
              inputDetail={inputDetailQuery.data ?? null}
              inputPreview={selectedInputPreview}
              isLoading={inputDetailQuery.isLoading}
              onOpenInventory={handleOpenInventory}
              onOpenProduct={handleOpenProduct}
              onOpenRecipes={handleOpenRecipes}
              onOpenSupplier={handleOpenSupplier}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
