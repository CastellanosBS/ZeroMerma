import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToString } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const authState = vi.hoisted(() => ({
  accessToken: null as string | null,
  clearSession: vi.fn(),
  setAccessToken: vi.fn(),
}));
const getCurrentBackofficeUser = vi.hoisted(() => vi.fn());

vi.mock("@tanstack/react-router", () => ({
  Navigate: ({ to }: { to: string }) => <span data-navigate-to={to}>Navigate</span>,
  useNavigate: () => vi.fn(),
}));

vi.mock("../../lib/api", () => ({
  getCurrentBackofficeUser,
  loginBackofficeUser: vi.fn(),
  toBackofficeErrorMessage: (_error: unknown, fallback: string) => fallback,
}));

vi.mock("./backoffice-auth-store", () => ({
  useBackofficeAuthStore: (selector: (state: typeof authState) => unknown) => selector(authState),
}));

vi.mock("../admin/layout/AdminLayout", () => ({
  AdminLayout: () => <main>Admin content</main>,
}));

import { BackofficeLoginPage } from "./BackofficeLoginPage";
import { ProtectedAdminRoute } from "./ProtectedAdminRoute";

function render(element: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return renderToString(
    <QueryClientProvider client={queryClient}>{element}</QueryClientProvider>,
  );
}

describe("ProtectedAdminRoute URL credential policy", () => {
  beforeEach(() => {
    authState.accessToken = null;
    authState.clearSession.mockClear();
    authState.setAccessToken.mockClear();
    getCurrentBackofficeUser.mockClear();
  });

  it.each([
    ["query", "http://localhost:5174/admin?access_token=query-secret"],
    ["fragment", "http://localhost:5174/admin#access_token=fragment-secret"],
  ])("does not authenticate from an access token in the %s", (_kind, url) => {
    vi.stubGlobal("window", {
      history: { replaceState: vi.fn() },
      location: { href: url },
    });

    const html = render(<ProtectedAdminRoute />);

    expect(html).toContain('data-navigate-to="/login"');
    expect(getCurrentBackofficeUser).not.toHaveBeenCalled();
    expect(authState.setAccessToken).not.toHaveBeenCalled();
  });

  it("keeps the normal independent backoffice login available", () => {
    vi.stubGlobal("window", {
      history: { replaceState: vi.fn() },
      location: { href: "http://localhost:5174/login" },
    });

    const html = render(<BackofficeLoginPage />);

    expect(html).toContain("Acceso administrativo");
    expect(html).toContain("Entrar al backoffice");
  });
});
