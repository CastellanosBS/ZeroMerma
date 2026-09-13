import { AdminActionButton } from "../../components/AdminActionButton";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminEntityDrawer } from "../../components/AdminEntityDrawer";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminSupplierBackendContract,
  changeAdminSupplierStatus,
  createAdminSupplier,
  fetchAdminSupplierDetail,
  fetchAdminSuppliers,
  updateAdminSupplier,
} from "../api";
import { AdminSupplierDetailPanel } from "../components/AdminSupplierDetailPanel";
import { AdminSupplierFormPanel } from "../components/AdminSupplierFormPanel";
import { AdminSuppliersFilters } from "../components/AdminSuppliersFilters";
import { AdminSuppliersTable } from "../components/AdminSuppliersTable";
import type {
  AdminSupplierDetail,
  AdminSupplierFilterOptions,
  AdminSupplierListFilters,
  AdminSupplierListItem,
  AdminSupplierListResponse,
  AdminSupplierPayload,
  AdminSupplierStatus,
} from "../types";

const defaultFilters: AdminSupplierListFilters = {
  category: "all",
  page: 1,
  pageSize: 25,
  productKind: "all",
  search: "",
  status: "all",
  warningState: "all",
};

const emptyFilterOptions: AdminSupplierFilterOptions = {
  branches: [],
  categories: [],
  productKinds: [],
  products: [],
  statuses: [],
  warningStates: [],
};

