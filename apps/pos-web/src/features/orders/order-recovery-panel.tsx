import { isCommandIntentionPending } from "@zeromerma/api-client";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { usePosAuthStore } from "../auth/auth-store";
import { orderIntentions } from "./order-command-intent";
import { useOrderIntention } from "./use-order-intention";

export function OrderRecoveryPanel({ workstationId }: { workstationId: string }) {
  const { metadata, error } = useOrderIntention(workstationId);
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
        ? orderIntentions.retry(metadata)
        : orderIntentions.recover(metadata));
      setMessage(`Pedido ${result.folio}: operación confirmada. No repitas el cobro.`);
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
      <h2 className="font-semibold">Pedido pendiente de confirmar</h2>
      <p>
        {error ??
          "El resultado todavía no está confirmado. Conservamos la misma referencia; no captures otro pedido ni repitas el pago."}
      </p>
      {metadata ? (
        <p>
          Referencia: {metadata.key} · {metadata.commandCode}
        </p>
      ) : null}
      {message ? <p>{message}</p> : null}
      {metadata ? (
        <div className="flex gap-3 mt-3">
          <button
            type="button"
            disabled={busy || metadata.userId !== user?.id}
            onClick={() => void resolve(false)}
          >
            Consultar resultado del pedido
          </button>
          {orderIntentions.hasBody(metadata.key) && metadata.status !== "CONFLICT" ? (
            <button
              type="button"
              disabled={busy || metadata.userId !== user?.id}
              onClick={() => void resolve(true)}
            >
              Reintentar el mismo comando
            </button>
          ) : (
            <p>
              Tras recargar sólo se consulta el resultado; no se vuelve a enviar el contenido
              perdido.
            </p>
          )}
        </div>
      ) : null}
    </section>
  );
}
