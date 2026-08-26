import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminDiscountsBackendContract,
  createAdminDiscount,
  duplicateAdminDiscount,
  fetchAdminDiscountDetail,
  fetchAdminDiscounts,
  updateAdminDiscount,
} from "../api";
import { AdminDiscountDetailPanel } from "../components/AdminDiscountDetailPanel";
import { AdminDiscountFormPanel } from "../components/AdminDiscountFormPanel";
import { AdminDiscountsFilters } from "../components/AdminDiscountsFilters";
import { AdminDiscountsTable } from "../components/AdminDiscountsTable";
import type {
  AdminDiscount,
  AdminDiscountFilterOptions,
  AdminDiscountListFilters,
  AdminDiscountListResponse,
  AdminDiscountSavePayload,
} from "../types";

const initialFilters: AdminDiscountListFilters = {
  page: 1,
  pageSize: 25,
  discountType: "all",
  search: "",
  status: "all",
  targetScope: "all",
  validity: "all",
  warningState: "all",
};

const emptyFilterOptions: AdminDiscountFilterOptions = {
  brands: [],
  classes: [],
  products: [],
};

const emptyDiscountList: AdminDiscountListResponse = {
  backendContract: adminDiscountsBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    activeDiscounts: "0",
    classScoped: "0",
    expiredDiscounts: "0",
    productScoped: "0",
    totalDiscounts: "0",
    upcomingDiscounts: "0",
    withWarnings: "0",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

function AdminDiscountMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminDiscountListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    { label: "Total", title: "Total de descuentos", value: loadingValue ?? metrics.totalDiscounts },
    { label: "Activos", title: "Descuentos activos", value: loadingValue ?? metrics.activeDiscounts },
    { label: "Proximos", title: "Descuentos proximos", value: loadingValue ?? metrics.upcomingDiscounts },
    { label: "Expirados", title: "Descuentos expirados", value: loadingValue ?? metrics.expiredDiscounts },
    { label: "Producto", title: "Alcance producto", value: loadingValue ?? metrics.productScoped },
    { label: "Clase", title: "Alcance clase", value: loadingValue ?? metrics.classScoped },
    { label: "Revisar", title: "Con advertencias", value: loadingValue ?? metrics.withWarnings },
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

export function AdminDiscountsPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminDiscountListFilters>(initialFilters);
  const [selectedDiscountId, setSelectedDiscountId] = useState<string | null>(null);
  const [formMode, setFormMode] = useState<{ type: "create" } | { type: "edit"; item: AdminDiscount } | null>(
    null,
  );
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(null);

  const discountsQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminDiscounts(accessToken ?? "", filters),
    queryKey: ["admin", "discounts", "list", filters],
    retry: false,
  });

  const discountList = discountsQuery.data ?? emptyDiscountList;
  const selectedDiscountPreview = useMemo(
    () => discountList.items.find((item) => item.id === selectedDiscountId) ?? null,
    [discountList.items, selectedDiscountId],
  );

  const discountDetailQuery = useQuery({
    enabled: Boolean(accessToken && selectedDiscountId),
    queryFn: () => fetchAdminDiscountDetail(accessToken ?? "", selectedDiscountId ?? ""),
    queryKey: ["admin", "discounts", "detail", selectedDiscountId],
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: (payload: AdminDiscountSavePayload) => createAdminDiscount(accessToken ?? "", payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo crear el descuento."),
      });
    },
    onSuccess: (item) => {
      setFeedback({ tone: "success", message: "Descuento creado correctamente." });
      setFormMode(null);
      setSelectedDiscountId(item.id);
      void queryClient.invalidateQueries({ queryKey: ["admin", "discounts"] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ discountId, payload }: { discountId: string; payload: AdminDiscountSavePayload }) =>
      updateAdminDiscount(accessToken ?? "", discountId, payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo actualizar el descuento."),
      });
    },
    onSuccess: (item) => {
      setFeedback({ tone: "success", message: "Descuento actualizado correctamente." });
      setFormMode(null);
      setSelectedDiscountId(item.id);
      void queryClient.invalidateQueries({ queryKey: ["admin", "discounts"] });
    },
  });

  const duplicateMutation = useMutation({
    mutationFn: (item: AdminDiscount) =>
      duplicateAdminDiscount(accessToken ?? "", item.id, {
        code: item.code ? `${item.code}-COPY` : null,
        name: `${item.name} copia`,
      }),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo duplicar el descuento."),
      });
    },
    onSuccess: (item) => {
      setFeedback({ tone: "success", message: "Descuento duplicado como inactivo." });
      setSelectedDiscountId(item.id);
      void queryClient.invalidateQueries({ queryKey: ["admin", "discounts"] });
    },
  });

  const detailDiscount = discountDetailQuery.data ?? selectedDiscountPreview;
  const listErrorMessage = discountsQuery.isError
    ? toBackofficeErrorMessage(discountsQuery.error, "No se pudieron cargar los descuentos. Intenta nuevamente.")
    : null;
  const detailErrorMessage = discountDetailQuery.isError
    ? toBackofficeErrorMessage(discountDetailQuery.error, "No se pudo cargar el detalle del descuento.")
    : null;
  const formErrorMessage =
    createMutation.isError || updateMutation.isError
      ? toBackofficeErrorMessage(createMutation.error ?? updateMutation.error, "No se pudo guardar el descuento.")
      : null;
  const pageStatusLabel = discountsQuery.isLoading
    ? "Validando API"
    : discountList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";
  const isSaving = createMutation.isPending || updateMutation.isPending;
  const isUpdating = isSaving || duplicateMutation.isPending;

  function patchFilters(patch: Partial<AdminDiscountListFilters>) {
    setFilters((current) => ({
      ...current,
      ...patch,
      page: patch.page ?? 1,
    }));
    setSelectedDiscountId(null);
  }

  function handleSubmitDiscount(payload: AdminDiscountSavePayload) {
    if (!accessToken || isSaving) {
      return;
    }

    setFeedback(null);
    if (formMode?.type === "edit") {
      updateMutation.mutate({ discountId: formMode.item.id, payload });
      return;
    }
    createMutation.mutate(payload);
  }

  function handleToggleStatus(item: AdminDiscount) {
    if (!accessToken || updateMutation.isPending) {
      return;
    }
    setFeedback(null);
    updateMutation.mutate({
      discountId: item.id,
      payload: {
        brandId: item.brandId,
        code: item.code,
        currencyCode: item.currencyCode,
        description: item.description,
        discountType: item.discountType,
        isPosEligible: item.isPosEligible,
        name: item.name,
        priority: item.priority,
        status: item.status === "ACTIVE" ? "INACTIVE" : "ACTIVE",
        targetId: item.targetId,
        targetScope: item.targetScope,
        validFromUtc: item.validFromUtc,
        validToUtc: item.validToUtc,
        value: item.value,
      },
    });
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionLabel="Nuevo descuento"
        description="Gobierna reglas comerciales de descuento sin modificar precios base ni ventas historicas."
        meta={[pageStatusLabel]}
        title="Descuentos"
        onAction={() => {
          setFeedback(null);
          setFormMode({ type: "create" });
        }}
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminDiscountsFilters
          filters={filters}
          isBackendConnected={discountList.isBackendConnected}
          options={discountList.filterOptions}
          onChange={patchFilters}
        />

        <AdminDiscountMetricStrip metrics={discountList.metrics} isLoading={discountsQuery.isLoading} />

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
          <AdminDiscountFormPanel
            brandOptions={discountList.filterOptions.brands}
            classOptions={discountList.filterOptions.classes}
            discount={formMode.type === "edit" ? formMode.item : null}
            errorMessage={formErrorMessage}
            isSubmitting={isSaving}
            key={formMode.type === "edit" ? formMode.item.id : "create"}
            productOptions={discountList.filterOptions.products}
            onClose={() => setFormMode(null)}
            onSubmit={handleSubmitDiscount}
          />
        ) : null}

        <div className="grid min-h-0 min-w-0 flex-1 items-stretch gap-2.5 overflow-hidden xl:grid-cols-[minmax(0,1fr)_minmax(15rem,18rem)]">
          <AdminDiscountsTable
            backendContract={discountList.backendContract}
            discounts={discountList.items}
            errorMessage={listErrorMessage}
            isLoading={discountsQuery.isLoading}
            isUpdating={isUpdating}
            page={discountList.page}
            pageSize={discountList.pageSize}
            selectedDiscountId={selectedDiscountId}
            total={discountList.total}
            onDuplicateDiscount={(item) => {
              setFeedback(null);
              duplicateMutation.mutate(item);
            }}
            onEditDiscount={(item) => {
              setFeedback(null);
              setFormMode({ type: "edit", item });
            }}
            onPageChange={(page) => setFilters((current) => ({ ...current, page }))}
            onSelectDiscount={(item) => setSelectedDiscountId(item.id)}
            onToggleStatus={handleToggleStatus}
          />
          <AdminDiscountDetailPanel
            discount={detailDiscount}
            errorMessage={detailErrorMessage}
            isLoading={discountDetailQuery.isLoading}
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
