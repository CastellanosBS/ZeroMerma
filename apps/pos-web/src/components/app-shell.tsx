import { Link } from "@tanstack/react-router";
import type { PropsWithChildren } from "react";

import { Button } from "../components/ui/button";
import { usePosShellStore } from "../stores/use-pos-shell-store";

export function AppShell({ children }: PropsWithChildren) {
  const branchName = usePosShellStore((state) => state.branchName);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-4">
          <div>
            <p className="text-sm font-medium uppercase tracking-wide text-green-800">
              ZeroMerma POS
            </p>
            <p className="text-lg font-semibold">{branchName}</p>
          </div>
          <nav className="flex items-center gap-2">
            <Link className="rounded-md px-3 py-2 text-sm font-medium hover:bg-slate-100" to="/">
              Register
            </Link>
            <Link
              className="rounded-md px-3 py-2 text-sm font-medium hover:bg-slate-100"
              to="/health"
            >
              Health
            </Link>
            <Button className="h-9">Cash session required</Button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  );
}
