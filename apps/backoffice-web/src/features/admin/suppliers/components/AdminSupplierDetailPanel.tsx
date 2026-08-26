import type { ReactNode } from "react";

import type { AdminSupplierDetail, AdminSupplierListItem } from "../types";

interface AdminSupplierDetailPanelProps {
  errorMessage?: string | null;
  isLoading: boolean;
  supplierDetail?: AdminSupplierDetail | null;
  supplierPreview?: AdminSupplierListItem | null;
  onOpenProduct: (productId: string) => void;
  onOpenBranch: (branchId: string) => void;
}

function formatDate(value?: string | null) {
  if (!value) {
    return "No disponible";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function toneClass(tone?: string | null) {
  if (tone === "critical") {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  if (tone === "warning") {
    return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
  }
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function DetailBlock({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{title}</h3>
      {children}
    </section>
  );
}

export function AdminSupplierDetailPanel({
  errorMessage,
  isLoading,
  supplierDetail,
  supplierPreview,
  onOpenBranch,
  onOpenProduct,
}: AdminSupplierDetailPanelProps) {
  if (!supplierPreview && !supplierDetail) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col justify-center rounded-[20px] border border-dashed border-slate-200 bg-slate-50 p-5 text-sm font-semibold text-slate-500">
        Selecciona un proveedor para revisar contactos, condiciones comerciales y productos asociados.
      </aside>
    );
  }

  if (isLoading) {
    return (
      <aside className="rounded-[20px] border border-[var(--ui-color-border)] bg-white p-4 text-sm font-semibold text-slate-500">
        Cargando detalle de proveedor.
      </aside>
    );
  }

  if (errorMessage) {
    return (
      <aside className="rounded-[20px] border border-rose-200 bg-[var(--ui-color-danger-soft)] p-4 text-sm font-semibold text-[var(--ui-color-danger)]">
        {errorMessage}
      </aside>
    );
  }

  if (!supplierDetail) {
    return null;
  }

  const overview = supplierDetail.overview;

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50">
      <div className="border-b border-[var(--ui-color-border)] bg-white p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Detalle de proveedor</p>
            <h2 className="truncate text-lg font-semibold text-slate-950">{overview.legalName}</h2>
            <p className="text-sm text-slate-600">
              {overview.code} - {overview.commercialName ?? "Sin nombre comercial"}
            </p>
          </div>
          <span className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-semibold ${toneClass(overview.readinessState)}`}>
            {overview.status}
          </span>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-2.5 overflow-auto p-3">
        <DetailBlock title="Resumen">
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <dt className="text-xs text-slate-500">Categoria</dt>
              <dd className="font-semibold text-slate-950">{overview.category}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">RFC / Tax ID</dt>
              <dd className="font-semibold text-slate-950">{overview.taxId ?? "No registrado"}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Creado</dt>
              <dd className="font-semibold text-slate-950">{formatDate(overview.createdAt)}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Actualizado</dt>
              <dd className="font-semibold text-slate-950">{formatDate(overview.updatedAt)}</dd>
            </div>
          </dl>
        </DetailBlock>

        <DetailBlock title="Fiscal / legal">
          <div className="space-y-2 text-sm text-slate-700">
            <p className="font-semibold text-slate-950">{supplierDetail.fiscalLegal.legalName}</p>
            <p>{supplierDetail.fiscalLegal.fiscalAddress ?? "Direccion fiscal no registrada."}</p>
            <p>{supplierDetail.fiscalLegal.paymentFiscalEmail ?? "Email fiscal no registrado."}</p>
            <p className="rounded-xl bg-slate-50 p-2">{supplierDetail.fiscalLegal.notes ?? "Sin notas."}</p>
          </div>
        </DetailBlock>

        <DetailBlock title="Contactos">
          {supplierDetail.contacts.length === 0 ? (
            <p className="text-sm font-semibold text-slate-500">Este proveedor no tiene contactos registrados.</p>
          ) : (
            <div className="space-y-2">
              {supplierDetail.contacts.map((contact) => (
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-2 text-sm" key={contact.id}>
                  <p className="font-semibold text-slate-950">
                    {contact.name} {contact.isPrimary ? "(principal)" : ""}
                  </p>
                  <p className="text-xs text-slate-500">
                    {contact.role ?? "Sin rol"} - {contact.phone ?? contact.whatsapp ?? "Sin telefono"} - {contact.email ?? "Sin email"}
                  </p>
                </div>
              ))}
            </div>
          )}
        </DetailBlock>

        <DetailBlock title="Condiciones comerciales">
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <dt className="text-xs text-slate-500">Terminos</dt>
              <dd className="font-semibold text-slate-950">{supplierDetail.commercialTerms.summary}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Moneda</dt>
              <dd className="font-semibold text-slate-950">{supplierDetail.commercialTerms.defaultCurrency}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Pedido minimo</dt>
              <dd className="font-semibold text-slate-950">{supplierDetail.commercialTerms.minimumOrderAmount ?? "No definido"}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Lead time</dt>
              <dd className="font-semibold text-slate-950">{supplierDetail.commercialTerms.leadTimeDays} dias</dd>
            </div>
          </dl>
        </DetailBlock>

        <DetailBlock title="Productos surtidos">
          {supplierDetail.productAssociations.length === 0 ? (
            <p className="text-sm font-semibold text-slate-500">Este proveedor no tiene productos o insumos asociados.</p>
          ) : (
            <div className="space-y-2">
              {supplierDetail.productAssociations.map((product) => (
                <button
                  className="w-full rounded-xl border border-slate-100 bg-slate-50 p-2 text-left text-sm hover:border-[var(--ui-color-primary)]"
                  key={product.id}
                  type="button"
                  onClick={() => onOpenProduct(product.productId)}
                >
                  <p className="font-semibold text-slate-950">{product.productName}</p>
                  <p className="text-xs text-slate-500">
                    {product.productCode} - {product.productKind} - {product.purchaseUom} - {product.isActive ? "Activo" : "Inactivo"}
                  </p>
                </button>
              ))}
            </div>
          )}
        </DetailBlock>

        <DetailBlock title="Sucursales aplicables">
          {supplierDetail.branchApplicability.length === 0 ? (
            <p className="text-sm font-semibold text-slate-500">Este proveedor no tiene sucursales asociadas.</p>
          ) : (
            <div className="space-y-2">
              {supplierDetail.branchApplicability.map((branch) => (
                <button
                  className="w-full rounded-xl border border-slate-100 bg-slate-50 p-2 text-left text-sm hover:border-[var(--ui-color-primary)]"
                  key={branch.branchId}
                  type="button"
                  onClick={() => onOpenBranch(branch.branchId)}
                >
                  <p className="font-semibold text-slate-950">{branch.branchName}</p>
                  <p className="text-xs text-slate-500">
                    {branch.branchCode} - {branch.branchStatus} - {branch.isActive ? "Aplicable" : "Inactiva"}
                  </p>
                </button>
              ))}
            </div>
          )}
        </DetailBlock>

        <DetailBlock title="Actividad operacional">
          <p className="text-sm font-semibold text-slate-500">{supplierDetail.operationalActivity.notes}</p>
        </DetailBlock>

        <DetailBlock title="Advertencias">
          {supplierDetail.warnings.length === 0 ? (
            <p className="text-sm font-semibold text-slate-500">No hay advertencias para este proveedor.</p>
          ) : (
            <div className="space-y-2">
              {supplierDetail.warnings.map((warning) => (
                <p className={`rounded-xl border px-3 py-2 text-sm font-semibold ${toneClass(warning.severity)}`} key={warning.code}>
                  {warning.message}
                </p>
              ))}
            </div>
          )}
        </DetailBlock>

        <DetailBlock title="Documentos relacionados">
          {supplierDetail.relatedDocuments.length === 0 ? (
            <p className="text-sm font-semibold text-slate-500">Este proveedor no tiene documentos relacionados.</p>
          ) : (
            <div className="space-y-2">
              {supplierDetail.relatedDocuments.map((document) => (
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-2 text-sm" key={`${document.documentType}-${document.documentId}`}>
                  <p className="font-semibold text-slate-950">{document.documentType}</p>
                  <p className="text-xs text-slate-500">
                    {document.folio} - {document.status}
                  </p>
                </div>
              ))}
            </div>
          )}
        </DetailBlock>
      </div>
    </aside>
  );
}
