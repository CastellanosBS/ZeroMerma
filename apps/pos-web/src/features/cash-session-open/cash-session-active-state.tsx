import type { CashSessionView, PosBootstrapResponse } from "../../lib/api-contracts";
import { formatCurrency, formatLocalDateTime } from "../../lib/formatters";

export function CashSessionActiveState({
  bootstrap,
  cashSession,
  successMessage,
}: {
  bootstrap: PosBootstrapResponse;
  cashSession: CashSessionView;
  successMessage?: string;
}) {
  return (
    <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
      <div className="rounded-lg border border-emerald-200 bg-white p-6 shadow-sm">
        <p className="text-sm font-medium uppercase tracking-wide text-emerald-800">
          Cash session active
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-950">Register ready</h1>
        <p className="mt-4 text-sm leading-6 text-slate-700">
          {successMessage ?? "The operator and workstation are ready for sales operations."}
        </p>

        <dl className="mt-8 grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-slate-600">Opening amount</dt>
            <dd className="mt-1 text-2xl font-semibold text-slate-950">
              {formatCurrency(cashSession.opening_amount)}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Opened at</dt>
            <dd className="mt-1 text-lg font-semibold text-slate-950">
              {formatLocalDateTime(cashSession.opened_at, bootstrap.branch.timezone)}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Branch</dt>
            <dd className="mt-1 text-lg font-semibold text-slate-950">{bootstrap.branch.name}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Workstation</dt>
            <dd className="mt-1 text-lg font-semibold text-slate-950">
              {bootstrap.workstation.name}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Operator</dt>
            <dd className="mt-1 text-lg font-semibold text-slate-950">{bootstrap.user.full_name}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Session status</dt>
            <dd className="mt-1 text-lg font-semibold text-emerald-800">{cashSession.status}</dd>
          </div>
        </dl>
      </div>

      <aside className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-950">Current POS context</h2>
        <dl className="mt-4 grid gap-4">
          <div>
            <dt className="text-sm font-medium text-slate-600">Operator</dt>
            <dd className="mt-1 text-sm text-slate-900">{bootstrap.user.full_name}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Workstation</dt>
            <dd className="mt-1 text-sm text-slate-900">{bootstrap.workstation.name}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Local date and time</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {formatLocalDateTime(bootstrap.local_timestamp, bootstrap.branch.timezone)}
            </dd>
          </div>
        </dl>
      </aside>
    </section>
  );
}
