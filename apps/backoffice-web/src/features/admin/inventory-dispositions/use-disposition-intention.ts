import { useEffect, useRef, useState } from "react";
import {
  DISPOSITION_SCOPE,
  dispositionIntentions,
  type DispositionMetadata,
} from "./disposition-command-intent";

function snapshot() {
  try {
    return { metadata: dispositionIntentions.read(DISPOSITION_SCOPE), error: null };
  } catch {
    return {
      metadata: null,
      error: "No se puede leer la referencia de disposicion pendiente. No repitas el movimiento.",
    };
  }
}
export function useDispositionIntention() {
  const [state, setState] = useState(snapshot);
  useEffect(() => {
    const update = () => setState(snapshot());
    update();
    return dispositionIntentions.subscribe(DISPOSITION_SCOPE, update);
  }, []);
  return state;
}
export function useDispositionDraftIdentity(
  metadata: DispositionMetadata | null,
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
