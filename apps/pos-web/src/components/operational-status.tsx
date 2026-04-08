import type { ReactNode } from "react";

interface OperationalStatusProps {
  action?: ReactNode;
  description: string;
  eyebrow?: string;
  title: string;
}

export function OperationalStatus({
  action,
  description,
  eyebrow = "ZeroMerma POS",
  title,
}: OperationalStatusProps) {
  return (
    <section className="mx-auto max-w-3xl rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-sm font-medium uppercase tracking-wide text-green-800">{eyebrow}</p>
      <h1 className="mt-2 text-3xl font-semibold text-slate-950">{title}</h1>
      <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-700">{description}</p>
      {action ? <div className="mt-6">{action}</div> : null}
    </section>
  );
}
