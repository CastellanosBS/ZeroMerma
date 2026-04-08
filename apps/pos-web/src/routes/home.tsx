import { usePosShellStore } from "../stores/use-pos-shell-store";

export function HomePage() {
  const branchName = usePosShellStore((state) => state.branchName);

  return (
    <section className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm font-medium uppercase tracking-wide text-green-800">Register</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-950">Cash session required</h1>
        <p className="mt-4 max-w-2xl text-base leading-7 text-slate-700">
          Sales operations start only after a cashier opens a branch cash session.
        </p>
      </div>
      <aside className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold">Current branch</h2>
        <p className="mt-3 text-2xl font-semibold text-green-800">{branchName}</p>
        <p className="mt-3 text-sm leading-6 text-slate-700">
          PRODUCT_DIRECT and CLASS_CAPTURE are the official sale capture modes.
        </p>
      </aside>
    </section>
  );
}
