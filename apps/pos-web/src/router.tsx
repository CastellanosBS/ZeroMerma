import { createRootRoute, createRoute, createRouter } from "@tanstack/react-router";

import { CashSessionOpenRoutePage } from "./routes/cash-session-open";
import { CorrectionsRoutePage } from "./routes/corrections";
import { DiscountsRoutePage } from "./routes/discounts";
import { HealthDemoPage } from "./routes/health-demo";
import { HomePage } from "./routes/home";
import { LoginRoutePage } from "./routes/login";
import { OrdersRoutePage } from "./routes/orders";
import { PassToCounterRoutePage } from "./routes/pass-to-counter";
import { PaymentsRoutePage } from "./routes/payments";
import { PosRoutePage } from "./routes/pos";
import { ReceiveTransferRoutePage } from "./routes/receive-transfer";
import { ReturnsRoutePage } from "./routes/returns";
import { RootLayout } from "./routes/root-layout";
import { SendToBranchRoutePage } from "./routes/send-to-branch";
import { ShiftCloseRoutePage } from "./routes/shift-close";
import { TicketsRoutePage } from "./routes/tickets";
import { WasteRoutePage } from "./routes/waste";

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

const posRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/pos",
  component: PosRoutePage,
});

const passToCounterRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/pasar-a-mostrador",
  component: PassToCounterRoutePage,
});

const sendToBranchRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/enviar-a-sucursal",
  component: SendToBranchRoutePage,
});

const receiveTransferRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/recibir-envio",
  component: ReceiveTransferRoutePage,
});

const ordersRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/pedidos",
  component: OrdersRoutePage,
});

const ticketsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/tickets",
  component: TicketsRoutePage,
});

const returnsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/devoluciones",
  component: ReturnsRoutePage,
});

const correctionsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/correcciones",
  component: CorrectionsRoutePage,
});

const wasteRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/registrar-merma",
  component: WasteRoutePage,
});

const paymentsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/pagos",
  component: PaymentsRoutePage,
});

const discountsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/descuentos",
  component: DiscountsRoutePage,
});

const shiftCloseRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/cerrar-turno",
  component: ShiftCloseRoutePage,
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
  posRoute,
  passToCounterRoute,
  sendToBranchRoute,
  receiveTransferRoute,
  ordersRoute,
  ticketsRoute,
  returnsRoute,
  correctionsRoute,
  wasteRoute,
  paymentsRoute,
  discountsRoute,
  shiftCloseRoute,
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
