import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  activateAdminRecipe,
  adminRecipeCostsBackendContract,
  applyAdminRecipeStandardCost,
  createAdminRecipe,
  duplicateAdminRecipe,
  fetchAdminRecipeCostDetail,
  fetchAdminRecipeCosts,
} from "../api";
import { AdminRecipeCostDetailPanel } from "../components/AdminRecipeCostDetailPanel";
import { AdminRecipeCostsFilters } from "../components/AdminRecipeCostsFilters";
import { AdminRecipeCostsTable } from "../components/AdminRecipeCostsTable";
import { AdminRecipeFormPanel } from "../components/AdminRecipeFormPanel";
import type {
  AdminRecipe,
  AdminRecipeCostDetail,
  AdminRecipeCostFilterOptions,
  AdminRecipeCostListFilters,
  AdminRecipeCostListResponse,
  AdminRecipeCostProduct,
  AdminRecipeCreatePayload,
} from "../types";

const initialFilters: AdminRecipeCostListFilters = {
  page: 1,
  pageSize: 25,
  recipeState: "all",
  search: "",
};

const emptyFilterOptions: AdminRecipeCostFilterOptions = {
  brands: [],
  classes: [],
  rawMaterials: [],
};

const emptyRecipeCostList: AdminRecipeCostListResponse = {
  backendContract: adminRecipeCostsBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    highVariance: "0",
    recentlyUpdated: "0",
    withActiveRecipe: "0",
    withoutRecipe: "0",
    withWarnings: "0",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

function AdminRecipeCostMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminRecipeCostListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    { label: "Con receta", title: "Productos con receta activa", value: loadingValue ?? metrics.withActiveRecipe },
    { label: "Sin receta", title: "Productos sin receta activa", value: loadingValue ?? metrics.withoutRecipe },
    { label: "Revisar", title: "Recetas con advertencias", value: loadingValue ?? metrics.withWarnings },
    { label: "Varianza", title: "Productos con varianza alta", value: loadingValue ?? metrics.highVariance },
    { label: "Actualizadas", title: "Recetas actualizadas", value: loadingValue ?? metrics.recentlyUpdated },
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

export function AdminRecipeCostsPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminRecipeCostListFilters>(initialFilters);
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [formProduct, setFormProduct] = useState<AdminRecipeCostProduct | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(null);

  const listQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminRecipeCosts(accessToken ?? "", filters),
    queryKey: ["admin", "recipes-costs", "list", filters],
    retry: false,
  });

  const recipeCostList = listQuery.data ?? emptyRecipeCostList;
  const selectedPreview = useMemo(
    () => recipeCostList.items.find((item) => item.productId === selectedProductId) ?? null,
    [recipeCostList.items, selectedProductId],
  );

  const detailQuery = useQuery({
    enabled: Boolean(accessToken && selectedProductId),
    queryFn: () => fetchAdminRecipeCostDetail(accessToken ?? "", selectedProductId ?? ""),
    queryKey: ["admin", "recipes-costs", "detail", selectedProductId],
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: (payload: AdminRecipeCreatePayload) => createAdminRecipe(accessToken ?? "", payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo guardar la receta."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Receta guardada correctamente." });
      setFormProduct(null);
      setSelectedProductId(detail.product.productId);
      void queryClient.invalidateQueries({ queryKey: ["admin", "recipes-costs"] });
    },
  });

  const actionMutation = useMutation({
    mutationFn: (action: { type: "activate" | "duplicate" | "apply"; recipe: AdminRecipe }) => {
      if (action.type === "activate") {
        return activateAdminRecipe(accessToken ?? "", action.recipe.id);
      }
      if (action.type === "apply") {
        return applyAdminRecipeStandardCost(accessToken ?? "", action.recipe.id);
      }
      return duplicateAdminRecipe(accessToken ?? "", action.recipe.id, {
        activate: false,
        versionName: `Copia de ${action.recipe.versionName ?? "receta"}`,
      });
    },
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo completar la accion."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Accion aplicada correctamente." });
      setSelectedProductId(detail.product.productId);
      void queryClient.invalidateQueries({ queryKey: ["admin", "recipes-costs"] });
    },
  });

  const detail: AdminRecipeCostDetail | null =
    detailQuery.data ?? (selectedPreview ? { product: selectedPreview, activeRecipe: null, recipeVersions: [] } : null);
  const listErrorMessage = listQuery.isError
    ? toBackofficeErrorMessage(listQuery.error, "No se pudieron cargar recetas y costos.")
    : null;
  const detailErrorMessage = detailQuery.isError
    ? toBackofficeErrorMessage(detailQuery.error, "No se pudo cargar el detalle de receta.")
    : null;
  const formErrorMessage = createMutation.isError
    ? toBackofficeErrorMessage(createMutation.error, "No se pudo guardar la receta.")
    : null;
  const pageStatusLabel = listQuery.isLoading
    ? "Validando API"
    : recipeCostList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminRecipeCostListFilters>) {
    setFilters((current) => ({ ...current, ...patch, page: patch.page ?? 1 }));
    setSelectedProductId(null);
  }

  function handleCreateRecipe(payload: AdminRecipeCreatePayload) {
    if (!accessToken || createMutation.isPending) {
      return;
    }

    setFeedback(null);
    createMutation.mutate(payload);
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionLabel="Nueva receta"
        description="Gobierna recetas tecnicas, rendimiento, insumos y costo teorico por producto terminado."
        meta={[pageStatusLabel]}
        onAction={() => {
          setFeedback(null);
          setFormProduct(detail?.product ?? recipeCostList.items[0] ?? null);
        }}
        title="Recetas y costos"
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminRecipeCostsFilters
          filters={filters}
          isBackendConnected={recipeCostList.isBackendConnected}
          options={recipeCostList.filterOptions}
          onChange={patchFilters}
        />

        <AdminRecipeCostMetricStrip metrics={recipeCostList.metrics} isLoading={listQuery.isLoading} />

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

        {formProduct ? (
          <AdminRecipeFormPanel
            errorMessage={formErrorMessage}
            isSubmitting={createMutation.isPending}
            product={formProduct}
            rawMaterialOptions={recipeCostList.filterOptions.rawMaterials}
            onClose={() => setFormProduct(null)}
            onSubmit={handleCreateRecipe}
          />
        ) : null}

        <div className="grid min-h-0 min-w-0 flex-1 items-stretch gap-2.5 overflow-hidden xl:grid-cols-[minmax(0,1fr)_minmax(15rem,18rem)]">
          <AdminRecipeCostsTable
            backendContract={recipeCostList.backendContract}
            errorMessage={listErrorMessage}
            isLoading={listQuery.isLoading}
            page={recipeCostList.page}
            pageSize={recipeCostList.pageSize}
            products={recipeCostList.items}
            selectedProductId={selectedProductId}
            total={recipeCostList.total}
            onPageChange={(page) => setFilters((current) => ({ ...current, page }))}
            onSelectProduct={(item) => {
              setSelectedProductId(item.productId);
              setFeedback(null);
            }}
          />
          <AdminRecipeCostDetailPanel
            detail={detail}
            errorMessage={detailErrorMessage}
            isLoading={detailQuery.isLoading}
            onActivateRecipe={(recipe) => actionMutation.mutate({ type: "activate", recipe })}
            onApplyStandardCost={(recipe) => actionMutation.mutate({ type: "apply", recipe })}
            onCreateRecipe={(product) => setFormProduct(product)}
            onDuplicateRecipe={(recipe) => actionMutation.mutate({ type: "duplicate", recipe })}
          />
        </div>
      </div>
    </section>
  );
}
