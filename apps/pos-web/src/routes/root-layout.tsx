import { Outlet, useRouterState } from "@tanstack/react-router";

import { StatusMessagesViewport } from "../components/status-messages";
import { PosProtectedLayout } from "../features/pos-bootstrap/pos-protected-layout";

export function RootLayout() {
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  });
  const isPublicRoute = pathname === "/login" || pathname === "/health";

  if (isPublicRoute) {
    return (
      <>
        <StatusMessagesViewport />
        <Outlet />
      </>
    );
  }

  return (
    <>
      <StatusMessagesViewport />
      <PosProtectedLayout>
        <Outlet />
      </PosProtectedLayout>
    </>
  );
}
