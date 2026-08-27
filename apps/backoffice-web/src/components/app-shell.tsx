import { Link } from "@tanstack/react-router";
import type { PropsWithChildren } from "react";

import { Button } from "../components/ui/button";
import { useBackofficeShellStore } from "../stores/use-backoffice-shell-store";

interface AppShellProps extends PropsWithChildren {
  showDevelopmentNavigation?: boolean;
}

export function AppShell({
  children,
  showDevelopmentNavigation = import.meta.env.DEV,
}: AppShellProps) {
  const workspaceName = useBackofficeShellStore((state) => state.workspaceName);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <header className="border-b border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)]">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-4">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-[var(--ui-color-primary)]">
              ZeroMerma Backoffice
            </p>
            <p className="text-lg font-semibold text-slate-950">{workspaceName}</p>
          </div>
          <nav className="flex items-center gap-2">
            <Link className="rounded-xl px-3 py-2 text-sm font-medium hover:bg-slate-100" to="/">
              Operations
            </Link>
            {showDevelopmentNavigation ? (
              <Link
                className="rounded-xl px-3 py-2 text-sm font-medium hover:bg-slate-100"
                to="/health"
              >
                Health
              </Link>
            ) : null}
            <Button className="h-9 rounded-xl">Audit required</Button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  );
}
