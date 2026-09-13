import { AdminRowActionsMenu } from "../../components/AdminRowActionsMenu";
import type { AdminSupplierBackendContract, AdminSupplierListItem } from "../types";

interface AdminSuppliersTableProps {
  backendContract: AdminSupplierBackendContract;
  errorMessage?: string | null;
  isLoading: boolean;
  page: number;
  pageSize: number;
  selectedSupplierId?: string | null;
  suppliers: AdminSupplierListItem[];
  total: number;
  onChangeStatus: (supplierId: string, status: AdminSupplierListItem["status"]) => void;
  onOpenProducts: (supplierId: string) => void;
  onPageChange: (page: number) => void;
  onSelectSupplier: (item: AdminSupplierListItem) => void;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusClass(status: string) {
  if (status === "ACTIVE") {
    return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
  }
  if (status === "BLOCKED") {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function statusLabel(status: string) {
  if (status === "ACTIVE") {
    return "Activo";
  }
  if (status === "INACTIVE") {
    return "Inactivo";
  }
  if (status === "BLOCKED") {
    return "Bloqueado";
  }
  return status;
}

function warningLabel(item: AdminSupplierListItem) {
  if (!item.warningState) {
    return "Sin advertencias";
  }
  if (item.warningState === "critical") {
    return "Critico";
  }
  if (item.warningState === "warning") {
    return "Advertencia";
  }
  return "Info";
}

export function AdminSuppliersTable({
  backendContract,
  errorMessage,
  isLoading,
  page,
  pageSize,
  selectedSupplierId,
  suppliers,
  total,
  onChangeStatus,
  onOpenProducts,
  onPageChange,
  onSelectSupplier,
}: AdminSuppliersTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex items-center justify-between border-b border-[var(--ui-color-border)] px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-950">Directorio de proveedores</h2>
          <p className="text-xs text-slate-500">{backendContract.listEndpoint}</p>
        </div>
        <span className="rounded-full bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600">
          {total} proveedores
        </span>
      </div>

      {errorMessage ? (
        <p className="m-3 rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] px-4 py-3 text-sm font-semibold text-[var(--ui-color-danger)]">
          {errorMessage}
        </p>
      ) : null}

      <div className="min-h-0 flex-1 overflow-auto">
        <table className="min-w-[96rem] w-full border-collapse text-sm">
          <thead className="sticky top-0 z-10 bg-slate-50 text-left text-xs uppercase tracking-[0.08em] text-slate-500">
            <tr>
              <th className="px-4 py-3 font-semibold">Nombre / razon social</th>
              <th className="px-4 py-3 font-semibold">Nombre comercial</th>
              <th className="px-4 py-3 font-semibold">RFC / Tax ID</th>
              <th className="px-4 py-3 font-semibold">Categoria</th>
              <th className="px-4 py-3 font-semibold">Estado</th>
              <th className="px-4 py-3 font-semibold">Contacto principal</th>
              <th className="px-4 py-3 font-semibold">Telefono / Email</th>
              <th className="px-4 py-3 font-semibold">Productos</th>
              <th className="px-4 py-3 font-semibold">Sucursales</th>
              <th className="px-4 py-3 font-semibold">Condiciones</th>
              <th className="px-4 py-3 font-semibold">Ultima actualizacion</th>
              <th className="px-4 py-3 font-semibold">Advertencias</th>
              <th className="px-4 py-3 font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {isLoading ? (
              <tr>
                <td
                  className="px-4 py-8 text-center text-sm font-semibold text-slate-500"
                  colSpan={13}
                >
                  Cargando proveedores.
                </td>
              </tr>
            ) : suppliers.length === 0 ? (
              <tr>
                <td
                  className="px-4 py-8 text-center text-sm font-semibold text-slate-500"
                  colSpan={13}
                >
                  No hay proveedores registrados. Crea el primer proveedor para iniciar la gestion
                  de compras.
                </td>
              </tr>
            ) : (
              suppliers.map((item) => (
                <tr
                  className={`cursor-pointer hover:bg-slate-50 ${
                    selectedSupplierId === item.id
                      ? "bg-[var(--ui-color-primary-soft)]"
                      : "bg-white"
                  }`}
                  key={item.id}
                  onClick={() => onSelectSupplier(item)}
                >
                  <td className="px-4 py-3">
                    <div className="font-semibold text-slate-950">{item.legalName}</div>
                    <div className="text-xs text-slate-500">{item.code}</div>
                  </td>
                  <td className="px-4 py-3 text-slate-700">
                    {item.commercialName ?? "No registrado"}
                  </td>
                  <td className="px-4 py-3 text-slate-700">{item.taxId ?? "No registrado"}</td>
                  <td className="px-4 py-3 text-slate-700">{item.category}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${statusClass(item.status)}`}
                    >
                      {statusLabel(item.status)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-700">
                    {item.primaryContactName ?? "Sin contacto"}
                  </td>
                  <td className="px-4 py-3 text-slate-700">
                    <div>{item.primaryContactPhone ?? "Sin telefono"}</div>
                    <div className="text-xs text-slate-500">
                      {item.primaryContactEmail ?? "Sin email"}
                    </div>
                  </td>
                  <td className="px-4 py-3 font-semibold text-slate-950">{item.productCount}</td>
                  <td className="px-4 py-3 font-semibold text-slate-950">{item.branchCount}</td>
                  <td className="px-4 py-3 text-slate-700">{item.termsSummary}</td>
                  <td className="px-4 py-3 text-slate-600">{formatDate(item.updatedAt)}</td>
                  <td className="px-4 py-3 text-slate-600">{warningLabel(item)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        className="rounded-full border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:border-[var(--ui-color-primary)]"
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          onSelectSupplier(item);
                        }}
                      >
                        Ver
                      </button>
                      <div onClick={(event) => event.stopPropagation()}>
                        <AdminRowActionsMenu
                          actions={[
                            { label: "Ver productos", onSelect: () => onOpenProducts(item.id) },
                            {
                              label: "Copiar identificador",
                              onSelect: () => {
                                void navigator.clipboard?.writeText(item.taxId ?? item.code);
                              },
                            },
                            {
                              destructive: item.status === "ACTIVE",
                              capability: "suppliers.manage",
                              globalOnly: true,
                              label: item.status === "ACTIVE" ? "Desactivar" : "Activar",
                              onSelect: () =>
                                onChangeStatus(
                                  item.id,
                                  item.status === "ACTIVE" ? "INACTIVE" : "ACTIVE",
                                ),
                            },
                            ...(item.status !== "BLOCKED"
                              ? [
                                  {
                                    destructive: true,
                                    capability: "suppliers.manage" as const,
                                    globalOnly: true,
                                    label: "Bloquear",
                                    onSelect: () => onChangeStatus(item.id, "BLOCKED" as const),
                                  },
                                ]
                              : []),
                          ]}
                          label={`Acciones para ${item.legalName}`}
                        />
                      </div>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between border-t border-[var(--ui-color-border)] px-4 py-3 text-xs text-slate-600">
        <span>
          Pagina {page} de {totalPages}
        </span>
        <div className="flex gap-2">
          <button
            className="rounded-full border border-slate-200 px-3 py-1.5 font-semibold disabled:opacity-50"
            disabled={page <= 1}
            type="button"
            onClick={() => onPageChange(page - 1)}
          >
            Anterior
          </button>
          <button
            className="rounded-full border border-slate-200 px-3 py-1.5 font-semibold disabled:opacity-50"
            disabled={page >= totalPages}
            type="button"
            onClick={() => onPageChange(page + 1)}
          >
            Siguiente
          </button>
        </div>
      </div>
    </section>
  );
}
