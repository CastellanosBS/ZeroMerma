import { Outlet, useRouterState } from "@tanstack/react-router";

import { PosProtectedLayout } from "../features/pos-bootstrap/pos-protected-layout";

export function RootLayout() {
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  });
  const isPublicRoute = pathname === "/login" || pathname === "/health";

  if (isPublicRoute) {
    return <Outlet />;
  }

  return (
    <PosProtectedLayout>
      <Outlet />
    </PosProtectedLayout>
  );
}
