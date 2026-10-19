import { useEffect, useRef, useState } from "react";
import { operationIntentions, type OperationIntentionMetadata } from "./operation-command-intent";

function snapshot(scope: string) {
  try {
    return { metadata: operationIntentions.read(scope), error: null };
  } catch {
    return {
      metadata: null,
      error:
        "No se pueden leer los datos de recuperación del movimiento. No repitas el movimiento.",
    };
  }
}
export function useOperationIntention(scope: string) {
  const [state, setState] = useState(() => snapshot(scope));
  useEffect(() => {
    const update = () => setState(snapshot(scope));
    update();
    return operationIntentions.subscribe(scope, update);
  }, [scope]);
  return state;
}

/** A rejected command preserves editable input; only a confirmed new identity clears the draft. */
export function useOperationDraftIdentity(
  metadata: OperationIntentionMetadata | null,
  enabled: boolean,
  onConfirmed: () => void,
) {
  const observedKey = useRef<string | null | undefined>(undefined);
  useEffect(() => {
    if (!enabled) return;
    const key = metadata?.key ?? null;
    if (observedKey.current === undefined) {
      // A mounted pending identity has not yet invalidated any draft prepared on this screen.
      observedKey.current =
        metadata?.status === "CONFIRMED" || metadata?.status === "REJECTED" ? key : null;
    } else if (metadata?.status === "CONFIRMED") {
      if (key !== observedKey.current) onConfirmed();
      observedKey.current = key;
    } else if (metadata?.status === "REJECTED") observedKey.current = key;
  }, [enabled, metadata?.key, metadata?.status, onConfirmed]);
  return observedKey;
}
