import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminEntityDrawer } from "../../components/AdminEntityDrawer";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  addAdminUserBranchAssignment,
  adminUserBackendContract,
  changeAdminUserStatus,
  createAdminUser,
  fetchAdminUserDetail,
  fetchAdminUsers,
  lockAdminUser,
  unlockAdminUser,
  updateAdminUser,
} from "../api";
import { AdminUserDetailPanel } from "../components/AdminUserDetailPanel";
import { AdminUsersFilters } from "../components/AdminUsersFilters";
import { AdminUsersTable } from "../components/AdminUsersTable";
import { AdminUserWorkflowPanel } from "../components/AdminUserWorkflowPanel";
import type {
  AdminUserCreatePayload,
  AdminUserFilterOptions,
  AdminUserListFilters,
  AdminUserListItem,
  AdminUserListResponse,
  AdminUserUpdatePayload,
} from "../types";

const initialFilters: AdminUserListFilters = {
  appAccess: "all",
  branchId: "all",
  lastLoginState: "all",
  page: 1,
  pageSize: 25,
  roleId: "all",
  search: "",
  status: "all",
  warningState: "all",
};

const emptyFilterOptions: AdminUserFilterOptions = {
  appAccess: [],
  branches: [],
  lastLoginStates: [],
  roles: [],
  statuses: [],
  warningStates: [],
};

