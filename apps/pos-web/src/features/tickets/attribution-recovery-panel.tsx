import { isCommandIntentionPending } from "@zeromerma/api-client";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { usePosAuthStore } from "../auth/auth-store";
import { attributionIntentions } from "./attribution-command-intent";
import { useAttributionIntention } from "./use-attribution-intention";

export function AttributionRecoveryPanel({ workstationId }: { workstationId: string }) {
  const { metadata, error } = useAttributionIntention(workstationId);
  const user = usePosAuthStore((state) => state.user);
  const queries = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  if (!error && !isCommandIntentionPending(metadata))
    return message ? <p role="status">{message}</p> : null;
  async function resolve(retry: boolean) {
    if (!metadata || metadata.userId !== user?.id || busy) return;
    setBusy(true);
    try {
      const result = await (retry
        ? attributionIntentions.retry(metadata)
        : attributionIntentions.recover(metadata));
      setMessage(
        `Atribucion confirmada. Referencia ${result.operation_id}. Consulta el pendiente actualizado del ticket.`,
      );
      void queries.invalidateQueries();
    } catch (failure) {
      setMessage(
        failure instanceof Error ? failure.message : "No fue posible consultar la atribucion.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section role="alert" className="rounded-xl border border-amber-400 bg-amber-50 p-3 text-sm">
      <h2 className="font-semibold">Atribucion fisica pendiente de confirmar</h2>
      <p>{error ?? "Consulta el resultado antes de atribuir otra cantidad."}</p>
      {metadata ? <p>Referencia: {metadata.key}</p> : null}
      {message ? <p>{message}</p> : null}
      {metadata ? (
        <div className="grid gap-2 mt-2">
          <button
            type="button"
            disabled={busy || metadata.userId !== user?.id}
            onClick={() => void resolve(false)}
          >
            Consultar atribucion fisica
          </button>
          {attributionIntentions.hasBody(metadata.key) && metadata.status !== "CONFLICT" ? (
            <button
              type="button"
              disabled={busy || metadata.userId !== user?.id}
              onClick={() => void resolve(true)}
            >
              Reintentar la misma atribucion
            </button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
