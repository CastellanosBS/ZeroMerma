import { useEffect, useRef, useState } from "react";
import { orderIntentions, type OrderIntentionMetadata } from "./order-command-intent";

function snapshot(scope: string) {
  try {
    return { metadata: orderIntentions.read(scope), error: null };
  } catch {
    return {
      metadata: null,
      error: "No se pueden leer los datos de recuperación del pedido. No repitas la operación.",
    };
  }
}
export function useOrderIntention(scope: string) {
  const [state, setState] = useState(() => snapshot(scope));
  useEffect(() => {
    const update = () => setState(snapshot(scope));
    update();
    return orderIntentions.subscribe(scope, update);
  }, [scope]);
  return state;
}

/** Bind the visible draft to the last resolved identity without losing correctable input. */
export function useOrderDraftIdentity(
  metadata: OrderIntentionMetadata | null,
  enabled: boolean,
  onConfirmed: () => void,
) {
  const observedKey = useRef<string | null | undefined>(undefined);
  useEffect(() => {
    if (!enabled) return;
    const key = metadata?.key ?? null;
    if (observedKey.current === undefined) {
      observedKey.current = key;
      return;
    }
    if (metadata?.status === "CONFIRMED") {
      if (key !== observedKey.current) onConfirmed();
      observedKey.current = key;
    } else if (metadata?.status === "REJECTED") {
      // A deterministic first-send rejection permits correction of the same visible draft.
      observedKey.current = key;
    }
    // PENDING/UNKNOWN/CONFLICT keep the draft anchor; they never authorize a replacement.
  }, [enabled, metadata?.key, metadata?.status, onConfirmed]);
  return observedKey;
}
