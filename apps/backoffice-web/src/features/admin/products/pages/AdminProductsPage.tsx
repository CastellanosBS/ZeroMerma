import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminEntityDrawer } from "../../components/AdminEntityDrawer";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminProductsBackendContract,
  createAdminProduct,
  fetchAdminProductDetail,
  fetchAdminProducts,
} from "../api";
import { AdminProductCreationPanel } from "../components/AdminProductCreationPanel";
import { AdminProductsDetailPanel } from "../components/AdminProductsDetailPanel";
import { AdminProductsFilters } from "../components/AdminProductsFilters";
import { AdminProductsTable } from "../components/AdminProductsTable";
import type {
  AdminProduct,
  AdminProductCreatePayload,
  AdminProductFilterOptions,
  AdminProductListFilters,
  AdminProductListResponse,
} from "../types";

const initialFilters: AdminProductListFilters = {
  page: 1,
  pageSize: 25,
  captureMode: "all",
  readiness: "all",
  search: "",
  status: "all",
};

function getInitialFilters(): AdminProductListFilters {
  const params = new URLSearchParams(window.location.search);
  const classId = params.get("class_id");

  return {
    ...initialFilters,
    classId: classId || null,
  };
}

const emptyFilterOptions: AdminProductFilterOptions = {
  branches: [],
  brands: [],
  classes: [],
};

const emptyProductList: AdminProductListResponse = {
  backendContract: adminProductsBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    activeProducts: null,
    classCapture: null,
    productDirect: null,
    requireAttention: null,
    withoutBranchAvailability: null,
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

function metricValue(value: string | null | undefined, isLoading: boolean): string {
  if (isLoading) {
    return "Cargando";
  }

  return value ?? "Pendiente";
}

function AdminProductsMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminProductListResponse["metrics"];
}) {
  const items = [
    {
      label: "Activos",
      title: "Productos activos",
      value: metricValue(metrics.activeProducts, isLoading),
    },
    {
      label: "Directos",
      title: "PRODUCT_DIRECT",
      value: metricValue(metrics.productDirect, isLoading),
    },
    {
      label: "Por clase",
      title: "CLASS_CAPTURE",
      value: metricValue(metrics.classCapture, isLoading),
    },
    {
      label: "Atencion",
      title: "Requieren atencion",
      value: metricValue(metrics.requireAttention, isLoading),
    },
    {
      label: "Disponibilidad",
      title: "Disponibilidad por sucursal",
      value: metrics.withoutBranchAvailability ?? "Pendiente de contrato",
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

export function AdminProductsPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminProductListFilters>(getInitialFilters);
  const [isCreating, setIsCreating] = useState(false);
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const productsQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminProducts(accessToken ?? "", filters),
    queryKey: ["admin", "products", "list", filters],
    retry: false,
  });

  const productList = productsQuery.data ?? emptyProductList;
  const selectedProductPreview = useMemo(
    () => productList.items.find((product) => product.id === selectedProductId) ?? null,
    [productList.items, selectedProductId],
  );

  const productDetailQuery = useQuery({
    enabled: Boolean(accessToken && selectedProductId),
    queryFn: () => fetchAdminProductDetail(accessToken ?? "", selectedProductId ?? ""),
    queryKey: ["admin", "products", "detail", selectedProductId],
    retry: false,
  });

  const createProductMutation = useMutation({
    mutationFn: (payload: AdminProductCreatePayload) =>
      createAdminProduct(accessToken ?? "", payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo crear el producto."),
      });
    },
    onSuccess: (product) => {
      setFeedback({ tone: "success", message: "Producto creado correctamente." });
      setIsCreating(false);
      setSelectedProductId(product.id);
      void queryClient.invalidateQueries({ queryKey: ["admin", "products"] });
    },
  });

  const detailProduct = productDetailQuery.data ?? selectedProductPreview;
  const listErrorMessage = productsQuery.isError
    ? toBackofficeErrorMessage(
        productsQuery.error,
        "No se pudieron cargar los productos. Intenta nuevamente.",
      )
    : null;
  const detailErrorMessage = productDetailQuery.isError
    ? toBackofficeErrorMessage(
        productDetailQuery.error,
        "No se pudo cargar el detalle del producto.",
      )
    : null;
  const createErrorMessage = createProductMutation.isError
    ? toBackofficeErrorMessage(createProductMutation.error, "No se pudo crear el producto.")
    : null;
  const pageStatusLabel = productsQuery.isLoading
    ? "Validando API"
    : productList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminProductListFilters>) {
    setFilters((current) => ({
      ...current,
      ...patch,
      page: patch.page ?? 1,
    }));
    setSelectedProductId(null);
  }

  function handleSelectProduct(product: AdminProduct) {
    setSelectedProductId(product.id);
  }

  function handlePageChange(page: number) {
    setFilters((current) => ({ ...current, page }));
  }

  function handleCreateProduct(payload: AdminProductCreatePayload) {
    if (!accessToken || createProductMutation.isPending) {
      return;
    }

    setFeedback(null);
    createProductMutation.mutate(payload);
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionGlobalOnly
        actionCapability="catalog.manage"
        actionLabel="Nuevo producto"
        description="Catalogo maestro de productos vendibles y operativos."
        meta={[pageStatusLabel]}
        onAction={() => {
          setFeedback(null);
          setIsCreating(true);
        }}
        title="Productos"
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminProductsFilters
          filters={filters}
          isBackendConnected={productList.isBackendConnected}
          options={productList.filterOptions}
          onChange={patchFilters}
        />

        <AdminProductsMetricStrip
          metrics={productList.metrics}
          isLoading={productsQuery.isLoading}
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
          description="Captura la identidad y configuracion inicial del producto."
          isOpen={isCreating}
          title="Nuevo producto"
          onClose={() => setIsCreating(false)}
        >
          <AdminProductCreationPanel
            classOptions={productList.filterOptions.classes}
            errorMessage={createErrorMessage}
            isSubmitting={createProductMutation.isPending}
            onClose={() => setIsCreating(false)}
            onSubmit={handleCreateProduct}
          />
        </AdminEntityDrawer>

        <div className="grid min-h-0 min-w-0 flex-1 items-stretch gap-2.5 overflow-hidden xl:grid-cols-[minmax(0,1fr)_minmax(15rem,18rem)]">
          <AdminProductsTable
            backendContract={productList.backendContract}
            errorMessage={listErrorMessage}
            isLoading={productsQuery.isLoading}
            page={productList.page}
            pageSize={productList.pageSize}
            products={productList.items}
            selectedProductId={selectedProductId}
            total={productList.total}
            onPageChange={handlePageChange}
            onSelectProduct={handleSelectProduct}
          />
          <AdminProductsDetailPanel
            errorMessage={detailErrorMessage}
            isLoading={productDetailQuery.isLoading}
            product={detailProduct}
          />
        </div>
      </div>
    </section>
  );
}
