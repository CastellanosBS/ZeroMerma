import { useEffect, useState } from "react";
import { ADMIN_ORDER_INTENTION_SCOPE, adminOrderIntentions } from "./order-command-intent";
function snapshot() {
  try {
    return { metadata: adminOrderIntentions.read(ADMIN_ORDER_INTENTION_SCOPE), error: null };
  } catch {
    return {
      metadata: null,
      error: "No se pueden leer los datos de recuperación del pedido. No repitas la operación.",
    };
  }
}
export function useAdminOrderIntention() {
  const [state, setState] = useState(snapshot);
  useEffect(
    () => adminOrderIntentions.subscribe(ADMIN_ORDER_INTENTION_SCOPE, () => setState(snapshot())),
    [],
  );
  return state;
}
