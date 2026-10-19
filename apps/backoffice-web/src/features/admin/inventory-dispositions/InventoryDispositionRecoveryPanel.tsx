import { isCommandIntentionPending } from "@zeromerma/api-client";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useBackofficeAuthStore } from "../../auth/backoffice-auth-store";
import { dispositionIntentions } from "./disposition-command-intent";
import { useDispositionIntention } from "./use-disposition-intention";

export function InventoryDispositionRecoveryPanel() {
  const { metadata, error } = useDispositionIntention();
  const user = useBackofficeAuthStore((state) => state.user);
  const queries = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  if (!error && !isCommandIntentionPending(metadata))
    return message ? <p role="status">{message}</p> : null;
  async function recover(retry: boolean) {
    if (!metadata || user?.id !== metadata.userId || busy) return;
    setBusy(true);
    try {
      const result = await (retry
        ? dispositionIntentions.retry(metadata)
        : dispositionIntentions.recover(metadata));
      setMessage(
        `Disposicion confirmada: ${result.quantity} a ${result.destination}. Referencia ${result.operation_id}.`,
      );
      void queries.invalidateQueries();
    } catch (failure) {
      setMessage(
        failure instanceof Error ? failure.message : "No se pudo consultar la disposicion.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section role="alert" className="rounded-xl border border-amber-400 bg-amber-50 p-3">
      <h2 className="font-semibold">Disposicion fisica pendiente de confirmar</h2>
      <p>{error ?? "Consulta el resultado antes de mover nuevamente el producto."}</p>
      {metadata ? <p>Referencia: {metadata.key}</p> : null}
      {message ? <p>{message}</p> : null}
      {metadata ? (
        <div className="flex gap-3">
          <button
            type="button"
            disabled={busy || user?.id !== metadata.userId}
            onClick={() => void recover(false)}
          >
            Consultar disposicion fisica
          </button>
          {dispositionIntentions.hasBody(metadata.key) && metadata.status !== "CONFLICT" ? (
            <button
              type="button"
              disabled={busy || user?.id !== metadata.userId}
              onClick={() => void recover(true)}
            >
              Reintentar la misma disposicion
            </button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
