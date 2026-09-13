import { useState } from "react";

import { hasEffectiveCapability } from "../../../auth/authorization";
import { useBackofficeAuthorization } from "../../../auth/authorization-context";
import { AdminActionButton } from "../../components/AdminActionButton";
import type {
  AdminUserDetail,
  AdminUserFilterOption,
  AdminUserRoleAssignmentPayload,
} from "../types";

interface Props {
  detail: AdminUserDetail;
  roles: AdminUserFilterOption[];
  pending: boolean;
  errorMessage: string | null;
  onSave: (payload: AdminUserRoleAssignmentPayload) => void;
  onRemove: (roleId: string) => void;
}

export function AdminUserRoleAssignmentPanel({
  detail,
  roles,
  pending,
  errorMessage,
  onSave,
  onRemove,
}: Props) {
  const actor = useBackofficeAuthorization();
  const [roleId, setRoleId] = useState("");
  const [scopeType, setScopeType] =
    useState<AdminUserRoleAssignmentPayload["scope_type"]>("BRANCH_SET");
  const [branchIds, setBranchIds] = useState<string[]>([]);
  const canUseGlobal = hasEffectiveCapability(actor, "role_assignments.manage", [], true);
  const branches = detail.branchAssignments.filter(
    (branch) =>
      branch.isActive &&
      hasEffectiveCapability(actor, "role_assignments.manage", [branch.branchId]),
  );

  if (
    !detail.availableActions.canEditRoleAssignments ||
    !hasEffectiveCapability(actor, "role_assignments.manage")
  )
    return null;

  function selectRole(value: string) {
    setRoleId(value);
    const existing = detail.roleAssignments.items.find((assignment) => assignment.roleId === value);
    setScopeType(existing?.scopeType ?? "BRANCH_SET");
    setBranchIds(existing?.branchIds ?? []);
  }

  const currentAssignment = detail.roleAssignments.items.find(
    (assignment) => assignment.roleId === roleId,
  );
  const validScope =
    scopeType === "GLOBAL"
      ? canUseGlobal
      : branchIds.length > 0 &&
        branchIds.every((id) => branches.some((branch) => branch.branchId === id));

  return (
    <section className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4">
      <h3 className="font-semibold">Roles y alcance de {detail.overview.fullName}</h3>
      <label className="grid gap-1 text-sm">
        Rol
        <select value={roleId} onChange={(event) => selectRole(event.target.value)}>
          <option value="">Selecciona un rol</option>
          {roles.map((role) => (
            <option key={role.id} value={role.id}>
              {role.label}
            </option>
          ))}
        </select>
      </label>
      <label className="grid gap-1 text-sm">
        Alcance de la asignación
        <select
          value={scopeType}
          onChange={(event) => {
            setScopeType(event.target.value as AdminUserRoleAssignmentPayload["scope_type"]);
            setBranchIds([]);
          }}
        >
          <option value="BRANCH_SET">Sucursales seleccionadas</option>
          <option value="GLOBAL" disabled={!canUseGlobal}>
            Global explícito
          </option>
        </select>
      </label>
      {scopeType === "BRANCH_SET" ? (
        <fieldset className="grid gap-2">
          <legend>Sucursales activas del usuario</legend>
          {branches.map((branch) => (
            <label key={branch.branchId} className="flex gap-2">
              <input
                type="checkbox"
                checked={branchIds.includes(branch.branchId)}
                onChange={(event) =>
                  setBranchIds((current) =>
                    event.target.checked
                      ? [...current, branch.branchId]
                      : current.filter((id) => id !== branch.branchId),
                  )
                }
              />
              {branch.branchName}
            </label>
          ))}
          {branches.length === 0 ? <p>No hay sucursales asignadas que puedas autorizar.</p> : null}
        </fieldset>
      ) : (
        <p>
          Esta asignación permitirá operar en todas las sucursales para las capacidades del rol.
        </p>
      )}
      <p className="text-sm text-slate-600">
        Los cambios de Superadministrador requieren su procedimiento de aprobación independiente.
      </p>
      {errorMessage ? (
        <p role="alert" className="text-sm text-rose-700">
          {errorMessage}
        </p>
      ) : null}
      <div className="flex gap-2">
        <AdminActionButton
          capability="role_assignments.manage"
          branchIds={scopeType === "BRANCH_SET" ? branchIds : []}
          globalOnly={scopeType === "GLOBAL"}
          disabled={pending || !roleId || !validScope}
          onClick={() =>
            onSave({
              role_id: roleId,
              scope_type: scopeType,
              branch_ids: scopeType === "GLOBAL" ? [] : branchIds,
            })
          }
        >
          Guardar asignación
        </AdminActionButton>
        <AdminActionButton
          capability="role_assignments.manage"
          branchIds={currentAssignment?.branchIds}
          globalOnly={currentAssignment?.scopeType === "GLOBAL"}
          disabled={pending || !currentAssignment}
          onClick={() => onRemove(roleId)}
        >
          Retirar rol
        </AdminActionButton>
      </div>
    </section>
  );
}
