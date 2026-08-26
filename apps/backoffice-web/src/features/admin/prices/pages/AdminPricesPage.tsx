import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminPricesBackendContract,
  fetchAdminPriceDetail,
  fetchAdminPrices,
  updateAdminPrice,
} from "../api";
import { AdminPriceDetailPanel } from "../components/AdminPriceDetailPanel";
import { AdminPriceEditPanel } from "../components/AdminPriceEditPanel";
import { AdminPricesFilters } from "../components/AdminPricesFilters";
import { AdminPricesTable } from "../components/AdminPricesTable";
import type {
  AdminPriceFilterOptions,
  AdminPriceListFilters,
  AdminPriceListResponse,
  AdminPriceRow,
  AdminPriceUpdatePayload,
} from "../types";

const initialFilters: AdminPriceListFilters = {
  page: 1,
  pageSize: 25,
  captureMode: "all",
  entityType: "all",
  priceHealth: "all",
  search: "",
  status: "all",
  updatedFrom: null,
  updatedTo: null,
};

const emptyFilterOptions: AdminPriceFilterOptions = {
  brands: [],
  classes: [],
};

const emptyPriceList: AdminPriceListResponse = {
  backendContract: adminPricesBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    classCapture: "0",
    highVariance: "0",
    missingOrInvalid: "0",
    productDirect: "0",
    recentlyChanged: "0",
    totalEntities: "0",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

function AdminPricesMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminPriceListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    { label: "Total", title: "Entidades con precio", value: loadingValue ?? metrics.totalEntities },
    { label: "Directos", title: "PRODUCT_DIRECT", value: loadingValue ?? metrics.productDirect },
    { label: "Por clase", title: "CLASS_CAPTURE", value: loadingValue ?? metrics.classCapture },
    { label: "Sin precio", title: "Precio faltante o cero", value: loadingValue ?? metrics.missingOrInvalid },
    { label: "Margen", title: "Margen bajo o negativo", value: loadingValue ?? metrics.highVariance },
    { label: "Recientes", title: "Cambios recientes", value: loadingValue ?? metrics.recentlyChanged },
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

function priceKey(item: AdminPriceRow): string {
  return `${item.entityType}:${item.entityId}`;
}

export function AdminPricesPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminPriceListFilters>(initialFilters);
  const [selectedPrice, setSelectedPrice] = useState<AdminPriceRow | null>(null);
  const [editingPrice, setEditingPrice] = useState<AdminPriceRow | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(null);

  const pricesQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminPrices(accessToken ?? "", filters),
    queryKey: ["admin", "prices", "list", filters],
    retry: false,
  });

  const priceList = pricesQuery.data ?? emptyPriceList;
  const selectedPricePreview = useMemo(() => {
    if (!selectedPrice) {
      return null;
    }

    return priceList.items.find((item) => priceKey(item) === priceKey(selectedPrice)) ?? selectedPrice;
  }, [priceList.items, selectedPrice]);

  const priceDetailQuery = useQuery({
    enabled: Boolean(accessToken && selectedPricePreview),
    queryFn: () =>
      fetchAdminPriceDetail(
        accessToken ?? "",
        selectedPricePreview?.entityType ?? "",
        selectedPricePreview?.entityId ?? "",
      ),
    queryKey: ["admin", "prices", "detail", selectedPricePreview?.entityType, selectedPricePreview?.entityId],
    retry: false,
  });

  const updatePriceMutation = useMutation({
    mutationFn: ({ payload, row }: { payload: AdminPriceUpdatePayload; row: AdminPriceRow }) =>
      updateAdminPrice(accessToken ?? "", row, payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo actualizar el precio."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Precio actualizado correctamente." });
      setSelectedPrice(detail.price);
      setEditingPrice(null);
      void queryClient.invalidateQueries({ queryKey: ["admin", "prices"] });
    },
  });

  const listErrorMessage = pricesQuery.isError
    ? toBackofficeErrorMessage(pricesQuery.error, "No se pudieron cargar los precios. Intenta nuevamente.")
    : null;
  const detailErrorMessage = priceDetailQuery.isError
    ? toBackofficeErrorMessage(priceDetailQuery.error, "No se pudo cargar el detalle del precio.")
    : null;
  const updateErrorMessage = updatePriceMutation.isError
    ? toBackofficeErrorMessage(updatePriceMutation.error, "No se pudo guardar el precio.")
    : null;
  const pageStatusLabel = pricesQuery.isLoading
    ? "Validando API"
    : priceList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminPriceListFilters>) {
    setFilters((current) => ({
      ...current,
      ...patch,
      page: patch.page ?? 1,
    }));
    setSelectedPrice(null);
  }

  function handlePageChange(page: number) {
    setFilters((current) => ({ ...current, page }));
  }

  function handleSelectPrice(item: AdminPriceRow) {
    setSelectedPrice(item);
  }

  function handleEditPrice(item: AdminPriceRow) {
    setFeedback(null);
    setSelectedPrice(item);
    setEditingPrice(item);
  }

  function handleSubmitPrice(payload: AdminPriceUpdatePayload) {
    if (!accessToken || !editingPrice || updatePriceMutation.isPending) {
      return;
    }

    setFeedback(null);
    updatePriceMutation.mutate({ row: editingPrice, payload });
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        description="Gobierna precios comerciales vigentes respetando su propietario real: producto o clase."
        meta={[pageStatusLabel]}
        title="Precios"
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminPricesFilters
          filters={filters}
          isBackendConnected={priceList.isBackendConnected}
          options={priceList.filterOptions}
          onChange={patchFilters}
        />

        <AdminPricesMetricStrip metrics={priceList.metrics} isLoading={pricesQuery.isLoading} />

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

        {editingPrice ? (
          <AdminPriceEditPanel
            errorMessage={updateErrorMessage}
            isSubmitting={updatePriceMutation.isPending}
            price={editingPrice}
            onClose={() => setEditingPrice(null)}
            onSubmit={handleSubmitPrice}
          />
        ) : null}

        <div className="grid min-h-0 min-w-0 flex-1 items-stretch gap-2.5 overflow-hidden xl:grid-cols-[minmax(0,1fr)_minmax(15rem,18rem)]">
          <AdminPricesTable
            backendContract={priceList.backendContract}
            errorMessage={listErrorMessage}
            isLoading={pricesQuery.isLoading}
            page={priceList.page}
            pageSize={priceList.pageSize}
            prices={priceList.items}
            selectedPriceKey={selectedPricePreview ? priceKey(selectedPricePreview) : null}
            total={priceList.total}
            onEditPrice={handleEditPrice}
            onPageChange={handlePageChange}
            onSelectPrice={handleSelectPrice}
          />
          <AdminPriceDetailPanel
            detail={priceDetailQuery.data ?? (selectedPricePreview ? { historyNote: null, price: selectedPricePreview } : null)}
            errorMessage={detailErrorMessage}
            isLoading={priceDetailQuery.isLoading}
            onEditPrice={handleEditPrice}
          />
        </div>
      </div>
    </section>
  );
}
