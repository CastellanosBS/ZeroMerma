import { AdminActionButton } from "../../components/AdminActionButton";
import { useMemo, useState } from "react";
import type { FormEvent } from "react";

import type {
  AdminBranchCreatePayload,
  AdminBranchDetail,
  AdminBranchFilterOption,
  AdminBranchUpdatePayload,
} from "../types";

const inputClassName =
  "h-10 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500";

function normalizeOptional(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

interface AdminBranchFormPanelProps {
  branchDetail?: AdminBranchDetail | null;
  brandOptions: AdminBranchFilterOption[];
  errorMessage?: string | null;
  isSubmitting?: boolean;
  onClose: () => void;
  onSubmit: (payload: AdminBranchCreatePayload | AdminBranchUpdatePayload) => void;
}

export function AdminBranchFormPanel({
  branchDetail,
  brandOptions,
  errorMessage,
  isSubmitting = false,
  onClose,
  onSubmit,
}: AdminBranchFormPanelProps) {
  const isEdit = Boolean(branchDetail);
  const [brandId, setBrandId] = useState(
    branchDetail?.overview.brandId ?? brandOptions[0]?.id ?? "",
  );
  const [code, setCode] = useState(branchDetail?.overview.code ?? "");
  const [name, setName] = useState(branchDetail?.overview.name ?? "");
  const [timezone, setTimezone] = useState(branchDetail?.overview.timezone ?? "");
  const [isActive, setIsActive] = useState(branchDetail?.overview.status !== "inactive");
  const [addressLine, setAddressLine] = useState(branchDetail?.locationContact.addressLine ?? "");
  const [city, setCity] = useState(branchDetail?.locationContact.city ?? "");
  const [state, setState] = useState(branchDetail?.locationContact.state ?? "");
  const [country, setCountry] = useState(branchDetail?.locationContact.country ?? "");
  const [postalCode, setPostalCode] = useState(branchDetail?.locationContact.postalCode ?? "");
  const [phone, setPhone] = useState(branchDetail?.locationContact.phone ?? "");
  const [contactEmail, setContactEmail] = useState(
    branchDetail?.locationContact.contactEmail ?? "",
  );
  const [notes, setNotes] = useState(branchDetail?.locationContact.notes ?? "");
  const [localError, setLocalError] = useState<string | null>(null);

  const title = isEdit ? "Editar sucursal" : "Nueva sucursal";
  const selectedBrandLabel = useMemo(
    () => brandOptions.find((option) => option.id === brandId)?.label ?? "Marca no seleccionada",
    [brandId, brandOptions],
  );

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLocalError(null);

    if (!brandId) {
      setLocalError("Selecciona una marca real para la sucursal.");
      return;
    }
    if (!code.trim()) {
      setLocalError("El codigo de sucursal es obligatorio.");
      return;
    }
    if (!name.trim()) {
      setLocalError("El nombre de sucursal es obligatorio.");
      return;
    }
    if (!timezone.trim()) {
      setLocalError("La zona horaria es obligatoria.");
      return;
    }

    onSubmit({
      addressLine: normalizeOptional(addressLine),
      brandId,
      city: normalizeOptional(city),
      code: code.trim(),
      contactEmail: normalizeOptional(contactEmail),
      country: normalizeOptional(country),
      isActive,
      name: name.trim(),
      notes: normalizeOptional(notes),
      phone: normalizeOptional(phone),
      postalCode: normalizeOptional(postalCode),
      state: normalizeOptional(state),
      timezone: timezone.trim(),
    });
  }

  return (
    <form
      className="grid min-w-0 gap-3 rounded-[20px] border border-[var(--ui-color-border)] bg-white p-3"
      onSubmit={handleSubmit}
    >
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">{title}</h3>
          <p className="truncate text-xs text-slate-500" title={selectedBrandLabel}>
            Configuracion base de la sucursal - {selectedBrandLabel}
          </p>
        </div>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={onClose}
        >
          Cerrar
        </button>
      </div>

      {(localError || errorMessage) && (
        <p className="rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-danger)]">
          {localError ?? errorMessage}
        </p>
      )}

      <div className="grid min-w-0 gap-2 lg:grid-cols-4">
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Marca
          <select
            className={inputClassName}
            value={brandId}
            onChange={(event) => setBrandId(event.target.value)}
          >
            {brandOptions.length === 0 ? <option value="">Marcas pendientes de API</option> : null}
            {brandOptions.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Codigo
          <input
            className={inputClassName}
            value={code}
            onChange={(event) => setCode(event.target.value)}
          />
        </label>
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500 lg:col-span-2">
          Nombre
          <input
            className={inputClassName}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Zona horaria
          <input
            className={inputClassName}
            placeholder="America/Hermosillo"
            value={timezone}
            onChange={(event) => setTimezone(event.target.value)}
          />
        </label>
        <label className="flex min-w-0 items-center gap-2 rounded-2xl border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700">
          <input
            checked={isActive}
            type="checkbox"
            onChange={(event) => setIsActive(event.target.checked)}
          />
          Activa
        </label>
      </div>

      <div className="grid min-w-0 gap-2 lg:grid-cols-4">
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500 lg:col-span-2">
          Direccion
          <input
            className={inputClassName}
            value={addressLine}
            onChange={(event) => setAddressLine(event.target.value)}
          />
        </label>
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Ciudad
          <input
            className={inputClassName}
            value={city}
            onChange={(event) => setCity(event.target.value)}
          />
        </label>
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Estado
          <input
            className={inputClassName}
            value={state}
            onChange={(event) => setState(event.target.value)}
          />
        </label>
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Pais
          <input
            className={inputClassName}
            value={country}
            onChange={(event) => setCountry(event.target.value)}
          />
        </label>
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Codigo postal
          <input
            className={inputClassName}
            value={postalCode}
            onChange={(event) => setPostalCode(event.target.value)}
          />
        </label>
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Telefono
          <input
            className={inputClassName}
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
          />
        </label>
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Correo
          <input
            className={inputClassName}
            value={contactEmail}
            onChange={(event) => setContactEmail(event.target.value)}
          />
        </label>
      </div>

      <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
        Notas
        <textarea
          className="min-h-[4.5rem] w-full min-w-0 resize-none rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
        />
      </label>

      <div className="flex min-w-0 flex-wrap justify-end gap-2 border-t border-[var(--ui-color-border)] pt-3">
        <button
          className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={onClose}
        >
          Cancelar
        </button>
        <AdminActionButton
          capability="branches.manage"
          globalOnly={!isEdit}
          branchIds={branchDetail ? [branchDetail.overview.id] : []}
          className="rounded-2xl bg-[var(--ui-color-primary)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[var(--ui-color-primary-strong)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "Guardando" : "Guardar sucursal"}
        </AdminActionButton>
      </div>
    </form>
  );
}