const emptySupplierList: AdminSupplierListResponse = {
  backendContract: adminSupplierBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    activeSuppliers: "0",
    blockedSuppliers: "0",
    inactiveSuppliers: "0",
    suppliersWithRecentActivity: "0",
    suppliersWithWarnings: "0",
    suppliersWithoutProducts: "0",
    totalSuppliers: "0",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

function getInitialFilters(): AdminSupplierListFilters {
  if (typeof window === "undefined") {
    return defaultFilters;
  }
  const params = new URLSearchParams(window.location.search);
  return {
    ...defaultFilters,
    branchId: params.get("branchId"),
  };
}

function AdminSupplierMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminSupplierListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    {
      label: "Totales",
      title: "Proveedores totales",
      value: loadingValue ?? metrics.totalSuppliers,
    },
    { label: "Activos", title: "Activos", value: loadingValue ?? metrics.activeSuppliers },
    { label: "Inactivos", title: "Inactivos", value: loadingValue ?? metrics.inactiveSuppliers },
    {
      label: "Advertencias",
      title: "Con advertencias",
      value: loadingValue ?? metrics.suppliersWithWarnings,
    },
    {
      label: "Sin productos",
      title: "Sin productos asociados",
      value: loadingValue ?? metrics.suppliersWithoutProducts,
    },
    {
      label: "Compras recientes",
      title: "Con compras recientes",
      value: loadingValue ?? metrics.suppliersWithRecentActivity,
    },
    { label: "Bloqueados", title: "Bloqueados", value: loadingValue ?? metrics.blockedSuppliers },
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

export function AdminSuppliersPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminSupplierListFilters>(getInitialFilters);
  const [selectedSupplierId, setSelectedSupplierId] = useState<string | null>(null);
  const [editingSupplier, setEditingSupplier] = useState<AdminSupplierDetail | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const suppliersQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminSuppliers(accessToken ?? "", filters),
    queryKey: ["admin", "suppliers", "list", filters],
    retry: false,
  });

  const supplierList = suppliersQuery.data ?? emptySupplierList;
  const selectedSupplierPreview = useMemo(
    () => supplierList.items.find((item) => item.id === selectedSupplierId) ?? null,
    [selectedSupplierId, supplierList.items],
  );

  const supplierDetailQuery = useQuery({
    enabled: Boolean(accessToken && selectedSupplierId),
    queryFn: () => fetchAdminSupplierDetail(accessToken ?? "", selectedSupplierId ?? ""),
    queryKey: ["admin", "suppliers", "detail", selectedSupplierId],
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: (payload: AdminSupplierPayload) => createAdminSupplier(accessToken ?? "", payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo guardar el proveedor."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Proveedor guardado correctamente." });
      setSelectedSupplierId(detail.overview.id);
      setIsFormOpen(false);
      setEditingSupplier(null);
      void queryClient.invalidateQueries({ queryKey: ["admin", "suppliers"] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ payload, supplierId }: { payload: AdminSupplierPayload; supplierId: string }) =>
      updateAdminSupplier(accessToken ?? "", supplierId, payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo actualizar el proveedor."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Proveedor actualizado correctamente." });
      setSelectedSupplierId(detail.overview.id);
      setIsFormOpen(false);
      setEditingSupplier(null);
      void queryClient.invalidateQueries({ queryKey: ["admin", "suppliers"] });
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({ status, supplierId }: { status: AdminSupplierStatus; supplierId: string }) =>
      changeAdminSupplierStatus(accessToken ?? "", supplierId, { notes: null, status }),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo cambiar el estado del proveedor."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Estado del proveedor actualizado." });
      setSelectedSupplierId(detail.overview.id);
      void queryClient.invalidateQueries({ queryKey: ["admin", "suppliers"] });
    },
  });

  const listErrorMessage = suppliersQuery.isError
    ? toBackofficeErrorMessage(suppliersQuery.error, "No se pudieron cargar proveedores.")
    : null;
  const detailErrorMessage = supplierDetailQuery.isError
    ? toBackofficeErrorMessage(
        supplierDetailQuery.error,
        "No se pudo cargar el detalle de proveedor.",
      )
    : null;
  const formErrorMessage =
    (createMutation.isError || updateMutation.isError) && feedback?.tone === "error"
      ? feedback.message
      : null;
  const isSubmitting =
    createMutation.isPending || updateMutation.isPending || statusMutation.isPending;
  const pageStatusLabel = suppliersQuery.isLoading
    ? "Validando API"
    : supplierList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminSupplierListFilters>) {
    setFilters((current) => ({ ...current, ...patch, page: patch.page ?? 1 }));
    setSelectedSupplierId(null);
  }

  function handleSubmit(payload: AdminSupplierPayload) {
    if (!accessToken || isSubmitting) {
      return;
    }
    setFeedback(null);
    if (editingSupplier) {
      updateMutation.mutate({ payload, supplierId: editingSupplier.overview.id });
      return;
    }
    createMutation.mutate(payload);
  }

  function handleChangeStatus(supplierId: string, status: AdminSupplierStatus) {
    if (!accessToken || isSubmitting) {
      return;
    }
    setFeedback(null);
    statusMutation.mutate({ status, supplierId });
  }

  function handleEditCurrent() {
    if (!supplierDetailQuery.data) {
      return;
    }
    setEditingSupplier(supplierDetailQuery.data);
    setIsFormOpen(true);
  }

  function handleOpenProduct(productId: string) {
    window.location.href = `/admin/productos?productId=${productId}`;
  }

  function handleOpenBranch(branchId: string) {
    window.location.href = `/admin/sucursales?branchId=${branchId}`;
  }

  function handleOpenProducts(supplierId: string) {
    setSelectedSupplierId(supplierId);
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionGlobalOnly
        actionCapability="suppliers.manage"
        actionLabel="Nuevo proveedor"
        description="Administra proveedores, contactos, condiciones comerciales, productos surtidos y estado operativo."
        meta={[pageStatusLabel, "Cambios auditables"]}
        onAction={() => {
          setFeedback(null);
          setEditingSupplier(null);
          setIsFormOpen(true);
        }}
        title="Proveedores"
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminSuppliersFilters
          filters={filters}
          isBackendConnected={supplierList.isBackendConnected}
          options={supplierList.filterOptions}
          onChange={patchFilters}
        />
        <AdminSupplierMetricStrip
          isLoading={suppliersQuery.isLoading}
          metrics={supplierList.metrics}
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
          description="Administra datos fiscales, contactos, productos surtidos y sucursales aplicables."
          isOpen={isFormOpen}
          title={editingSupplier ? "Editar proveedor" : "Nuevo proveedor"}
          onClose={() => {
            setIsFormOpen(false);
            setEditingSupplier(null);
          }}
        >
          <AdminSupplierFormPanel
            branchOptions={supplierList.filterOptions.branches}
            categoryOptions={supplierList.filterOptions.categories}
            errorMessage={formErrorMessage}
            initialSupplier={editingSupplier}
            isSubmitting={isSubmitting}
            productOptions={supplierList.filterOptions.products}
            statusOptions={supplierList.filterOptions.statuses}
            onClose={() => {
              setIsFormOpen(false);
              setEditingSupplier(null);
            }}
            onSubmit={handleSubmit}
          />
        </AdminEntityDrawer>

        <div className="grid min-h-0 min-w-0 flex-1 items-stretch gap-2.5 overflow-hidden xl:grid-cols-[minmax(0,1fr)_minmax(15rem,20rem)]">
          <AdminSuppliersTable
            backendContract={supplierList.backendContract}
            errorMessage={listErrorMessage}
            isLoading={suppliersQuery.isLoading}
            page={supplierList.page}
            pageSize={supplierList.pageSize}
            selectedSupplierId={selectedSupplierId}
            suppliers={supplierList.items}
            total={supplierList.total}
            onChangeStatus={handleChangeStatus}
            onOpenProducts={handleOpenProducts}
            onPageChange={(page) => setFilters((current) => ({ ...current, page }))}
            onSelectSupplier={(item: AdminSupplierListItem) => setSelectedSupplierId(item.id)}
          />
          <div className="flex min-h-0 flex-col gap-2.5 overflow-hidden">
            {supplierDetailQuery.data ? (
              <AdminActionButton
                capability="suppliers.manage"
                globalOnly
                className="rounded-[16px] border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700"
                type="button"
                onClick={handleEditCurrent}
              >
                Editar proveedor
              </AdminActionButton>
            ) : null}
            <AdminSupplierDetailPanel
              errorMessage={detailErrorMessage}
              isLoading={supplierDetailQuery.isLoading}
              supplierDetail={supplierDetailQuery.data ?? null}
              supplierPreview={selectedSupplierPreview}
              onOpenBranch={handleOpenBranch}
              onOpenProduct={handleOpenProduct}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
