import { withCapabilities } from "../../../test-support/authorization";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminRoleDetailPanel } from "./components/AdminRoleDetailPanel";
import { AdminRolesPermissionsFilters } from "./components/AdminRolesPermissionsFilters";
import { AdminRolesPermissionsTable } from "./components/AdminRolesPermissionsTable";
import { AdminRoleWorkflowPanel } from "./components/AdminRoleWorkflowPanel";
import { AdminRolesPermissionsPage } from "./pages/AdminRolesPermissionsPage";
import type {
  AdminPermissionGroup,
  AdminRoleDetail,
  AdminRoleFilterOptions,
  AdminRoleListFilters,
  AdminRoleListItem,
} from "./types";

const filterOptions: AdminRoleFilterOptions = {
  appSurfaces: [{ id: "BACKOFFICE", label: "Backoffice" }],
  hasUsers: [{ id: "yes", label: "Con usuarios" }],
  highPrivilege: [{ id: "yes", label: "Alto privilegio" }],
  permissionModules: [{ id: "control", label: "Control" }],
  statuses: [{ id: "active", label: "Activos" }],
  systemStates: [{ id: "system", label: "Sistema" }],
  warningStates: [{ id: "with_warnings", label: "Con advertencias" }],
};

const filters: AdminRoleListFilters = {
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

const role: AdminRoleListItem = {
  assignedUserCount: 1,
  code: "admin",
  description: "Acceso administrativo completo.",
  id: "role-1",
  isHighPrivilege: true,
  isSystem: true,
  name: "Administrador",
  permissionCount: 1,
  scopeSummary: "Sin restricciones de alcance configuradas.",
  status: "active",
  surfaces: ["BACKOFFICE"],
  updatedAt: "2026-05-22T10:00:00Z",
  warningState: "warning",
  warnings: [],
};

const permissionGroups: AdminPermissionGroup[] = [
  {
    label: "Control",
    module: "control",
    permissions: [
      {
        action: "manage",
        code: "roles.manage",
        description: "Permite modificar roles.",
        id: "permission-1",
        isEnabled: true,
        isSensitive: true,
        label: "Gestionar roles",
        module: "control",
        moduleLabel: "Control",
        surfaces: ["BACKOFFICE"],
      },
    ],
  },
];

const detail: AdminRoleDetail = {
  accessSurfaces: {
    backofficeEnabled: true,
    grantsBothSurfaces: false,
    note: "Surface note",
    posEnabled: false,
    surfaces: ["BACKOFFICE"],
  },
  assignedUsers: [
    {
      scopeType: "GLOBAL",
      branchIds: [],
      assignedAt: "2026-05-22T10:00:00Z",
      branchSummary: "Main Branch",
      email: "admin@zeromerma.local",
      fullName: "ZeroMerma Admin",
      status: "active",
      surfaces: ["BACKOFFICE"],
      userId: "user-1",
    },
  ],
  auditHistory: [
    {
      action: "admin.role.created",
      actorId: "user-1",
      id: "audit-1",
      metadata: {},
      occurredAt: "2026-05-22T10:00:00Z",
    },
  ],
  availableActions: {
    canActivate: false,
    canAssignUsers: false,
    canDeactivate: false,
    canDelete: false,
    canDuplicate: false,
    canEdit: false,
    canOpenAudit: true,
    canRemoveUsers: false,
  },
  overview: { ...role, createdAt: "2026-05-22T10:00:00Z" },
  permissionMatrix: permissionGroups,
  scopes: {
    isSupported: false,
    missingContractNote: "Branch-scoped roles are not available yet.",
    scopeSummary: "Sin restricciones de alcance configuradas.",
  },
  sensitivePermissions: permissionGroups[0].permissions,
  warnings: [],
};

function render(element: ReactElement) {
  return renderToString(withCapabilities(element, ["roles.manage"]));
}

describe("admin roles and permissions UI components", () => {
  it("renders the page shell with the canonical action", () => {
    const queryClient = new QueryClient();
    const html = render(
      <QueryClientProvider client={queryClient}>
        <AdminRolesPermissionsPage />
      </QueryClientProvider>,
    );

    expect(html).toContain("Roles y permisos");
    expect(html).toContain("Nuevo rol");
    expect(html).toContain(
      "Selecciona un rol para revisar permisos, usuarios asignados y alcance operativo.",
    );
  });

  it("renders compact filter toolbar", () => {
    const html = render(
      <AdminRolesPermissionsFilters
        filters={filters}
        isBackendConnected={true}
        options={filterOptions}
        onChange={() => undefined}
      />,
    );

    expect(html).toContain("Buscar por rol o descripcion");
    expect(html).toContain("Filtros");
    expect(html).toContain("Backend conectado");
    expect(html).not.toContain("Alto privilegio");
  });

  it("renders empty and populated role table states", () => {
    const emptyHtml = render(
      <AdminRolesPermissionsTable
        page={1}
        pageSize={25}
        roles={[]}
        total={0}
        onCopyRole={() => undefined}
        onEdit={() => undefined}
        onPageChange={() => undefined}
        onSelectRole={() => undefined}
      />,
    );
    expect(emptyHtml).toContain("No hay roles registrados para los filtros seleccionados.");

    const tableHtml = render(
      <AdminRolesPermissionsTable
        page={1}
        pageSize={25}
        roles={[role]}
        total={1}
        onCopyRole={() => undefined}
        onEdit={() => undefined}
        onPageChange={() => undefined}
        onSelectRole={() => undefined}
      />,
    );
    expect(tableHtml).toContain("Administrador");
    expect(tableHtml).toContain("Backoffice");
    expect(tableHtml).toContain("Alto");
  });

  it("renders role detail sections", () => {
    const html = render(
      <AdminRoleDetailPanel
        detail={detail}
        selectedRole={role}
        onActivate={() => undefined}
        onCopyRole={() => undefined}
        onDeactivate={() => undefined}
        onEdit={() => undefined}
        onRemoveUser={() => undefined}
      />,
    );

    expect(html).toContain("Superficies de acceso");
    expect(html).toContain("Matriz de permisos");
    expect(html).toContain("Permisos sensibles");
    expect(html).toContain("Usuarios asignados");
    expect(html).toContain("Auditoria / historial");
  });

  it("renders create and edit workflow controls", () => {
    const createHtml = render(
      <AdminRoleWorkflowPanel
        detail={null}
        mode="create"
        permissionGroups={permissionGroups}
        sensitivePermissionCodes={["roles.manage"]}
        onCancel={() => undefined}
        onCreate={() => undefined}
        onUpdate={() => undefined}
      />,
    );
    expect(createHtml).toContain("Nuevo rol");
    expect(createHtml).toContain("Permisos por modulo");
    expect(createHtml).toContain("Confirmo que revise los permisos sensibles");

    const editHtml = render(
      <AdminRoleWorkflowPanel
        detail={detail}
        mode="edit"
        permissionGroups={permissionGroups}
        sensitivePermissionCodes={["roles.manage"]}
        onCancel={() => undefined}
        onCreate={() => undefined}
        onUpdate={() => undefined}
      />,
    );
    expect(editHtml).toContain("Editar rol");
    expect(editHtml).toContain("Gestionar roles");
  });
});
