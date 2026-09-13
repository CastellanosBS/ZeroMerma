import { useMemo, useState } from "react";

import { useBackofficeAuthorization } from "../../../auth/authorization-context";
import { hasEffectiveCapability } from "../../../auth/authorization";
import { AdminActionButton } from "../../components/AdminActionButton";

import type {
  AdminUserCreatePayload,
  AdminUserDetail,
  AdminUserFilterOptions,
  AdminUserSurface,
  AdminUserUpdatePayload,
} from "../types";

type WorkflowMode = "create" | "edit";

interface AdminUserWorkflowPanelProps {
  detail: AdminUserDetail | null;
  errorMessage?: string | null;
  isSubmitting?: boolean;
  mode: WorkflowMode;
  options: AdminUserFilterOptions;
  onAddBranch: (userId: string, branchId: string, isDefault: boolean) => void;
  onCancel: () => void;
  onCreate: (payload: AdminUserCreatePayload) => void;
  onUpdate: (userId: string, payload: AdminUserUpdatePayload) => void;
}

function fieldClass() {
  return "h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-700 placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]";
}

function toSurfaces(posEnabled: boolean, backofficeEnabled: boolean): AdminUserSurface[] {
  return [
    ...(posEnabled ? (["POS"] as const) : []),
    ...(backofficeEnabled ? (["BACKOFFICE"] as const) : []),
  ];
}

