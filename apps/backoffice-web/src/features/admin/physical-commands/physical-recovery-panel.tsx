import { isCommandIntentionPending } from "@zeromerma/api-client";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useBackofficeAuthStore } from "../../auth/backoffice-auth-store";
import { physicalIntentions, PHYSICAL_INTENTION_SCOPE } from "./physical-command-intent";
import { usePhysicalIntention } from "./use-physical-intention";

export function AdminPhysicalRecoveryPanel() {
  const { metadata, error } = usePhysicalIntention(PHYSICAL_INTENTION_SCOPE);
  const user = useBackofficeAuthStore((state) => state.user);
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
        ? physicalIntentions.retry(metadata)
        : physicalIntentions.recover(metadata));
      setMessage(
        `Movimiento de inventario ${"folio" in result ? result.folio : result.id} confirmada. No repitas el movimiento.`,
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
      <h2 className="font-semibold">Movimiento de inventario pendiente de confirmar</h2>
      <p>
        {error ??
          "El resultado todavía no está confirmado. Conservamos la misma referencia; no repitas el movimiento."}
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
            Consultar resultado del movimiento
          </button>
          {physicalIntentions.hasBody(metadata.key) && metadata.status !== "CONFLICT" ? (
            <button
              type="button"
              disabled={busy || metadata.userId !== user?.id}
              onClick={() => void resolve(true)}
            >
              Reintentar la misma operación
            </button>
          ) : (
            <p>Para continuar, primero confirma el resultado de esta operación.</p>
          )}
        </div>
      ) : null}
    </section>
  );
}
