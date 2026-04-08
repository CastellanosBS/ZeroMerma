import { useBackofficeShellStore } from "../stores/use-backoffice-shell-store";

export function HomePage() {
  const workspaceName = useBackofficeShellStore((state) => state.workspaceName);

  return (
    <section className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm font-medium uppercase tracking-wide text-green-800">Operations</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-950">Branch operations</h1>
        <p className="mt-4 max-w-2xl text-base leading-7 text-slate-700">
          Sensitive operations require audit entries and useful analytics traces.
        </p>
      </div>
      <aside className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold">Workspace</h2>
        <p className="mt-3 text-2xl font-semibold text-green-800">{workspaceName}</p>
        <p className="mt-3 text-sm leading-6 text-slate-700">
          Backend contracts are the source of truth for this application.
        </p>
      </aside>
    </section>
  );
}
