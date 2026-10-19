import { isCommandIntentionPending } from "@zeromerma/api-client";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { PosButton } from "../../components/pos-foundations";
import { formatCurrency } from "../../lib/formatters";
import { usePosAuthStore } from "../auth/auth-store";
import { refundIntentions } from "./refund-command-intent";
import { useRefundIntention } from "./use-refund-intention";

export function RefundRecoveryPanel({ workstationId }: { workstationId: string }) {
  const { metadata, error } = useRefundIntention(workstationId);
  const user = usePosAuthStore((state) => state.user);
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  if (!error && !isCommandIntentionPending(metadata))
    return message ? <p role="status">{message}</p> : null;
  async function recover() {
    if (!metadata || metadata.userId !== user?.id || busy) return;
    setBusy(true);
    try {
      const result = await refundIntentions.recover(metadata);
      setMessage(
        `Entrega verificada: ${formatCurrency(result.amount_settled)}. Pendiente: ${formatCurrency(result.amount_pending)}. Revisa el historial antes de repetir dinero.`,
      );
      await queryClient.invalidateQueries();
    } catch (failure) {
      setMessage(failure instanceof Error ? failure.message : "El resultado sigue sin confirmar.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section role="alert" className="rounded-xl border border-amber-400 bg-amber-50 p-4">
      <h2 className="font-semibold">Entrega de reembolso por verificar</h2>
      <p>{error ?? "Consulta el resultado original antes de entregar dinero otra vez."}</p>
      {metadata ? <p className="break-all">Referencia: {metadata.key}</p> : null}
      {message ? <p>{message}</p> : null}
      {metadata ? (
        <PosButton disabled={busy || metadata.userId !== user?.id} onClick={() => void recover()}>
          Consultar entrega de reembolso
        </PosButton>
      ) : null}
    </section>
  );
}
