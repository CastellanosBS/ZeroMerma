import {
  createRootRoute,
  createRoute,
  createRouter,
  Navigate,
  Outlet,
} from "@tanstack/react-router";

import { AppShell } from "./components/app-shell";
import { AdminAuditPage } from "./features/admin/audit/pages/AdminAuditPage";
import { adminModules } from "./features/admin/adminModules";
import {
  DEFAULT_ADMIN_RELEASE_PATH,
  getAdminModuleReleaseRedirect,
} from "./features/admin/releaseVisibility";
import { AdminCleaningLogsPage } from "./features/admin/cleaning-logs/pages/AdminCleaningLogsPage";
import { AdminModulePage } from "./features/admin/pages/AdminModulePage";
import { AdminBranchesPage } from "./features/admin/branches/pages/AdminBranchesPage";
import { AdminCashCutsPage } from "./features/admin/cash-cuts/pages/AdminCashCutsPage";
import { AdminCashFlowPage } from "./features/admin/cash-flow/pages/AdminCashFlowPage";
import { AdminClassesPage } from "./features/admin/classes/pages/AdminClassesPage";
import { AdminDiscountsPage } from "./features/admin/discounts/pages/AdminDiscountsPage";
import { AdminEquipmentMaintenancePage } from "./features/admin/equipment-maintenance/pages/AdminEquipmentMaintenancePage";
import { AdminIncidentsPage } from "./features/admin/incidents/pages/AdminIncidentsPage";
import { AdminInventoryPage } from "./features/admin/inventory/pages/AdminInventoryPage";
import { AdminInputsSuppliesPage } from "./features/admin/inputs-supplies/pages/AdminInputsSuppliesPage";
import { AdminOrdersPage } from "./features/admin/orders/pages/AdminOrdersPage";
import { AdminPricesPage } from "./features/admin/prices/pages/AdminPricesPage";
import { AdminProductionPage } from "./features/admin/production/pages/AdminProductionPage";
import { AdminProductsPage } from "./features/admin/products/pages/AdminProductsPage";
import { AdminPurchasesPage } from "./features/admin/purchases/pages/AdminPurchasesPage";
import { AdminReconciliationPage } from "./features/admin/reconciliation/pages/AdminReconciliationPage";
import { AdminRecipeCostsPage } from "./features/admin/recipes-costs/pages/AdminRecipeCostsPage";
import { AdminReportsPage } from "./features/admin/reports/pages/AdminReportsPage";
import { AdminReturnsCorrectionsPage } from "./features/admin/returns-corrections/pages/AdminReturnsCorrectionsPage";
import { AdminRolesPermissionsPage } from "./features/admin/roles-permissions/pages/AdminRolesPermissionsPage";
import { AdminSalesTicketsPage } from "./features/admin/sales-tickets/pages/AdminSalesTicketsPage";
import { AdminSanitaryVerificationsPage } from "./features/admin/sanitary-verifications/pages/AdminSanitaryVerificationsPage";
import { AdminSettingsPage } from "./features/admin/settings/pages/AdminSettingsPage";
import { AdminSuppliersPage } from "./features/admin/suppliers/pages/AdminSuppliersPage";
import { AdminTransfersPage } from "./features/admin/transfers/pages/AdminTransfersPage";
import { AdminUsersPage } from "./features/admin/users/pages/AdminUsersPage";
import { AdminWastePage } from "./features/admin/waste/pages/AdminWastePage";
import { AdminWorkstationsPage } from "./features/admin/workstations/pages/AdminWorkstationsPage";
import { BackofficeLoginPage } from "./features/auth/BackofficeLoginPage";
import { ProtectedAdminRoute } from "./features/auth/ProtectedAdminRoute";
import { AuthorizedAdminHome } from "./features/auth/AdminAccessDenied";
import { HealthDemoPage } from "./routes/health-demo";
import { HomePage } from "./routes/home";

const rootRoute = createRootRoute({
  component: Outlet,
});

export function getBackofficeDevelopmentRouteRedirect(
  pathname: "/" | "/health",
  isDevelopment: boolean,
) {
  return isDevelopment ? null : ("/login" as const);
}

function DevelopmentHomeRoute() {
  const redirect = getBackofficeDevelopmentRouteRedirect("/", import.meta.env.DEV);
  return redirect ? (
    <Navigate to={redirect} />
  ) : (
    <AppShell>
      <HomePage />
    </AppShell>
  );
}

