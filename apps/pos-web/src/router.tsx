import { createRootRoute, createRoute, createRouter } from "@tanstack/react-router";

import { CashSessionOpenRoutePage } from "./routes/cash-session-open";
import { HealthDemoPage } from "./routes/health-demo";
import { HomePage } from "./routes/home";
import { LoginRoutePage } from "./routes/login";
import { RootLayout } from "./routes/root-layout";

const rootRoute = createRootRoute({
  component: RootLayout,
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: HomePage,
});

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  component: LoginRoutePage,
});

const cashSessionOpenRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/cash-session/open",
  component: CashSessionOpenRoutePage,
});

const healthRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/health",
  component: HealthDemoPage,
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  loginRoute,
  cashSessionOpenRoute,
  healthRoute,
]);

export const router = createRouter({
  routeTree,
  defaultPreload: "intent",
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
