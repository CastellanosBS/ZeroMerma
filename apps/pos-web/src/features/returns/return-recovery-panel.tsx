import { isCommandIntentionPending } from "@zeromerma/api-client";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { usePosAuthStore } from "../auth/auth-store";
import { returnIntentions } from "./return-command-intent";
import { useReturnIntention } from "./use-return-intention";

export function ReturnRecoveryPanel({ workstationId }: { workstationId: string }) {
  const { metadata, error } = useReturnIntention(workstationId);
  const user = usePosAuthStore((state) => state.user);
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  if (!error && !isCommandIntentionPending(metadata))
    return message ? <p role="status">{message}</p> : null;
  async function resolve(retry: boolean) {
    if (!metadata || metadata.userId !== user?.id || busy) return;
    setBusy(true);
    try {
      const result = await (retry
        ? returnIntentions.retry(metadata)
        : returnIntentions.recover(metadata));
      setMessage(
        `Devolución ${result.folio} confirmada. No repitas el reembolso. Consulta su detalle en el historial.`,
      );
      void queryClient.invalidateQueries();
    } catch (failure) {
      setMessage(
        failure instanceof Error ? failure.message : "No fue posible recuperar el resultado.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section role="alert" className="rounded-xl border border-amber-400 bg-amber-50 p-4">
      <h2 className="font-semibold">Devolución pendiente de confirmar</h2>
      <p>
        {error ??
          "El resultado todavía no está confirmado. Conservamos la misma referencia; no entregues otro reembolso."}
      </p>
      {metadata ? <p>Referencia: {metadata.key}</p> : null}
      {message ? <p>{message}</p> : null}
      {metadata ? (
        <div className="flex gap-3 mt-3">
          <button
            type="button"
            disabled={busy || metadata.userId !== user?.id}
            onClick={() => void resolve(false)}
          >
            Consultar resultado de la devolución
          </button>
          {returnIntentions.hasBody(metadata.key) && metadata.status !== "CONFLICT" ? (
            <button
              type="button"
              disabled={busy || metadata.userId !== user?.id}
              onClick={() => void resolve(true)}
            >
              Reintentar la misma devolución
            </button>
          ) : (
            <p>Para continuar, primero confirma el resultado de esta devolución.</p>
          )}
        </div>
      ) : null}
    </section>
  );
}
