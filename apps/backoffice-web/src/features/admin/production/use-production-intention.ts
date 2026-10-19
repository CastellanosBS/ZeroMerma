import { useEffect, useState } from "react";
import { PRODUCTION_INTENTION_SCOPE, productionIntentions } from "./production-command-intent";

function snapshot() {
  try {
    return { metadata: productionIntentions.read(PRODUCTION_INTENTION_SCOPE), error: null };
  } catch {
    return {
      metadata: null,
      error:
        "No se puede leer la referencia de producción. Conserva los datos y solicita revisión.",
    };
  }
}

export function useProductionIntention() {
  const [state, setState] = useState(snapshot);
  useEffect(
    () => productionIntentions.subscribe(PRODUCTION_INTENTION_SCOPE, () => setState(snapshot())),
    [],
  );
  return state;
}
