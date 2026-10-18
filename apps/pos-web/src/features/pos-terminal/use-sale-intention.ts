import { useEffect, useState } from "react";
import {
  readSaleIntention,
  SALE_INTENTION_EVENT,
  SALE_INTENTION_STORAGE_PREFIX,
} from "./sale-confirmation-intent";

function snapshot(workstationId: string) {
  try {
    return { metadata: readSaleIntention(workstationId), error: null };
  } catch {
    return {
      metadata: null,
      error: "No se pueden leer los datos de recuperación. No inicies otro cobro en esta estación.",
    };
  }
}

export function useSaleIntention(workstationId: string) {
  const [state, setState] = useState(() => snapshot(workstationId));
  useEffect(() => {
    const update = () => setState(snapshot(workstationId));
    const onStorage = (event: StorageEvent) => {
      if (event.key === null || event.key === `${SALE_INTENTION_STORAGE_PREFIX}${workstationId}`)
        update();
    };
    update();
    window.addEventListener(SALE_INTENTION_EVENT, update);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener(SALE_INTENTION_EVENT, update);
      window.removeEventListener("storage", onStorage);
    };
  }, [workstationId]);
  return state;
}
