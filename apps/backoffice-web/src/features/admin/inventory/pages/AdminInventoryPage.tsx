import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminEntityDrawer } from "../../components/AdminEntityDrawer";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminInventoryBackendContract,
  createAdminInventoryAdjustment,
  fetchAdminInventory,
  fetchAdminInventoryDetail,
} from "../api";
import { AdminInventoryAdjustmentPanel } from "../components/AdminInventoryAdjustmentPanel";
import { AdminInventoryDetailPanel } from "../components/AdminInventoryDetailPanel";
import { AdminInventoryFilters } from "../components/AdminInventoryFilters";
import { AdminInventoryTable } from "../components/AdminInventoryTable";
import type {
  AdminInventoryAdjustmentPayload,
  AdminInventoryDetail,
  AdminInventoryFilterOptions,
  AdminInventoryListFilters,
  AdminInventoryListItem,
  AdminInventoryListResponse,
} from "../types";

const defaultFilters: AdminInventoryListFilters = {
  locationCode: "all",
  page: 1,
  pageSize: 25,
  productKind: "all",
  productStatus: "all",
  search: "",
  stockState: "all",
};

const emptyFilterOptions: AdminInventoryFilterOptions = {
  branches: [],
  classes: [],
  locations: [],
  productKinds: [],
  products: [],
};

