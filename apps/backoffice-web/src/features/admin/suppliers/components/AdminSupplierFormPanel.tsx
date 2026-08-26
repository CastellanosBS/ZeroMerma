import { useEffect, useMemo, useState } from "react";

import type {
  AdminSupplierDetail,
  AdminSupplierFilterOption,
  AdminSupplierPayload,
  AdminSupplierProductPayload,
  AdminSupplierStatus,
} from "../types";

interface AdminSupplierFormPanelProps {
  branchOptions: AdminSupplierFilterOption[];
  categoryOptions: AdminSupplierFilterOption[];
  errorMessage?: string | null;
  initialSupplier?: AdminSupplierDetail | null;
  isSubmitting: boolean;
  productOptions: AdminSupplierFilterOption[];
  statusOptions: AdminSupplierFilterOption[];
  onClose: () => void;
  onSubmit: (payload: AdminSupplierPayload) => void;
}

function selectedIdsFromDetail(initialSupplier?: AdminSupplierDetail | null) {
  return {
    branchIds: initialSupplier?.branchApplicability.filter((branch) => branch.isActive).map((branch) => branch.branchId) ?? [],
    productIds: initialSupplier?.productAssociations.filter((product) => product.isActive).map((product) => product.productId) ?? [],
  };
}

export function AdminSupplierFormPanel({
  branchOptions,
  categoryOptions,
  errorMessage,
  initialSupplier,
  isSubmitting,
  productOptions,
  statusOptions,
  onClose,
  onSubmit,
}: AdminSupplierFormPanelProps) {
  const selectedIds = useMemo(() => selectedIdsFromDetail(initialSupplier), [initialSupplier]);
  const [branchIds, setBranchIds] = useState<string[]>(selectedIds.branchIds);
  const [category, setCategory] = useState(initialSupplier?.overview.category ?? "OTHER");
  const [code, setCode] = useState(initialSupplier?.overview.code ?? "");
  const [commercialName, setCommercialName] = useState(initialSupplier?.overview.commercialName ?? "");
  const [contactEmail, setContactEmail] = useState(initialSupplier?.contacts[0]?.email ?? "");
  const [contactName, setContactName] = useState(initialSupplier?.contacts[0]?.name ?? "");
  const [contactPhone, setContactPhone] = useState(initialSupplier?.contacts[0]?.phone ?? "");
  const [creditDays, setCreditDays] = useState(String(initialSupplier?.commercialTerms.creditDays ?? 0));
  const [fiscalEmail, setFiscalEmail] = useState(initialSupplier?.fiscalLegal.paymentFiscalEmail ?? "");
  const [leadTimeDays, setLeadTimeDays] = useState(String(initialSupplier?.commercialTerms.leadTimeDays ?? 0));
  const [legalName, setLegalName] = useState(initialSupplier?.overview.legalName ?? "");
  const [minimumOrderAmount, setMinimumOrderAmount] = useState(initialSupplier?.commercialTerms.minimumOrderAmount ?? "");
  const [notes, setNotes] = useState(initialSupplier?.fiscalLegal.notes ?? "");
  const [paymentTermsType, setPaymentTermsType] = useState(initialSupplier?.commercialTerms.paymentTermsType ?? "CASH");
  const [productIds, setProductIds] = useState<string[]>(selectedIds.productIds);
  const [status, setStatus] = useState<AdminSupplierStatus>(initialSupplier?.overview.status ?? "ACTIVE");
  const [taxId, setTaxId] = useState(initialSupplier?.overview.taxId ?? "");
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  useEffect(() => {
    const nextSelectedIds = selectedIdsFromDetail(initialSupplier);
    setBranchIds(nextSelectedIds.branchIds);
    setCategory(initialSupplier?.overview.category ?? "OTHER");
    setCode(initialSupplier?.overview.code ?? "");
    setCommercialName(initialSupplier?.overview.commercialName ?? "");
    setContactEmail(initialSupplier?.contacts[0]?.email ?? "");
    setContactName(initialSupplier?.contacts[0]?.name ?? "");
    setContactPhone(initialSupplier?.contacts[0]?.phone ?? "");
    setCreditDays(String(initialSupplier?.commercialTerms.creditDays ?? 0));
    setFiscalEmail(initialSupplier?.fiscalLegal.paymentFiscalEmail ?? "");
    setLeadTimeDays(String(initialSupplier?.commercialTerms.leadTimeDays ?? 0));
    setLegalName(initialSupplier?.overview.legalName ?? "");
    setMinimumOrderAmount(initialSupplier?.commercialTerms.minimumOrderAmount ?? "");
    setNotes(initialSupplier?.fiscalLegal.notes ?? "");
    setPaymentTermsType(initialSupplier?.commercialTerms.paymentTermsType ?? "CASH");
    setProductIds(nextSelectedIds.productIds);
    setStatus(initialSupplier?.overview.status ?? "ACTIVE");
    setTaxId(initialSupplier?.overview.taxId ?? "");
  }, [initialSupplier]);

  function toggleSelection(value: string, current: string[], setter: (next: string[]) => void) {
    setter(current.includes(value) ? current.filter((item) => item !== value) : [...current, value]);
  }

  function handleSubmit() {
    if (!legalName.trim()) {
      setValidationMessage("El nombre o razon social es requerido.");
      return;
    }
    if (contactEmail && !contactEmail.includes("@")) {
      setValidationMessage("El email de contacto no es valido.");
      return;
    }
    if (fiscalEmail && !fiscalEmail.includes("@")) {
      setValidationMessage("El email fiscal no es valido.");
      return;
    }
    if (Number(creditDays) < 0 || Number(leadTimeDays) < 0 || Number(minimumOrderAmount || 0) < 0) {
      setValidationMessage("Los dias y montos no pueden ser negativos.");
      return;
    }

    const secondaryContacts =
      initialSupplier?.contacts.slice(1).map((contact) => ({
        email: contact.email,
        isPrimary: contact.isPrimary,
        name: contact.name,
        notes: contact.notes,
        phone: contact.phone,
        role: contact.role,
        whatsapp: contact.whatsapp,
      })) ?? [];
    const contacts = contactName.trim()
      ? [
          {
            email: contactEmail.trim() || null,
            isPrimary: true,
            name: contactName.trim(),
            phone: contactPhone.trim() || null,
          },
          ...secondaryContacts,
        ]
      : secondaryContacts;
    const productRelations: AdminSupplierProductPayload[] = productIds.map((productId) => ({
      productId,
    }));

    setValidationMessage(null);
    onSubmit({
      branchIds,
      category,
      code: code.trim() || null,
      commercialName: commercialName.trim() || null,
      contacts,
      creditDays: Number(creditDays || 0),
      defaultCurrency: "MXN",
      fiscalAddress: null,
      fiscalRegime: null,
      leadTimeDays: Number(leadTimeDays || 0),
      legalName: legalName.trim(),
      minimumOrderAmount: minimumOrderAmount.trim() || null,
      notes: notes.trim() || null,
      paymentFiscalEmail: fiscalEmail.trim() || null,
      paymentTermsType,
      productRelations,
      purchaseNotes: null,
      status,
      taxId: taxId.trim() || null,
    });
  }

  return (
    <section className="rounded-[20px] border border-[var(--ui-color-border)] bg-white p-4 shadow-[var(--ui-shadow-subtle)]">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            {initialSupplier ? "Editar proveedor" : "Nuevo proveedor"}
          </p>
          <h2 className="text-lg font-semibold text-slate-950">Datos maestros y preparacion de compras</h2>
          <p className="text-sm text-slate-600">Los cambios se persisten en backend y quedan auditados.</p>
        </div>
        <button className="rounded-full border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700" type="button" onClick={onClose}>
          Cerrar
        </button>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <label className="flex flex-col gap-1 xl:col-span-2">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Razon social</span>
          <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm" value={legalName} onChange={(event) => setLegalName(event.target.value)} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Codigo</span>
          <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm" placeholder="Autogenerado si queda vacio" value={code} onChange={(event) => setCode(event.target.value)} />
        </label>
        <label className="flex flex-col gap-1 xl:col-span-2">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Nombre comercial</span>
          <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm" value={commercialName} onChange={(event) => setCommercialName(event.target.value)} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">RFC / Tax ID</span>
          <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm" value={taxId} onChange={(event) => setTaxId(event.target.value)} />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Categoria</span>
          <select className="rounded-xl border border-slate-200 px-3 py-2 text-sm" value={category} onChange={(event) => setCategory(event.target.value)}>
            {categoryOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Estado</span>
          <select className="rounded-xl border border-slate-200 px-3 py-2 text-sm" value={status} onChange={(event) => setStatus(event.target.value as AdminSupplierStatus)}>
            {statusOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 xl:col-span-2">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Contacto principal</span>
          <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm" value={contactName} onChange={(event) => setContactName(event.target.value)} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Telefono</span>
          <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm" value={contactPhone} onChange={(event) => setContactPhone(event.target.value)} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Email</span>
          <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm" value={contactEmail} onChange={(event) => setContactEmail(event.target.value)} />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Terminos</span>
          <select className="rounded-xl border border-slate-200 px-3 py-2 text-sm" value={paymentTermsType} onChange={(event) => setPaymentTermsType(event.target.value)}>
            <option value="CASH">Contado</option>
            <option value="CREDIT">Credito</option>
            <option value="TRANSFER">Transferencia</option>
            <option value="MIXED">Mixto</option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Dias credito</span>
          <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm" min="0" type="number" value={creditDays} onChange={(event) => setCreditDays(event.target.value)} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Lead time</span>
          <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm" min="0" type="number" value={leadTimeDays} onChange={(event) => setLeadTimeDays(event.target.value)} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Pedido minimo</span>
          <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm" min="0" step="0.01" type="number" value={minimumOrderAmount} onChange={(event) => setMinimumOrderAmount(event.target.value)} />
        </label>
        <label className="flex flex-col gap-1 xl:col-span-2">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Email fiscal</span>
          <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm" value={fiscalEmail} onChange={(event) => setFiscalEmail(event.target.value)} />
        </label>

        <fieldset className="rounded-xl border border-slate-200 p-3 xl:col-span-3">
          <legend className="px-1 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Productos surtidos</legend>
          <div className="grid gap-2 sm:grid-cols-2">
            {productOptions.map((option) => (
              <label className="flex items-center gap-2 text-sm text-slate-700" key={option.id}>
                <input checked={productIds.includes(option.id)} type="checkbox" onChange={() => toggleSelection(option.id, productIds, setProductIds)} />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="rounded-xl border border-slate-200 p-3 xl:col-span-3">
          <legend className="px-1 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Sucursales aplicables</legend>
          <div className="grid gap-2 sm:grid-cols-2">
            {branchOptions.map((option) => (
              <label className="flex items-center gap-2 text-sm text-slate-700" key={option.id}>
                <input checked={branchIds.includes(option.id)} type="checkbox" onChange={() => toggleSelection(option.id, branchIds, setBranchIds)} />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <label className="flex flex-col gap-1 xl:col-span-6">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Notas</span>
          <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm" value={notes} onChange={(event) => setNotes(event.target.value)} />
        </label>
      </div>

      {validationMessage || errorMessage ? (
        <p className="mt-3 rounded-xl border border-rose-200 bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-danger)]">
          {validationMessage ?? errorMessage}
        </p>
      ) : null}

      <div className="mt-4 flex justify-end gap-2">
        <button className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700" disabled={isSubmitting} type="button" onClick={onClose}>
          Cancelar
        </button>
        <button className="rounded-xl bg-[var(--ui-color-primary)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={isSubmitting} type="button" onClick={handleSubmit}>
          Guardar proveedor
        </button>
      </div>
    </section>
  );
}
