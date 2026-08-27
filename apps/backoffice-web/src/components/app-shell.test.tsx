import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { AppShell } from "./app-shell";

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, to }: { children: ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}));

describe("backoffice public shell release navigation", () => {
  it("shows technical health navigation in development", () => {
    const html = renderToString(
      <AppShell showDevelopmentNavigation={true}>Development</AppShell>,
    );

    expect(html).toContain('href="/health"');
    expect(html).toContain("Health");
  });

  it("does not show technical health navigation in production", () => {
    const html = renderToString(
      <AppShell showDevelopmentNavigation={false}>Production</AppShell>,
    );

    expect(html).not.toContain('href="/health"');
    expect(html).not.toContain(">Health<");
  });
});
