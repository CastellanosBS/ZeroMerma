import { useEffect, useRef, useState } from "react";
import { attributionIntentions, type AttributionMetadata } from "./attribution-command-intent";

function snapshot(scope: string) {
  try {
    return { metadata: attributionIntentions.read(scope), error: null };
  } catch {
    return {
      metadata: null,
      error: "No se puede leer la recuperacion de atribucion. No repitas la operacion.",
    };
  }
}
export function useAttributionIntention(scope: string) {
  const [state, setState] = useState(() => snapshot(scope));
  useEffect(() => {
    const update = () => setState(snapshot(scope));
    update();
    return attributionIntentions.subscribe(scope, update);
  }, [scope]);
  return state;
}
export function useAttributionDraftIdentity(
  metadata: AttributionMetadata | null,
  onConfirmed: () => void,
) {
  const observed = useRef<string | null | undefined>(undefined);
  useEffect(() => {
    const key = metadata?.key ?? null;
    if (observed.current === undefined)
      observed.current =
        metadata?.status === "CONFIRMED" || metadata?.status === "REJECTED" ? key : null;
    else if (metadata?.status === "CONFIRMED") {
      if (key !== observed.current) onConfirmed();
      observed.current = key;
    } else if (metadata?.status === "REJECTED") observed.current = key;
  }, [metadata?.key, metadata?.status, onConfirmed]);
  return observed;
}
