import type { CustomerOrderDetailResponse } from "../../lib/api-contracts";
import { formatCurrency } from "../../lib/formatters";

export function OrderPaymentHistory({
  payments,
}: {
  payments: CustomerOrderDetailResponse["payments"];
}) {
  if (payments.length === 0) return null;
  const labels: Record<string, string> = {
    ADVANCE: "Anticipo",
    SETTLEMENT: "Liquidación",
    REFUND: "Reembolso",
  };
  return (
    <details className="mt-3 rounded-xl border border-[var(--pos-shell-border)] bg-white p-3 text-sm">
      <summary className="cursor-pointer font-semibold">
        Pagos registrados ({payments.length})
      </summary>
      <div className="mt-2 grid gap-2">
        {payments.map((payment) => (
          <div key={payment.id} className="rounded-lg border border-slate-200 p-2">
            <p className="font-semibold">
              {labels[payment.payment_type] ?? payment.payment_type} ·{" "}
              {payment.payment_method_code === "CASH"
                ? "Efectivo"
                : payment.payment_method_code === "CARD"
                  ? "Tarjeta"
                  : payment.payment_method_code}{" "}
              · {formatCurrency(payment.amount)}
            </p>
            <p className="text-xs text-slate-600">
              {payment.recorded_by_user_full_name} ·{" "}
              {new Intl.DateTimeFormat("es-MX", { dateStyle: "short", timeStyle: "short" }).format(
                new Date(payment.recorded_at_utc),
              )}
            </p>
            {payment.payment_method_code === "CARD" ? (
              <p className="text-xs text-slate-600">
                Tarjeta registrada externamente; no afecta el efectivo ni confirma una captura del
                proveedor.
              </p>
            ) : null}
            <details className="mt-1 text-xs text-slate-600">
              <summary>Referencias del pago y turno</summary>
              <p className="break-all">Pago: {payment.id}</p>
              <p className="break-all">Turno: {payment.cash_session_id}</p>
              <p className="break-all">Estación: {payment.workstation_id}</p>
              {payment.financial_entry_id ? (
                <>
                  <p className="break-all">Operación: {payment.financial_operation_id}</p>
                  <p className="break-all">Asiento: {payment.financial_entry_id}</p>
                </>
              ) : (
                <p>
                  Registro anterior a la integración financiera; sin asiento financiero vinculado.
                </p>
              )}
            </details>
          </div>
        ))}
      </div>
    </details>
  );
}
