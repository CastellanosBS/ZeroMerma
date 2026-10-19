import { useEffect, useState } from "react";
import { refundIntentions } from "./refund-command-intent";

function snapshot(scope: string) {
  try {
    return { metadata: refundIntentions.read(scope), error: null };
  } catch {
    return {
      metadata: null,
      error:
        "No se puede leer la referencia pendiente. Solicita revisión antes de entregar dinero.",
    };
  }
}
export function useRefundIntention(scope: string) {
  const [stored, setStored] = useState(() => snapshot(scope));
  useEffect(() => {
    const update = () => setStored(snapshot(scope));
    update();
    return refundIntentions.subscribe(scope, update);
  }, [scope]);
  return stored;
}
