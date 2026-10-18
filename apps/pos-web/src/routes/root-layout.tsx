import { Outlet, useRouterState } from "@tanstack/react-router";

import { PosSessionBoundary } from "../features/auth/PosSessionBoundary";

import { StatusMessagesViewport } from "../components/status-messages";
import { PosProtectedLayout } from "../features/pos-bootstrap/pos-protected-layout";

function ContentLayout() {
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

export function RootLayout() {
  return <PosSessionBoundary><ContentLayout /></PosSessionBoundary>;
}
