import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminRoleBackendContract,
  changeAdminRoleStatus,
  createAdminRole,
  fetchAdminRoleDetail,
  fetchAdminRolePermissions,
  fetchAdminRoles,
  removeAdminRoleFromUser,
  updateAdminRole,
} from "../api";
import { AdminRoleDetailPanel } from "../components/AdminRoleDetailPanel";
import { AdminRolesPermissionsFilters } from "../components/AdminRolesPermissionsFilters";
import { AdminRolesPermissionsTable } from "../components/AdminRolesPermissionsTable";
import { AdminRoleWorkflowPanel } from "../components/AdminRoleWorkflowPanel";
import type {
  AdminPermissionsResponse,
  AdminRoleCreatePayload,
  AdminRoleFilterOptions,
  AdminRoleListFilters,
  AdminRoleListItem,
  AdminRoleListResponse,
  AdminRoleUpdatePayload,
} from "../types";

const initialFilters: AdminRoleListFilters = {
  appSurface: "all",
  hasUsers: "all",
  highPrivilege: "all",
  page: 1,
  pageSize: 25,
  permissionModule: "all",
  search: "",
  status: "all",
  systemState: "all",
  warningState: "all",
};

const emptyFilterOptions: AdminRoleFilterOptions = {
  appSurfaces: [],
  hasUsers: [],
  highPrivilege: [],
  permissionModules: [],
  statuses: [],
  systemStates: [],
  warningStates: [],
};

const emptyRoleList: AdminRoleListResponse = {
  backendContract: adminRoleBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    activeRoles: "0",
    backofficeRoles: "0",
    highPrivilege: "0",
    inactiveRoles: "0",
    posRoles: "0",
    totalRoles: "0",
    withUsers: "0",
    withWarnings: "0",
    withoutUsers: "0",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

const emptyPermissions: AdminPermissionsResponse = {
  groups: [],
  sensitivePermissionCodes: [],
};

function RoleMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminRoleListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    { label: "Roles totales", value: loadingValue ?? metrics.totalRoles },
    { label: "Activos", value: loadingValue ?? metrics.activeRoles },
    { label: "Inactivos", value: loadingValue ?? metrics.inactiveRoles },
    { label: "Con usuarios", value: loadingValue ?? metrics.withUsers },
    { label: "Sin usuarios", value: loadingValue ?? metrics.withoutUsers },
    { label: "Alto privilegio", value: loadingValue ?? metrics.highPrivilege },
    { label: "POS", value: loadingValue ?? metrics.posRoles },
    { label: "Backoffice", value: loadingValue ?? metrics.backofficeRoles },
    { label: "Con advertencias", value: loadingValue ?? metrics.withWarnings },
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
          title={`${item.label}: ${item.value}`}
        >
          <span className="truncate text-slate-500">{item.label}</span>
          <span className="truncate font-semibold text-slate-950">{item.value}</span>
        </span>
      ))}
    </section>
  );
}