export function AdminUserWorkflowPanel({
  detail,
  errorMessage,
  isSubmitting = false,
  mode,
  options,
  onAddBranch,
  onCancel,
  onCreate,
  onUpdate,
}: AdminUserWorkflowPanelProps) {
  const isEdit = mode === "edit" && detail !== null;
  const actor = useBackofficeAuthorization();
  const assignableBranches = options.branches.filter((branch) =>
    hasEffectiveCapability(actor, "role_assignments.manage", [branch.id]),
  );
  const canEditAppAccess = !isEdit || Boolean(detail?.availableActions.canEditAppAccess);
  const canEditBranches = !isEdit || Boolean(detail?.availableActions.canEditBranchAssignments);
  const initialSurfaces = detail?.appAccess.allowedSurfaces ?? ["BACKOFFICE"];
  const [fullName, setFullName] = useState(detail?.profile.fullName ?? "");
  const [email, setEmail] = useState(detail?.profile.email ?? "");
  const [phone, setPhone] = useState(detail?.profile.phone ?? "");
  const [notes, setNotes] = useState(detail?.profile.notes ?? "");
  const [temporaryPassword, setTemporaryPassword] = useState("");
  const [posEnabled, setPosEnabled] = useState(initialSurfaces.includes("POS"));
  const [backofficeEnabled, setBackofficeEnabled] = useState(
    initialSurfaces.includes("BACKOFFICE"),
  );
  const [defaultSurface, setDefaultSurface] = useState<AdminUserSurface>(
    detail?.appAccess.defaultSurface ?? "BACKOFFICE",
  );
  const [selectedBranchIds, setSelectedBranchIds] = useState<string[]>(
    detail?.branchAssignments
      .filter((assignment) => assignment.isActive)
      .map((assignment) => assignment.branchId) ?? [],
  );
  const [branchToAdd, setBranchToAdd] = useState(assignableBranches[0]?.id ?? "");
  const [makeDefaultBranch, setMakeDefaultBranch] = useState(false);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  const surfaces = useMemo(
    () => toSurfaces(posEnabled, backofficeEnabled),
    [backofficeEnabled, posEnabled],
  );
  const requiresDefaultSurface = surfaces.length > 1;
  const primaryTitle = isEdit ? "Editar usuario" : "Nuevo usuario";

  function toggleBranch(branchId: string) {
    setSelectedBranchIds((current) =>
      current.includes(branchId)
        ? current.filter((item) => item !== branchId)
        : [...current, branchId],
    );
  }

  function validateForm(): boolean {
    if (
      !isEdit &&
      selectedBranchIds.some((id) => !assignableBranches.some((branch) => branch.id === id))
    ) {
      setValidationMessage("No tienes permiso para asignar esas sucursales.");
      return false;
    }
    if (!fullName.trim()) {
      setValidationMessage("El nombre completo es obligatorio.");
      return false;
    }
    if (!email.trim() || !email.includes("@")) {
      setValidationMessage("El correo debe ser valido.");
      return false;
    }
    if (surfaces.length === 0) {
      setValidationMessage("Selecciona acceso POS, Backoffice o ambos.");
      return false;
    }
    if (requiresDefaultSurface && !surfaces.includes(defaultSurface)) {
      setValidationMessage("Selecciona una superficie inicial valida.");
      return false;
    }
    if (!isEdit && temporaryPassword.trim().length < 8) {
      setValidationMessage("La contrasena temporal debe tener al menos 8 caracteres.");
      return false;
    }
    if (!isEdit && surfaces.includes("POS") && selectedBranchIds.length === 0) {
      setValidationMessage("Los usuarios POS requieren al menos una sucursal.");
      return false;
    }
    setValidationMessage(null);
    return true;
  }

  function handleSubmit() {
    if (!validateForm()) {
      return;
    }
    const resolvedDefaultSurface = requiresDefaultSurface ? defaultSurface : surfaces[0];
    if (isEdit && detail) {
      onUpdate(detail.overview.id, {
        allowedSurfaces: surfaces,
        defaultSurface: resolvedDefaultSurface,
        email: email.trim(),
        fullName: fullName.trim(),
        notes: notes.trim() || null,
        phone: phone.trim() || null,
      });
      return;
    }
    onCreate({
      allowedSurfaces: surfaces,
      branchAssignments: selectedBranchIds.map((branchId, index) => ({
        branchId,
        isDefault: index === 0,
      })),
      defaultSurface: resolvedDefaultSurface,
      email: email.trim(),
      fullName: fullName.trim(),
      notes: notes.trim() || null,
      phone: phone.trim() || null,
      sendInvitation: false,
      temporaryPassword: temporaryPassword,
    });
  }

  function handleAddBranch() {
    if (
      !detail ||
      !branchToAdd ||
      !canEditBranches ||
      !assignableBranches.some((branch) => branch.id === branchToAdd)
    ) {
      return;
    }
    onAddBranch(detail.overview.id, branchToAdd, makeDefaultBranch);
  }

  return (
    <section className="grid gap-3 rounded-[20px] border border-[var(--ui-color-border)] bg-white p-3 shadow-[var(--ui-shadow-subtle)]">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">{primaryTitle}</h3>
          <p className="mt-1 text-sm text-slate-600">
            Gestiona identidad, acceso de aplicacion y asignacion inicial de sucursales con
            persistencia backend.
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

      <div className="grid gap-2 md:grid-cols-2">
        <label className="grid gap-1 text-xs font-semibold text-slate-600">
          Nombre completo
          <input
            className={fieldClass()}
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
          />
        </label>
        <label className="grid gap-1 text-xs font-semibold text-slate-600">
          Correo
          <input
            className={fieldClass()}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label className="grid gap-1 text-xs font-semibold text-slate-600">
          Telefono
          <input
            className={fieldClass()}
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
          />
        </label>
        <label className="grid gap-1 text-xs font-semibold text-slate-600">
          Notas
          <input
            className={fieldClass()}
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
          />
        </label>
        {!isEdit ? (
          <label className="grid gap-1 text-xs font-semibold text-slate-600 md:col-span-2">
            Contrasena temporal
            <input
              className={fieldClass()}
              type="password"
              value={temporaryPassword}
              onChange={(event) => setTemporaryPassword(event.target.value)}
            />
          </label>
        ) : null}
      </div>

      <div className="grid gap-2 rounded-[16px] bg-slate-50 p-3">
        <span className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
          Acceso a aplicaciones
        </span>
        <div className="flex flex-wrap gap-3">
          <label className="inline-flex items-center gap-2 text-sm font-semibold text-slate-700">
            <input
              disabled={!canEditAppAccess}
              checked={posEnabled}
              type="checkbox"
              onChange={(event) => setPosEnabled(event.target.checked)}
            />
            POS
          </label>
          <label className="inline-flex items-center gap-2 text-sm font-semibold text-slate-700">
            <input
              disabled={!canEditAppAccess}
              checked={backofficeEnabled}
              type="checkbox"
              onChange={(event) => setBackofficeEnabled(event.target.checked)}
            />
            Backoffice
          </label>
          <select
            className={fieldClass()}
            disabled={!requiresDefaultSurface || !canEditAppAccess}
            value={defaultSurface}
            onChange={(event) => setDefaultSurface(event.target.value as AdminUserSurface)}
          >
            <option value="POS">Inicio POS</option>
            <option value="BACKOFFICE">Inicio Backoffice</option>
          </select>
        </div>
      </div>

      <div className="grid gap-2 rounded-[16px] bg-slate-50 p-3">
        <span className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
          Sucursales
        </span>
        {!canEditBranches || assignableBranches.length === 0 ? (
          <p className="text-sm text-slate-600">
            La asignación de sucursales requiere autorización adicional.
          </p>
        ) : !isEdit ? (
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {assignableBranches.map((branch) => (
              <label
                className="inline-flex min-w-0 items-center gap-2 rounded-[14px] border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700"
                key={branch.id}
              >
                <input
                  checked={selectedBranchIds.includes(branch.id)}
                  type="checkbox"
                  onChange={() => toggleBranch(branch.id)}
                />
                <span className="truncate">{branch.label}</span>
              </label>
            ))}
          </div>
        ) : (
          <div className="flex min-w-0 flex-wrap gap-2">
            <select
              className={fieldClass()}
              value={branchToAdd}
              onChange={(event) => setBranchToAdd(event.target.value)}
            >
              {assignableBranches.map((branch) => (
                <option key={branch.id} value={branch.id}>
                  {branch.label}
                </option>
              ))}
            </select>
            <label className="inline-flex items-center gap-2 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-700">
              <input
                checked={makeDefaultBranch}
                type="checkbox"
                onChange={(event) => setMakeDefaultBranch(event.target.checked)}
              />
              Predeterminada
            </label>
            <AdminActionButton
              capability="role_assignments.manage"
              branchIds={[branchToAdd]}
              className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-700"
              disabled={!branchToAdd || isSubmitting}
              type="button"
              onClick={handleAddBranch}
            >
              Agregar sucursal
            </AdminActionButton>
          </div>
        )}
      </div>

      <p className="text-sm text-slate-600">
        Los roles y su alcance se administran por separado después de crear la cuenta.
      </p>

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
        <AdminActionButton
          capability="users.manage"
          className="rounded-2xl bg-[var(--ui-color-primary)] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
          disabled={isSubmitting || (isEdit && !detail.availableActions.canEditProfile)}
          type="button"
          onClick={handleSubmit}
        >
          {isSubmitting ? "Guardando" : isEdit ? "Guardar cambios" : "Crear usuario"}
        </AdminActionButton>
      </div>
    </section>
  );
}