const emptyInventoryList: AdminInventoryListResponse = {
  backendContract: adminInventoryBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    estimatedValue: null,
    negativeStock: "0",
    productsWithStock: "0",
    staleStock: "0",
    totalRecords: "0",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

function getInitialFilters(): AdminInventoryListFilters {
  if (typeof window === "undefined") {
    return defaultFilters;
  }

  const params = new URLSearchParams(window.location.search);
  return {
    ...defaultFilters,
    branchId: params.get("branchId"),
    classId: params.get("classId"),
  };
}

function AdminInventoryMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminInventoryListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    {
      label: "Con existencia",
      title: "Productos con existencia",
      value: loadingValue ?? metrics.productsWithStock,
    },
    {
      label: "Stock negativo",
      title: "Registros con stock negativo",
      value: loadingValue ?? metrics.negativeStock,
    },
    {
      label: "Sin movimiento",
      title: "Registros sin movimiento reciente",
      value: loadingValue ?? metrics.staleStock,
    },
    {
      label: "Registros",
      title: "Registros de inventario",
      value: loadingValue ?? metrics.totalRecords,
    },
    {
      label: "Valor estimado",
      title: "Valor estimado por costo estandar disponible",
      value: loadingValue ?? metrics.estimatedValue ?? "No disponible",
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

function getBalanceId(item: AdminInventoryDetail | AdminInventoryListItem): string {
  return item.balanceId;
}

export function AdminInventoryPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminInventoryListFilters>(getInitialFilters);
  const [selectedBalanceId, setSelectedBalanceId] = useState<string | null>(null);
  const [adjustmentSource, setAdjustmentSource] = useState<
    AdminInventoryDetail | AdminInventoryListItem | null
  >(null);
  const [isAdjustmentOpen, setIsAdjustmentOpen] = useState(false);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const inventoryQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminInventory(accessToken ?? "", filters),
    queryKey: ["admin", "inventory", "list", filters],
    retry: false,
  });

  const inventoryList = inventoryQuery.data ?? emptyInventoryList;
  const selectedInventoryPreview = useMemo(
    () => inventoryList.items.find((item) => item.balanceId === selectedBalanceId) ?? null,
    [inventoryList.items, selectedBalanceId],
  );

  const inventoryDetailQuery = useQuery({
    enabled: Boolean(accessToken && selectedBalanceId),
    queryFn: () => fetchAdminInventoryDetail(accessToken ?? "", selectedBalanceId ?? ""),
    queryKey: ["admin", "inventory", "detail", selectedBalanceId],
    retry: false,
  });

  const adjustmentMutation = useMutation({
    mutationFn: (payload: AdminInventoryAdjustmentPayload) =>
      createAdminInventoryAdjustment(accessToken ?? "", payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo guardar el ajuste de inventario."),
      });
    },
    onSuccess: (adjustment) => {
      setFeedback({ tone: "success", message: "Ajuste de inventario guardado correctamente." });
      setIsAdjustmentOpen(false);
      setAdjustmentSource(null);
      setSelectedBalanceId(adjustment.balanceId);
      void queryClient.invalidateQueries({ queryKey: ["admin", "inventory"] });
    },
  });

  const detailInventory = inventoryDetailQuery.data ?? null;
  const listErrorMessage = inventoryQuery.isError
    ? toBackofficeErrorMessage(
        inventoryQuery.error,
        "No se pudo cargar inventario. Intenta nuevamente.",
      )
    : null;
  const detailErrorMessage = inventoryDetailQuery.isError
    ? toBackofficeErrorMessage(
        inventoryDetailQuery.error,
        "No se pudo cargar el detalle de inventario.",
      )
    : null;
  const adjustmentErrorMessage = adjustmentMutation.isError
    ? toBackofficeErrorMessage(adjustmentMutation.error, "No se pudo guardar el ajuste.")
    : null;
  const pageStatusLabel = inventoryQuery.isLoading
    ? "Validando API"
    : inventoryList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminInventoryListFilters>) {
    setFilters((current) => ({
      ...current,
      ...patch,
      page: patch.page ?? 1,
    }));
    setSelectedBalanceId(null);
  }

  function handleSelectInventory(item: AdminInventoryListItem) {
    setSelectedBalanceId(item.balanceId);
  }

  function handlePageChange(page: number) {
    setFilters((current) => ({ ...current, page }));
  }

  function handleOpenAdjustment(source?: AdminInventoryDetail | AdminInventoryListItem | null) {
    setFeedback(null);
    if (source) {
      setSelectedBalanceId(getBalanceId(source));
    }
    setAdjustmentSource(source ?? null);
    setIsAdjustmentOpen(true);
  }

  function handleSubmitAdjustment(payload: AdminInventoryAdjustmentPayload) {
    if (!accessToken || adjustmentMutation.isPending) {
      return;
    }

    setFeedback(null);
    adjustmentMutation.mutate(payload);
  }

  function handleOpenProduct(productId: string) {
    window.location.href = `/admin/productos?productId=${productId}`;
  }

  function handleOpenBranch(branchId: string) {
    window.location.href = `/admin/sucursales?branchId=${branchId}`;
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionCapability="inventory.adjust"
        actionLabel="Nuevo ajuste"
        description="Consulta existencias por sucursal, producto y ubicacion; revisa movimientos, alertas y ajustes auditados."
        meta={[pageStatusLabel, "Conteos pendientes de contrato"]}
        onAction={() => handleOpenAdjustment(null)}
        title="Inventario"
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminInventoryFilters
          filters={filters}
          isBackendConnected={inventoryList.isBackendConnected}
          options={inventoryList.filterOptions}
          onChange={patchFilters}
        />

        <AdminInventoryMetricStrip
          metrics={inventoryList.metrics}
          isLoading={inventoryQuery.isLoading}
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

        <AdminEntityDrawer
          description="Registra ajustes auditados sin desplazar la tabla de inventario."
          isOpen={isAdjustmentOpen}
          title="Nuevo ajuste de inventario"
          onClose={() => {
            setIsAdjustmentOpen(false);
            setAdjustmentSource(null);
          }}
        >
          <AdminInventoryAdjustmentPanel
            branchOptions={inventoryList.filterOptions.branches}
            errorMessage={adjustmentErrorMessage}
            initialInventory={adjustmentSource}
            isSubmitting={adjustmentMutation.isPending}
            locationOptions={inventoryList.filterOptions.locations}
            productOptions={inventoryList.filterOptions.products}
            onClose={() => {
              setIsAdjustmentOpen(false);
              setAdjustmentSource(null);
            }}
            onSubmit={handleSubmitAdjustment}
          />
        </AdminEntityDrawer>

        <div className="grid min-h-0 min-w-0 flex-1 items-stretch gap-2.5 overflow-hidden xl:grid-cols-[minmax(0,1fr)_minmax(15rem,19rem)]">
          <AdminInventoryTable
            backendContract={inventoryList.backendContract}
            errorMessage={listErrorMessage}
            inventory={inventoryList.items}
            isLoading={inventoryQuery.isLoading}
            isSubmitting={adjustmentMutation.isPending}
            page={inventoryList.page}
            pageSize={inventoryList.pageSize}
            selectedBalanceId={selectedBalanceId}
            total={inventoryList.total}
            onAdjust={handleOpenAdjustment}
            onOpenBranch={handleOpenBranch}
            onOpenProduct={handleOpenProduct}
            onPageChange={handlePageChange}
            onSelectInventory={handleSelectInventory}
          />
          <AdminInventoryDetailPanel
            errorMessage={detailErrorMessage}
            inventoryDetail={detailInventory}
            inventoryPreview={selectedInventoryPreview}
            isLoading={inventoryDetailQuery.isLoading}
            onAdjust={handleOpenAdjustment}
            onOpenBranch={handleOpenBranch}
            onOpenProduct={handleOpenProduct}
          />
        </div>
      </div>
    </section>
  );
}
