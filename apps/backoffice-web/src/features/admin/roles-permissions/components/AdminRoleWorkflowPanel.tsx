import { useMemo, useState } from "react";

import type {
  AdminPermissionGroup,
  AdminRoleCreatePayload,
  AdminRoleDetail,
  AdminRoleSurface,
  AdminRoleUpdatePayload,
} from "../types";

type WorkflowMode = "create" | "edit";

interface AdminRoleWorkflowPanelProps {
  detail: AdminRoleDetail | null;
  errorMessage?: string | null;
  isSubmitting?: boolean;
  mode: WorkflowMode;
  permissionGroups: AdminPermissionGroup[];
  sensitivePermissionCodes: string[];
  onCancel: () => void;
  onCreate: (payload: AdminRoleCreatePayload) => void;
  onUpdate: (roleId: string, payload: AdminRoleUpdatePayload) => void;
}

function fieldClass() {
  return "h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-700 placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]";
}

function toSurfaces(posEnabled: boolean, backofficeEnabled: boolean): AdminRoleSurface[] {
  return [
    ...(posEnabled ? (["POS"] as const) : []),
    ...(backofficeEnabled ? (["BACKOFFICE"] as const) : []),
  ];
}

export function AdminRoleWorkflowPanel({
  detail,
  errorMessage,
  isSubmitting = false,
  mode,
  permissionGroups,
  sensitivePermissionCodes,
  onCancel,
  onCreate,
  onUpdate,
}: AdminRoleWorkflowPanelProps) {
  const isEdit = mode === "edit" && detail !== null;
  const selectedCodesFromDetail = useMemo(() => {
    if (!detail) {
      return [];
    }
    return detail.permissionMatrix.flatMap((group) =>
      group.permissions
        .filter((permission) => permission.isEnabled)
        .map((permission) => permission.code),
    );
  }, [detail]);
  const initialSurfaces = detail?.accessSurfaces.surfaces ?? ["BACKOFFICE"];
  const [code, setCode] = useState(detail?.overview.code ?? "");
  const [name, setName] = useState(detail?.overview.name ?? "");
  const [description, setDescription] = useState(detail?.overview.description ?? "");
  const [posEnabled, setPosEnabled] = useState(initialSurfaces.includes("POS"));
  const [backofficeEnabled, setBackofficeEnabled] = useState(
    initialSurfaces.includes("BACKOFFICE"),
  );
  const [permissionCodes, setPermissionCodes] = useState<string[]>(selectedCodesFromDetail);
  const [confirmedHighRiskChange, setConfirmedHighRiskChange] = useState(false);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  const surfaces = useMemo(
    () => toSurfaces(posEnabled, backofficeEnabled),
    [backofficeEnabled, posEnabled],
  );
  const hasSensitiveSelection = permissionCodes.some((item) =>
    sensitivePermissionCodes.includes(item),
  );
  const primaryTitle = isEdit ? "Editar rol" : "Nuevo rol";

  function togglePermission(permissionCode: string) {
    setPermissionCodes((current) =>
      current.includes(permissionCode)
        ? current.filter((item) => item !== permissionCode)
        : [...current, permissionCode],
    );
  }

  function validateForm(): boolean {
    if (!isEdit && !code.trim()) {
      setValidationMessage("El codigo del rol es obligatorio.");
      return false;
    }
    if (!name.trim()) {
      setValidationMessage("El nombre del rol es obligatorio.");
      return false;
    }
    if (surfaces.length === 0) {
      setValidationMessage("Selecciona acceso POS, Backoffice o ambos.");
      return false;
    }
    if (permissionCodes.length === 0) {
      setValidationMessage("Selecciona al menos un permiso.");
      return false;
    }
    if (hasSensitiveSelection && !confirmedHighRiskChange) {
      setValidationMessage("Confirma el cambio de alto riesgo antes de guardar.");
      return false;
    }
    setValidationMessage(null);
    return true;
  }

  function handleSubmit() {
    if (!validateForm()) {
      return;
    }
    if (isEdit && detail) {
      onUpdate(detail.overview.id, {
        confirmedHighRiskChange,
        description: description.trim() || null,
        name: name.trim(),
        permissionCodes,
        surfaces,
      });
      return;
    }
    onCreate({
      code: code.trim(),
      confirmedHighRiskChange,
      description: description.trim() || null,
      isActive: true,
      name: name.trim(),
      permissionCodes,
      surfaces,
    });
  }

  return (
    <section className="grid gap-3 rounded-[20px] border border-[var(--ui-color-border)] bg-white p-3 shadow-[var(--ui-shadow-subtle)]">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">{primaryTitle}</h3>
          <p className="mt-1 text-sm text-slate-600">
            Define superficie, permisos y advertencias de riesgo con persistencia backend.
          </p>
        </div>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700"
          type="button"
          onClick={onCancel}
        >
          Cerrar
        </button>
      </div>

      <div className="grid gap-2 md:grid-cols-3">
        <label className="grid gap-1 text-xs font-semibold text-slate-600">
          Codigo
          <input
            className={fieldClass()}
            disabled={isEdit}
            value={code}
            onChange={(event) => setCode(event.target.value)}
          />
        </label>
        <label className="grid gap-1 text-xs font-semibold text-slate-600">
          Nombre
          <input className={fieldClass()} value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <label className="grid gap-1 text-xs font-semibold text-slate-600">
          Descripcion
          <input
            className={fieldClass()}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </label>
      </div>

      <div className="grid gap-2 rounded-[16px] bg-slate-50 p-3">
        <span className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
          Superficies de acceso
        </span>
        <div className="flex flex-wrap gap-3">
          <label className="inline-flex items-center gap-2 text-sm font-semibold text-slate-700">
            <input
              checked={posEnabled}
              type="checkbox"
              onChange={(event) => setPosEnabled(event.target.checked)}
            />
            POS
          </label>
          <label className="inline-flex items-center gap-2 text-sm font-semibold text-slate-700">
            <input
              checked={backofficeEnabled}
              type="checkbox"
              onChange={(event) => setBackofficeEnabled(event.target.checked)}
            />
            Backoffice
          </label>
        </div>
      </div>

      <div className="grid max-h-80 gap-2 overflow-y-auto rounded-[16px] bg-slate-50 p-3">
        <span className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
          Permisos por modulo
        </span>
        {permissionGroups.length > 0 ? (
          permissionGroups.map((group) => (
            <div
              className="rounded-[14px] border border-[var(--ui-color-border)] bg-white px-3 py-2"
              key={group.module}
            >
              <p className="text-sm font-semibold text-slate-950">{group.label}</p>
              <div className="mt-2 grid gap-1 sm:grid-cols-2">
                {group.permissions.map((permission) => (
                  <label
                    className="inline-flex min-w-0 items-start gap-2 rounded-[12px] px-2 py-1 text-sm font-semibold text-slate-700"
                    key={permission.code}
                  >
                    <input
                      checked={permissionCodes.includes(permission.code)}
                      type="checkbox"
                      onChange={() => togglePermission(permission.code)}
                    />
                    <span className="min-w-0">
                      <span className="block truncate">
                        {permission.label}
                        {permission.isSensitive ? " · sensible" : ""}
                      </span>
                      <span className="block truncate text-xs font-normal text-slate-500">
                        {permission.code}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
            </div>
          ))
        ) : (
          <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
            Este rol no tiene permisos asignados.
          </p>
        )}
      </div>

      <label className="inline-flex items-start gap-2 rounded-[16px] border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-warning)]">
        <input
          checked={confirmedHighRiskChange}
          type="checkbox"
          onChange={(event) => setConfirmedHighRiskChange(event.target.checked)}
        />
        Confirmo que revise los permisos sensibles y el impacto operativo del rol.
      </label>

      {validationMessage || errorMessage ? (
        <p className="rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-danger)]">
          {validationMessage ?? errorMessage}
        </p>
      ) : null}

      <div className="flex flex-wrap justify-end gap-2">
        <button
          className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-4 py-2 text-sm font-semibold text-slate-700"
          type="button"
          onClick={onCancel}
        >
          Cancelar
        </button>
        <button
          className="rounded-2xl bg-[var(--ui-color-primary)] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
          disabled={isSubmitting}
          type="button"
          onClick={handleSubmit}
        >
          {isSubmitting ? "Guardando" : isEdit ? "Guardar cambios" : "Crear rol"}
        </button>
      </div>
    </section>
  );
}

