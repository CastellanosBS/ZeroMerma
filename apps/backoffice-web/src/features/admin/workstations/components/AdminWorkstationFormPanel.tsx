import { AdminActionButton } from "../../components/AdminActionButton";
import { useMemo, useState } from "react";
import type { FormEvent } from "react";

import type {
  AdminWorkstationCreatePayload,
  AdminWorkstationDetail,
  AdminWorkstationFilterOption,
  AdminWorkstationUpdatePayload,
} from "../types";

const inputClassName =
  "h-10 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500";

interface AdminWorkstationFormPanelProps {
  branchOptions: AdminWorkstationFilterOption[];
  errorMessage?: string | null;
  isSubmitting?: boolean;
  onClose: () => void;
  onSubmit: (payload: AdminWorkstationCreatePayload | AdminWorkstationUpdatePayload) => void;
  workstationDetail?: AdminWorkstationDetail | null;
}

export function AdminWorkstationFormPanel({
  branchOptions,
  errorMessage,
  isSubmitting = false,
  onClose,
  onSubmit,
  workstationDetail,
}: AdminWorkstationFormPanelProps) {
  const isEdit = Boolean(workstationDetail);
  const [branchId, setBranchId] = useState(
    workstationDetail?.branchRelationship.branchId ?? branchOptions[0]?.id ?? "",
  );
  const [code, setCode] = useState(workstationDetail?.overview.code ?? "");
  const [name, setName] = useState(workstationDetail?.overview.name ?? "");
  const [isActive, setIsActive] = useState(workstationDetail?.overview.status !== "inactive");
  const [localError, setLocalError] = useState<string | null>(null);

  const title = isEdit ? "Editar estacion" : "Nueva estacion";
  const selectedBranchLabel = useMemo(
    () =>
      branchOptions.find((option) => option.id === branchId)?.label ?? "Sucursal no seleccionada",
    [branchId, branchOptions],
  );

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLocalError(null);

    if (!branchId) {
      setLocalError("Selecciona una sucursal para asociar esta estacion.");
      return;
    }
    if (!code.trim()) {
      setLocalError("El codigo de estacion es obligatorio.");
      return;
    }
    if (!name.trim()) {
      setLocalError("El nombre de estacion es obligatorio.");
      return;
    }

    onSubmit({
      branchId,
      code: code.trim(),
      isActive,
      name: name.trim(),
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
          <p className="truncate text-xs text-slate-500" title={selectedBranchLabel}>
            Codigo operativo para POS - {selectedBranchLabel}
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

      <div className="grid min-w-0 gap-2 lg:grid-cols-[minmax(12rem,1fr)_minmax(9rem,0.7fr)_minmax(14rem,1.1fr)_auto]">
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Sucursal
          <select
            className={inputClassName}
            value={branchId}
            onChange={(event) => setBranchId(event.target.value)}
          >
            {branchOptions.length === 0 ? (
              <option value="">Sucursales pendientes de API</option>
            ) : null}
            {branchOptions.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Codigo
          <input
            className={`${inputClassName} font-mono`}
            placeholder="POS-01"
            value={code}
            onChange={(event) => setCode(event.target.value)}
          />
        </label>
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Nombre
          <input
            className={inputClassName}
            placeholder="Caja principal"
            value={name}
            onChange={(event) => setName(event.target.value)}
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

      <p className="rounded-[16px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
        El codigo se usa para que POS resuelva sucursal y estacion. Si cambias un codigo existente,
        verifica la configuracion del dispositivo POS correspondiente.
      </p>

      <div className="flex min-w-0 flex-wrap justify-end gap-2 border-t border-[var(--ui-color-border)] pt-3">
        <button
          className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={onClose}
        >
          Cancelar
        </button>
        <AdminActionButton
          capability="workstations.manage"
          branchIds={[branchId]}
          className="rounded-2xl bg-[var(--ui-color-primary)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[var(--ui-color-primary-strong)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "Guardando" : "Guardar estacion"}
        </AdminActionButton>
      </div>
    </form>
  );
}
