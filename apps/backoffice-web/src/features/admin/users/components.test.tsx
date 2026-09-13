import { withCapabilities } from "../../../test-support/authorization";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminUserDetailPanel } from "./components/AdminUserDetailPanel";
import { AdminUsersFilters } from "./components/AdminUsersFilters";
import { AdminUsersTable } from "./components/AdminUsersTable";
import { AdminUserWorkflowPanel } from "./components/AdminUserWorkflowPanel";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import type {
  AdminUserDetail,
  AdminUserFilterOptions,
  AdminUserListFilters,
  AdminUserListItem,
} from "./types";

const filterOptions: AdminUserFilterOptions = {
  appAccess: [{ id: "BACKOFFICE", label: "Backoffice" }],
  branches: [{ id: "branch-1", label: "Main Branch - MAIN" }],
  lastLoginStates: [{ id: "with_login", label: "Con acceso" }],
  roles: [],
  statuses: [{ id: "active", label: "Activos" }],
  warningStates: [{ id: "with_warnings", label: "Con advertencias" }],
};

const filters: AdminUserListFilters = {
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

const user: AdminUserListItem = {
  allowedSurfaces: ["POS", "BACKOFFICE"],
  branchCount: 1,
  branchNames: ["Main Branch"],
  createdAt: "2026-05-22T10:00:00Z",
  defaultSurface: "BACKOFFICE",
  email: "admin@zeromerma.local",
  fullName: "ZeroMerma Admin",
  id: "user-1",
  lastLoginAt: "2026-05-22T11:00:00Z",
  roleCount: 0,
  roleNames: [],
  status: "active",
  updatedAt: "2026-05-22T11:00:00Z",
  warningState: "ready",
  warnings: [],
};

const detail: AdminUserDetail = {
  accountStatus: {
    activeSessionsCount: null,
    activeSessionsSupported: false,
    failedLoginCount: null,
    isActive: true,
    isLocked: false,
    lastLoginAt: "2026-05-22T11:00:00Z",
    lockReason: null,
    passwordResetRequired: false,
    pendingInvitation: false,
  },
  appAccess: {
    allowedSurfaces: ["POS", "BACKOFFICE"],
    backofficeEnabled: true,
    defaultSurface: "BACKOFFICE",
    hasBothSurfaces: true,
    posEnabled: true,
  },
  auditTimeline: [
    {
      action: "admin.user.created",
      actorId: "admin-1",
      id: "audit-1",
      metadata: {},
      occurredAt: "2026-05-22T10:00:00Z",
    },
  ],
  availableActions: {
    canActivate: false,
    canDeactivate: true,
    canEditAppAccess: true,
    canEditBranchAssignments: true,
    canEditProfile: true,
    canEditRoleAssignments: false,
    canLock: true,
    canOpenAudit: true,
    canUnlock: false,
  },
  branchAssignments: [
    {
      assignedAt: "2026-05-22T10:00:00Z",
      assignmentId: "assignment-1",
      branchCode: "MAIN",
      branchId: "branch-1",
      branchName: "Main Branch",
      isActive: true,
      isDefault: true,
      updatedAt: "2026-05-22T10:00:00Z",
    },
  ],
  operationalContext: {
    activeSessionsSupported: false,
    lastWorkstationUsed: null,
    openCashSessionsCount: 0,
    recentBackofficeActivityCount: 1,
    recentPosActivityCount: 0,
    recentlyOperatedBranches: [],
  },
  overview: user,
  profile: {
    displayName: null,
    email: "admin@zeromerma.local",
    employeeCode: null,
    fullName: "ZeroMerma Admin",
    notes: null,
    phone: null,
  },
  roleAssignments: {
    isSupported: false,
    items: [],
    missingContractNote: "Role assignment backend support is not available yet.",
  },
  securityActions: {
    canActivate: false,
    canDeactivate: true,
    canLock: true,
    canRevokeSessions: false,
    canSendInvitation: false,
    canSendPasswordReset: false,
    canUnlock: false,
    supportsInvitation: false,
    supportsLocking: true,
    supportsPasswordReset: false,
    supportsSessionRevocation: false,
  },
  warnings: [],
};

function render(element: ReactElement) {
  return renderToString(withCapabilities(element, ["users.manage", "role_assignments.manage"]));
}

describe("admin users UI components", () => {
  it("renders the page shell with the canonical action", () => {
    const queryClient = new QueryClient();
    const html = render(
      <QueryClientProvider client={queryClient}>
        <AdminUsersPage />
      </QueryClientProvider>,
    );

    expect(html).toContain("Usuarios");
    expect(html).toContain("Nuevo usuario");
    expect(html).toContain(
      "Selecciona un usuario para revisar acceso, sucursales, roles y estado de cuenta.",
    );
  });

  it("renders compact filter toolbar", () => {
    const html = render(
      <AdminUsersFilters
        filters={filters}
        isBackendConnected={true}
        options={filterOptions}
        onChange={() => undefined}
      />,
    );

    expect(html).toContain("Buscar por nombre o correo");
    expect(html).toContain("Filtros");
    expect(html).toContain("Backend conectado");
    expect(html).not.toContain("Con advertencias");
  });

  it("renders empty and populated user table states", () => {
    const emptyHtml = render(
      <AdminUsersTable
        page={1}
        pageSize={25}
        total={0}
        users={[]}
        onCopyEmail={() => undefined}
        onEdit={() => undefined}
        onPageChange={() => undefined}
        onSelectUser={() => undefined}
      />,
    );
    expect(emptyHtml).toContain("No hay usuarios registrados para los filtros seleccionados.");

    const tableHtml = render(
      <AdminUsersTable
        page={1}
        pageSize={25}
        total={1}
        users={[user]}
        onCopyEmail={() => undefined}
        onEdit={() => undefined}
        onPageChange={() => undefined}
        onSelectUser={() => undefined}
      />,
    );
    expect(tableHtml).toContain("ZeroMerma Admin");
    expect(tableHtml).toContain("POS + Backoffice");
    expect(tableHtml).toContain("Sin roles");
  });

  it("renders user detail sections and security actions", () => {
    const html = render(
      <AdminUserDetailPanel
        detail={detail}
        selectedUser={user}
        onActivate={() => undefined}
        onCopyEmail={() => undefined}
        onDeactivate={() => undefined}
        onEdit={() => undefined}
        onLock={() => undefined}
        onUnlock={() => undefined}
      />,
    );

    expect(html).toContain("Estado de cuenta");
    expect(html).toContain("Acceso a aplicaciones");
    expect(html).toContain("Sucursales asignadas");
    expect(html).toContain("Este usuario no tiene roles asignados.");
    expect(html).toContain("Auditoria / timeline");
  });

  it("renders create and edit workflow controls", () => {
    const createHtml = render(
      <AdminUserWorkflowPanel
        detail={null}
        mode="create"
        options={filterOptions}
        onAddBranch={() => undefined}
        onCancel={() => undefined}
        onCreate={() => undefined}
        onUpdate={() => undefined}
      />,
    );
    expect(createHtml).toContain("Nuevo usuario");
    expect(createHtml).toContain("Contrasena temporal");
    expect(createHtml).toContain("Sucursales");

    const editHtml = render(
      <AdminUserWorkflowPanel
        detail={detail}
        mode="edit"
        options={filterOptions}
        onAddBranch={() => undefined}
        onCancel={() => undefined}
        onCreate={() => undefined}
        onUpdate={() => undefined}
      />,
    );
    expect(editHtml).toContain("Editar usuario");
    expect(editHtml).toContain("Agregar sucursal");
  });
});
