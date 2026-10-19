import { useEffect, useState } from "react";
import { PURCHASE_INTENTION_SCOPE, purchaseIntentions } from "./purchase-command-intent";

function read() {
  try {
    return { metadata: purchaseIntentions.read(PURCHASE_INTENTION_SCOPE), error: null };
  } catch (error) {
    return {
      metadata: null,
      error: error instanceof Error ? error.message : "No se puede leer la recuperación.",
    };
  }
}

export function usePurchaseIntention() {
  const [state, setState] = useState(read);
  useEffect(
    () => purchaseIntentions.subscribe(PURCHASE_INTENTION_SCOPE, () => setState(read())),
    [],
  );
  return state;
}
