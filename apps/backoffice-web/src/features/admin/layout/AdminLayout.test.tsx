import { withCapabilities } from "../../../test-support/authorization";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement, ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { AdminLayout } from "./AdminLayout";
import {
  ADMIN_SIDEBAR_COLLAPSED_STORAGE_KEY,
  getInitialAdminSidebarCollapsed,
} from "./adminSidebarPreferences";
import { adminNavigationSections } from "../navigation/adminNavigation";

vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    to,
    ...props
  }: {
    children: ReactNode;
    to: string;
    [key: string]: unknown;
  }) => (
    <a href={to} {...props}>
      {children}
    </a>
  ),
  Outlet: () => <div>Admin content</div>,
  useRouterState: () => "/admin/configuracion",
}));

function render(element: ReactElement) {
  return renderToString(withCapabilities(element, ["audit.view"]));
}

function renderLayout() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <AdminLayout />
    </QueryClientProvider>,
  );
}

describe("AdminLayout sidebar", () => {
  it("defaults to collapsed when no stored preference exists", () => {
    expect(getInitialAdminSidebarCollapsed(null)).toBe(true);
    expect(
      getInitialAdminSidebarCollapsed({
        getItem: () => null,
        setItem: () => undefined,
      }),
    ).toBe(true);
  });

  it("reads the persisted expanded preference", () => {
    expect(
      getInitialAdminSidebarCollapsed({
        getItem: (key) => (key === ADMIN_SIDEBAR_COLLAPSED_STORAGE_KEY ? "false" : null),
        setItem: () => undefined,
      }),
    ).toBe(false);
  });

  it("renders collapsed section-icon navigation and hamburger control by default", () => {
    const html = renderLayout();

    expect(html).toContain('aria-label="Toggle admin sidebar"');
    expect(html).toContain('aria-expanded="false"');
    expect(html).toContain("lg:grid-cols-[4.5rem_minmax(0,1fr)]");
    expect(html).toContain('aria-label="Control"');
    expect(html).toContain('title="Control"');
    expect(html).not.toContain('href="/admin/configuracion"');
  });

  it("assigns representative icons only to sections", () => {
    for (const section of adminNavigationSections) {
      expect(section.icon).toBeTruthy();
      for (const item of section.items) {
        expect("icon" in item).toBe(false);
      }
    }
  });
});
