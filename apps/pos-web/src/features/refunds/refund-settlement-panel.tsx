import { isCommandIntentionPending } from "@zeromerma/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { PosButton } from "../../components/pos-foundations";
import { appEnv } from "../../env";
import { formatCurrency } from "../../lib/formatters";
import { toOperationalErrorMessage } from "../../lib/http";
import { usePosAuthStore } from "../auth/auth-store";
import { useCurrentCashSessionQuery } from "../cash-session-open/queries";
import {
  refundIntentions,
  type FinancialRefund,
  type RefundIntentionContext,
} from "./refund-command-intent";
import { useRefundIntention } from "./use-refund-intention";

export function RefundSettlementPanel({ refund }: { refund: FinancialRefund | null | undefined }) {
  const user = usePosAuthStore((state) => state.user);
  const cash = useCurrentCashSessionQuery().data;
  const queryClient = useQueryClient();
  const scope = cash?.workstation_id ?? "unavailable";
  const stored = useRefundIntention(scope);
  const metadata = stored.metadata;
  const pending = isCommandIntentionPending(metadata);
  const context: RefundIntentionContext | null =
    cash && user && refund
      ? {
          userId: user.id,
          branchId: cash.branch_id,
          workstationId: cash.workstation_id,
          workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
          cashSessionId: cash.id,
          sourceType: refund.source_type,
          sourceId: refund.source_id,
        }
      : null;
  const matches =
    context &&
    metadata &&
    context.userId === metadata.userId &&
    context.branchId === metadata.branchId &&
    context.workstationId === metadata.workstationId &&
    context.sourceId === metadata.sourceId &&
    context.sourceType === metadata.sourceType;
  const mutation = useMutation({
    mutationFn: async (action: "begin" | "recover" | "retry") => {
      if (!context || stored.error)
        throw new Error("Se requiere una caja abierta y el operador autorizado.");
      if (action !== "begin") {
        if (!matches || !metadata)
          throw new Error("Consulta la referencia con el operador y documento originales.");
        return action === "recover"
          ? refundIntentions.recover(metadata)
          : refundIntentions.retry(metadata);
      }
      return refundIntentions.begin(
        context,
        {
          workstation_code: context.workstationCode,
          cash_session_id: context.cashSessionId,
        },
        metadata?.key ?? null,
      );
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries();
    },
  });
  if (!refund)
    return (
      <p className="text-xs text-slate-600">
        Sin evidencia financiera del reembolso; requiere revisión.
      </p>
    );
  return (
    <section
      aria-label="Estado del reembolso"
      className="my-3 grid gap-2 rounded-xl border border-slate-200 bg-white p-3 text-sm"
    >
      <h3 className="font-semibold">Reembolso</h3>
      <p>Importe autorizado: {formatCurrency(refund.amount_due)}</p>
      <p>Entrega confirmada: {formatCurrency(refund.amount_settled)}</p>
      <p className="font-semibold">
        Pendiente de entregar: {formatCurrency(refund.amount_pending)}
      </p>
      {refund.entries.length > 0 ? (
        <details>
          <summary>Entregas y estado de los pagos</summary>
          <ul className="mt-2 space-y-2">
            {refund.entries.map((entry) => (
              <li key={entry.id}>
                {entry.payment_method_code === "CASH" ? "Efectivo" : "Tarjeta"} ·{" "}
                {formatCurrency(entry.amount)} ·{" "}
                {entry.state === "CONFIRMED" ? "Confirmado" : entry.state}
                <p className="break-all text-xs text-slate-600">
                  Turno: {entry.cash_session_id ?? "Sin turno asignado"}
                </p>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
      {stored.error ? <p role="alert">{stored.error}</p> : null}
      {pending ? (
        <div className="grid gap-2">
          <p>Hay una entrega por verificar. Conserva la referencia y no repitas el dinero.</p>
          <p className="break-all text-xs">Referencia: {metadata?.key}</p>
          {!matches ? (
            <p>Abre el documento original con el mismo operador para recuperar el resultado.</p>
          ) : (
            <>
              <PosButton disabled={mutation.isPending} onClick={() => mutation.mutate("recover")}>
                Consultar entrega pendiente
              </PosButton>
              {metadata &&
              refundIntentions.hasBody(metadata.key) &&
              metadata.status !== "CONFLICT" ? (
                <PosButton
                  disabled={mutation.isPending}
                  onClick={() => mutation.mutate("retry")}
                  variant="neutral"
                >
                  Reintentar la misma entrega
                </PosButton>
              ) : null}
            </>
          )}
        </div>
      ) : Number(refund.amount_pending) > 0 ? (
        <>
          <p className="text-xs text-slate-600">
            Se registrará sólo el efectivo disponible en la caja actual. El resto seguirá pendiente.
          </p>
          <PosButton
            disabled={!context || !!stored.error || mutation.isPending}
            onClick={() => mutation.mutate("begin")}
          >
            Continuar reembolso en efectivo
          </PosButton>
        </>
      ) : null}
      {mutation.error ? (
        <p role="alert">
          {toOperationalErrorMessage(
            mutation.error,
            "No se confirmó el resultado. Consulta la misma referencia antes de entregar dinero.",
          )}
        </p>
      ) : null}
      {mutation.isSuccess ? (
        <p role="status">
          Resultado verificado. Revisa las entregas registradas antes de entregar dinero otra vez.
        </p>
      ) : null}
    </section>
  );
}