export function AdminRolesPermissionsPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminRoleListFilters>(initialFilters);
  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);
  const [workflowMode, setWorkflowMode] = useState<"create" | "edit" | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const rolesQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminRoles(accessToken ?? "", filters),
    queryKey: ["admin", "roles", "list", filters],
    retry: false,
  });

  const permissionsQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminRolePermissions(accessToken ?? ""),
    queryKey: ["admin", "roles", "permissions"],
    retry: false,
  });

  const roleList = rolesQuery.data ?? emptyRoleList;
  const permissions = permissionsQuery.data ?? emptyPermissions;
  const selectedRole = useMemo(
    () => roleList.items.find((item) => item.id === selectedRoleId) ?? null,
    [roleList.items, selectedRoleId],
  );

  const detailQuery = useQuery({
    enabled: Boolean(accessToken && selectedRoleId),
    queryFn: () => fetchAdminRoleDetail(accessToken ?? "", selectedRoleId ?? ""),
    queryKey: ["admin", "roles", "detail", selectedRoleId],
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: (payload: AdminRoleCreatePayload) => createAdminRole(accessToken ?? "", payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo crear el rol."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Rol ${detail.overview.name} creado.` });
      setSelectedRoleId(detail.overview.id);
      setWorkflowMode(null);
      await queryClient.invalidateQueries({ queryKey: ["admin", "roles"] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ payload, roleId }: { payload: AdminRoleUpdatePayload; roleId: string }) =>
      updateAdminRole(accessToken ?? "", roleId, payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo actualizar el rol."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Rol ${detail.overview.name} actualizado.` });
      setSelectedRoleId(detail.overview.id);
      setWorkflowMode(null);
      await queryClient.invalidateQueries({ queryKey: ["admin", "roles"] });
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({
      confirmedHighRiskChange,
      isActive,
      roleId,
    }: {
      confirmedHighRiskChange: boolean;
      isActive: boolean;
      roleId: string;
    }) => changeAdminRoleStatus(accessToken ?? "", roleId, isActive, confirmedHighRiskChange),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo cambiar el estado del rol."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Estado actualizado para ${detail.overview.name}.` });
      setSelectedRoleId(detail.overview.id);
      await queryClient.invalidateQueries({ queryKey: ["admin", "roles"] });
    },
  });

  const removeUserMutation = useMutation({
    mutationFn: ({ roleId, userId }: { roleId: string; userId: string }) =>
      removeAdminRoleFromUser(accessToken ?? "", roleId, userId),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo quitar el usuario del rol."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Usuario removido de ${detail.overview.name}.` });
      await queryClient.invalidateQueries({ queryKey: ["admin", "roles"] });
      await queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });

  const listErrorMessage = rolesQuery.isError
    ? toBackofficeErrorMessage(rolesQuery.error, "No se pudieron cargar los roles.")
    : null;
  const detailErrorMessage = detailQuery.isError
    ? toBackofficeErrorMessage(detailQuery.error, "No se pudo cargar el detalle del rol.")
    : null;
  const workflowErrorMessage =
    createMutation.isError || updateMutation.isError
      ? toBackofficeErrorMessage(
          createMutation.error ?? updateMutation.error,
          "No se pudo guardar el rol.",
        )
      : null;
  const pageStatusLabel = rolesQuery.isLoading
    ? "Validando API"
    : roleList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminRoleListFilters>) {
    setFilters((current) => ({ ...current, ...patch, page: patch.page ?? 1 }));
    setSelectedRoleId(null);
  }

  function handleSelectRole(item: AdminRoleListItem) {
    setSelectedRoleId(item.id);
  }

  function handleCopyRole(value: AdminRoleListItem | string) {
    const code = typeof value === "string" ? value : value.code;
    void navigator.clipboard?.writeText(code);
    setFeedback({ tone: "success", message: `Codigo ${code} copiado.` });
  }

  function handleEdit(item: AdminRoleListItem) {
    setSelectedRoleId(item.id);
    setWorkflowMode("edit");
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionCapability="roles.manage"
        actionGlobalOnly
        actionLabel="Nuevo rol"
        description="Define roles, permisos por modulo, acceso a POS y Backoffice, alcance operativo y usuarios asignados."
        meta={[pageStatusLabel]}
        title="Roles y permisos"
        onAction={() => {
          setSelectedRoleId(null);
          setWorkflowMode("create");
        }}
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminRolesPermissionsFilters
          filters={filters}
          isBackendConnected={roleList.isBackendConnected}
          options={roleList.filterOptions}
          onChange={patchFilters}
        />

        <RoleMetricStrip isLoading={rolesQuery.isLoading} metrics={roleList.metrics} />

        <div className="flex min-w-0 flex-wrap gap-2">
          <button
            className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
            type="button"
            onClick={() => rolesQuery.refetch()}
          >
            Actualizar
          </button>
          <button
            className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
            type="button"
            onClick={() => patchFilters({ highPrivilege: "yes" })}
          >
            Ver roles criticos
          </button>
        </div>

        {workflowMode ? (
          <AdminRoleWorkflowPanel
            detail={detailQuery.data ?? null}
            errorMessage={workflowErrorMessage}
            isSubmitting={createMutation.isPending || updateMutation.isPending}
            mode={workflowMode}
            permissionGroups={permissions.groups}
            sensitivePermissionCodes={permissions.sensitivePermissionCodes}
            onCancel={() => setWorkflowMode(null)}
            onCreate={(payload) => createMutation.mutate(payload)}
            onUpdate={(roleId, payload) => updateMutation.mutate({ payload, roleId })}
          />
        ) : null}

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

        <div className="grid min-h-0 min-w-0 flex-1 gap-2.5 xl:grid-cols-[minmax(0,1fr)_minmax(23rem,0.42fr)]">
          <AdminRolesPermissionsTable
            errorMessage={listErrorMessage}
            isLoading={rolesQuery.isLoading}
            page={filters.page}
            pageSize={filters.pageSize}
            roles={roleList.items}
            selectedRoleId={selectedRoleId}
            total={roleList.total}
            onCopyRole={handleCopyRole}
            onEdit={handleEdit}
            onPageChange={(page) => setFilters((current) => ({ ...current, page }))}
            onSelectRole={handleSelectRole}
          />

          <AdminRoleDetailPanel
            detail={detailQuery.data ?? null}
            errorMessage={detailErrorMessage}
            isLoading={
              detailQuery.isLoading || statusMutation.isPending || removeUserMutation.isPending
            }
            selectedRole={selectedRole}
            onActivate={(item) =>
              statusMutation.mutate({
                confirmedHighRiskChange: true,
                isActive: true,
                roleId: item.id,
              })
            }
            onCopyRole={handleCopyRole}
            onDeactivate={(item) =>
              statusMutation.mutate({
                confirmedHighRiskChange: item.assignedUserCount > 0,
                isActive: false,
                roleId: item.id,
              })
            }
            onEdit={handleEdit}
            onRemoveUser={(roleId, userId) => removeUserMutation.mutate({ roleId, userId })}
          />
        </div>
      </div>
    </section>
  );
}
