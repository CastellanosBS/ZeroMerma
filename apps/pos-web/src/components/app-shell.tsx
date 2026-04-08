import { Link } from "@tanstack/react-router";
import type { PropsWithChildren } from "react";

import { Button } from "../components/ui/button";

interface AppShellProps extends PropsWithChildren {
  branchName: string;
  localDateTime: string;
  operatorName: string;
  onSignOut: () => void;
  workstationName: string;
}

export function AppShell({
  branchName,
  children,
  localDateTime,
  operatorName,
  onSignOut,
  workstationName,
}: AppShellProps) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-start justify-between gap-4 px-4 py-4">
          <div className="grid gap-3">
            <p className="text-sm font-medium uppercase tracking-wide text-green-800">
              ZeroMerma POS
            </p>
            <div className="grid gap-1">
              <p className="text-lg font-semibold">{branchName}</p>
              <p className="text-sm text-slate-700">{workstationName}</p>
            </div>
          </div>
          <div className="grid gap-3 text-sm text-slate-700">
            <div className="grid gap-1">
              <span className="font-medium text-slate-900">{operatorName}</span>
              <span>{localDateTime}</span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Link className="rounded-md px-3 py-2 text-sm font-medium hover:bg-slate-100" to="/">
                Register
              </Link>
              <Link
                className="rounded-md px-3 py-2 text-sm font-medium hover:bg-slate-100"
                to="/health"
              >
                Health
              </Link>
              <Button
                className="h-9 border-slate-300 bg-white text-slate-900 hover:bg-slate-100"
                onClick={onSignOut}
              >
                Sign out
              </Button>
            </div>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  );
}