function DevelopmentHealthRoute() {
  const redirect = getBackofficeDevelopmentRouteRedirect("/health", import.meta.env.DEV);
  return redirect ? (
    <Navigate to={redirect} />
  ) : (
    <AppShell>
      <HealthDemoPage />
    </AppShell>
  );
}

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: DevelopmentHomeRoute,
});

const healthRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/health",
  component: DevelopmentHealthRoute,
});

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  component: BackofficeLoginPage,
});

const adminRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/admin",
  component: ProtectedAdminRoute,
});

const adminIndexRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "/",
  component: AuthorizedAdminHome,
});

const adminModuleRoutes = adminModules.map((module) => {
  const releaseRedirect = getAdminModuleReleaseRedirect(module.key);
  return createRoute({
    getParentRoute: () => adminRoute,
    path: module.routeSlug,
    component: releaseRedirect
      ? AuthorizedAdminHome
      : module.key === "cleaningLogs"
        ? AdminCleaningLogsPage
        : module.key === "sanitaryChecks"
          ? AdminSanitaryVerificationsPage
          : module.key === "products"
            ? AdminProductsPage
            : module.key === "categories"
              ? AdminClassesPage
              : module.key === "recipesCosts"
                ? AdminRecipeCostsPage
                : module.key === "prices"
                  ? AdminPricesPage
                  : module.key === "discounts"
                    ? AdminDiscountsPage
                    : module.key === "sales"
                      ? AdminSalesTicketsPage
                      : module.key === "orders"
                        ? AdminOrdersPage
                        : module.key === "returnsCorrections"
                          ? AdminReturnsCorrectionsPage
                          : module.key === "branches"
                            ? AdminBranchesPage
                            : module.key === "registersStations"
                              ? AdminWorkstationsPage
                              : module.key === "inventory"
                                ? AdminInventoryPage
                                : module.key === "transfers"
                                  ? AdminTransfersPage
                                  : module.key === "production"
                                    ? AdminProductionPage
                                    : module.key === "waste"
                                      ? AdminWastePage
                                      : module.key === "suppliers"
                                        ? AdminSuppliersPage
                                        : module.key === "purchases"
                                          ? AdminPurchasesPage
                                          : module.key === "suppliesConsumables"
                                            ? AdminInputsSuppliesPage
                                            : module.key === "cashCuts"
                                              ? AdminCashCutsPage
                                              : module.key === "reconciliation"
                                                ? AdminReconciliationPage
                                                : module.key === "cashFlow"
                                                  ? AdminCashFlowPage
                                                  : module.key === "incidents"
                                                    ? AdminIncidentsPage
                                                    : module.key === "equipmentMaintenance"
                                                      ? AdminEquipmentMaintenancePage
                                                      : module.key === "users"
                                                        ? AdminUsersPage
                                                        : module.key === "rolesPermissions"
                                                          ? AdminRolesPermissionsPage
                                                          : module.key === "audit"
                                                            ? AdminAuditPage
                                                            : module.key === "reports"
                                                              ? AdminReportsPage
                                                              : module.key === "settings"
                                                                ? AdminSettingsPage
                                                                : () => (
                                                                    <AdminModulePage
                                                                      moduleKey={module.key}
                                                                    />
                                                                  ),
  });
});

const legacyRolesRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "roles",
  component: () => <Navigate to={DEFAULT_ADMIN_RELEASE_PATH as never} />,
});

const legacyRegistersRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "cajas",
  component: () => <Navigate to={"/admin/cajas-estaciones" as never} />,
});

const legacySalesTicketsRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "ventas-tickets",
  component: () => <Navigate to={"/admin/ventas" as never} />,
});

const legacyPurchasesRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "compras",
  component: () => <Navigate to={"/admin/compras-entradas" as never} />,
});

const adminRouteTree = adminRoute.addChildren([
  adminIndexRoute,
  ...adminModuleRoutes,
  legacyRolesRoute,
  legacyRegistersRoute,
  legacySalesTicketsRoute,
  legacyPurchasesRoute,
]);

const routeTree = rootRoute.addChildren([indexRoute, healthRoute, loginRoute, adminRouteTree]);

export const router = createRouter({
  routeTree,
  defaultPreload: "intent",
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