const emptyUserList: AdminUserListResponse = {
  backendContract: adminUserBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    activeUsers: "0",
    backofficeUsers: "0",
    inactiveUsers: "0",
    lockedUsers: "0",
    pendingUsers: "0",
    posUsers: "0",
    totalUsers: "0",
    withoutBranch: "0",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

function UserMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminUserListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    { label: "Usuarios totales", value: loadingValue ?? metrics.totalUsers },
    { label: "Activos", value: loadingValue ?? metrics.activeUsers },
    { label: "Inactivos", value: loadingValue ?? metrics.inactiveUsers },
    { label: "Bloqueados", value: loadingValue ?? metrics.lockedUsers },
    { label: "Pendientes", value: loadingValue ?? metrics.pendingUsers },
    { label: "POS", value: loadingValue ?? metrics.posUsers },
    { label: "Backoffice", value: loadingValue ?? metrics.backofficeUsers },
    { label: "Sin sucursal", value: loadingValue ?? metrics.withoutBranch },
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

export function AdminUsersPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminUserListFilters>(initialFilters);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [workflowMode, setWorkflowMode] = useState<"create" | "edit" | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const usersQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminUsers(accessToken ?? "", filters),
    queryKey: ["admin", "users", "list", filters],
    retry: false,
  });

  const userList = usersQuery.data ?? emptyUserList;
  const selectedUser = useMemo(
    () => userList.items.find((item) => item.id === selectedUserId) ?? null,
    [selectedUserId, userList.items],
  );

  const detailQuery = useQuery({
    enabled: Boolean(accessToken && selectedUserId),
    queryFn: () => fetchAdminUserDetail(accessToken ?? "", selectedUserId ?? ""),
    queryKey: ["admin", "users", "detail", selectedUserId],
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: (payload: AdminUserCreatePayload) => createAdminUser(accessToken ?? "", payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo crear el usuario."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Usuario ${detail.overview.email} creado.` });
      setSelectedUserId(detail.overview.id);
      setWorkflowMode(null);
      await queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ payload, userId }: { payload: AdminUserUpdatePayload; userId: string }) =>
      updateAdminUser(accessToken ?? "", userId, payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo actualizar el usuario."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Usuario ${detail.overview.email} actualizado.` });
      setSelectedUserId(detail.overview.id);
      setWorkflowMode(null);
      await queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({ isActive, userId }: { isActive: boolean; userId: string }) =>
      changeAdminUserStatus(accessToken ?? "", userId, { isActive }),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo cambiar el estado."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Estado actualizado para ${detail.overview.email}.` });
      setSelectedUserId(detail.overview.id);
      await queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });

  const lockMutation = useMutation({
    mutationFn: ({ reason, userId }: { reason: string | null; userId: string }) =>
      lockAdminUser(accessToken ?? "", userId, { reason }),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo bloquear la cuenta."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Cuenta ${detail.overview.email} bloqueada.` });
      setSelectedUserId(detail.overview.id);
      await queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });

  const unlockMutation = useMutation({
    mutationFn: (userId: string) => unlockAdminUser(accessToken ?? "", userId),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo desbloquear la cuenta."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Cuenta ${detail.overview.email} desbloqueada.` });
      setSelectedUserId(detail.overview.id);
      await queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });

  const branchMutation = useMutation({
    mutationFn: ({
      branchId,
      isDefault,
      userId,
    }: {
      branchId: string;
      isDefault: boolean;
      userId: string;
    }) => addAdminUserBranchAssignment(accessToken ?? "", userId, branchId, isDefault),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo asignar la sucursal."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Sucursal asignada a ${detail.overview.email}.` });
      setSelectedUserId(detail.overview.id);
      await queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });

  const listErrorMessage = usersQuery.isError
    ? toBackofficeErrorMessage(usersQuery.error, "No se pudieron cargar los usuarios.")
    : null;
  const detailErrorMessage = detailQuery.isError
    ? toBackofficeErrorMessage(detailQuery.error, "No se pudo cargar el detalle del usuario.")
    : null;
  const workflowErrorMessage = createMutation.isError || updateMutation.isError || branchMutation.isError
    ? toBackofficeErrorMessage(
        createMutation.error ?? updateMutation.error ?? branchMutation.error,
        "No se pudo guardar el usuario.",
      )
    : null;
  const pageStatusLabel = usersQuery.isLoading
    ? "Validando API"
    : userList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminUserListFilters>) {
    setFilters((current) => ({ ...current, ...patch, page: patch.page ?? 1 }));
    setSelectedUserId(null);
  }

  function handleSelectUser(item: AdminUserListItem) {
    setSelectedUserId(item.id);
  }

  function handleCopyEmail(value: AdminUserListItem | string) {
    const email = typeof value === "string" ? value : value.email;
    void navigator.clipboard?.writeText(email);
    setFeedback({ tone: "success", message: `Correo ${email} copiado.` });
  }

  function handleEdit(item: AdminUserListItem) {
    setSelectedUserId(item.id);
    setWorkflowMode("edit");
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionLabel="Nuevo usuario"
        description="Administra usuarios, acceso a POS y Backoffice, sucursales asignadas, roles y estado de cuenta."
        meta={[pageStatusLabel]}
        title="Usuarios"
        onAction={() => {
          setSelectedUserId(null);
          setWorkflowMode("create");
        }}
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminUsersFilters
          filters={filters}
          isBackendConnected={userList.isBackendConnected}
          options={userList.filterOptions}
          onChange={patchFilters}
        />

        <UserMetricStrip isLoading={usersQuery.isLoading} metrics={userList.metrics} />

        <div className="flex min-w-0 flex-wrap gap-2">
          <button
            className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
            type="button"
            onClick={() => usersQuery.refetch()}
          >
            Actualizar
          </button>
          <button
            className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
            type="button"
            onClick={() => patchFilters({ status: "locked" })}
          >
            Ver bloqueados
          </button>
        </div>

        <AdminEntityDrawer
          description="Gestiona identidad, acceso, roles y sucursales en un panel lateral."
          isOpen={Boolean(workflowMode)}
          title={workflowMode === "edit" ? "Editar usuario" : "Nuevo usuario"}
          onClose={() => setWorkflowMode(null)}
        >
          {workflowMode ? (
          <AdminUserWorkflowPanel
            detail={detailQuery.data ?? null}
            errorMessage={workflowErrorMessage}
            isSubmitting={
              createMutation.isPending || updateMutation.isPending || branchMutation.isPending
            }
            mode={workflowMode}
            options={userList.filterOptions}
            onAddBranch={(userId, branchId, isDefault) =>
              branchMutation.mutate({ branchId, isDefault, userId })
            }
            onCancel={() => setWorkflowMode(null)}
            onCreate={(payload) => createMutation.mutate(payload)}
            onUpdate={(userId, payload) => updateMutation.mutate({ payload, userId })}
          />
          ) : null}
        </AdminEntityDrawer>

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
          <AdminUsersTable
            errorMessage={listErrorMessage}
            isLoading={usersQuery.isLoading}
            page={filters.page}
            pageSize={filters.pageSize}
            selectedUserId={selectedUserId}
            total={userList.total}
            users={userList.items}
            onCopyEmail={handleCopyEmail}
            onEdit={handleEdit}
            onPageChange={(page) => setFilters((current) => ({ ...current, page }))}
            onSelectUser={handleSelectUser}
          />

          <AdminUserDetailPanel
            detail={detailQuery.data ?? null}
            errorMessage={detailErrorMessage}
            isLoading={
              detailQuery.isLoading
              || statusMutation.isPending
              || lockMutation.isPending
              || unlockMutation.isPending
            }
            selectedUser={selectedUser}
            onActivate={(item) => statusMutation.mutate({ isActive: true, userId: item.id })}
            onCopyEmail={handleCopyEmail}
            onDeactivate={(item) => statusMutation.mutate({ isActive: false, userId: item.id })}
            onEdit={handleEdit}
            onLock={(item) => lockMutation.mutate({ reason: "Bloqueado desde Backoffice.", userId: item.id })}
            onUnlock={(item) => unlockMutation.mutate(item.id)}
          />
        </div>
      </div>
    </section>
  );
}
