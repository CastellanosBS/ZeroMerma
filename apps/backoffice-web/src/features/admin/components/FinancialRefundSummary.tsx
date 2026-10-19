import type { components } from "@zeromerma/api-client";

export function FinancialRefundSummary({
  refund,
}: {
  refund: components["schemas"]["FinancialRefundView"] | null | undefined;
}) {
  if (!refund) return null;
  const money = (amount: string) =>
    new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(Number(amount));
  return (
    <section
      aria-label="Estado financiero del reembolso"
      className="my-3 rounded-xl border border-slate-200 p-3 text-sm"
    >
      <h4 className="font-semibold">Estado del reembolso</h4>
      <p>Importe autorizado: {money(refund.amount_due)}</p>
      <p>Entrega confirmada: {money(refund.amount_settled)}</p>
      <p className="font-semibold">Pendiente de entregar: {money(refund.amount_pending)}</p>
      <p>Efectivo confirmado: {money(refund.cash_settled_amount)}</p>
      <p>Tarjeta confirmada: {money(refund.card_settled_amount)}</p>
      <details className="mt-2">
        <summary>Pagos y turnos reales</summary>
        <ul>
          {refund.entries.map((entry) => (
            <li className="my-2" key={entry.id}>
              {entry.payment_method_code === "CASH" ? "Efectivo" : "Tarjeta"} ·{" "}
              {money(entry.amount)} · {entry.state === "CONFIRMED" ? "Confirmado" : entry.state}
              <p className="break-all text-xs">
                Turno: {entry.cash_session_id ?? "Sin turno asignado"}
              </p>
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}
