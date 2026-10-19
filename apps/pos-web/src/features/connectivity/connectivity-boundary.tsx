import { useCallback, useEffect, type PropsWithChildren } from "react";
import { queryClient } from "../../lib/query-client";

import {
  checkLocalReadiness,
  observeLocalConnectivity,
  updateBrowserNetworkHint,
  useConnectivityStore,
} from "./connectivity-state";

export function ConnectivityBoundary({ children }: PropsWithChildren) {
  const { local, checking, browserNetworkHint } = useConnectivityStore();
  const verify = useCallback(() => {
    updateBrowserNetworkHint();
    const previous = useConnectivityStore.getState().local;
    void checkLocalReadiness().then((ready) => {
      if (ready && previous !== "ready") {
        // Refresh only reads. Pending commands retain their explicit recovery controls.
        void queryClient.invalidateQueries();
      }
    });
  }, []);
  useEffect(() => {
    const stop = observeLocalConnectivity();
    verify();
    const interval = window.setInterval(verify, 15_000);
    window.addEventListener("online", verify);
    window.addEventListener("offline", verify);
    window.addEventListener("focus", verify);
    return () => {
      stop();
      window.clearInterval(interval);
      window.removeEventListener("online", verify);
      window.removeEventListener("offline", verify);
      window.removeEventListener("focus", verify);
    };
  }, [verify]);

  const ready = local === "ready";
  const message = ready
    ? "Servidor local disponible. Internet externo: sin verificar."
    : local === "databaseUnavailable"
      ? "El servidor responde, pero su base de datos no está disponible para operar."
      : local === "unreachable"
        ? "No se pudo contactar al servidor local. Revisa la red del local y el servidor."
        : checking ? "Verificando el servidor local antes de operar." : "No se ha podido verificar la disponibilidad del servidor local.";

  return <div className="pos-runtime">
    <aside aria-label="Conectividad del punto de venta" className="pos-connectivity" data-ready={ready}>
      <div aria-live="polite" aria-atomic="true">
        <span>{message}</span>
        {!ready ? <p>Las operaciones nuevas están bloqueadas. Las ya enviadas pueden estar confirmadas: consulta su resultado al recuperar la conexión. No vuelvas a cobrar.</p> : null}
        {browserNetworkHint === false ? <p>El navegador informa un corte de red. Si el servidor local responde, puedes operar por la red del local.</p> : null}
      </div>
      <button type="button" disabled={checking} onClick={verify}>
        {checking ? "Verificando conexión…" : "Verificar conexión"}
      </button>
    </aside>
    <div className="pos-runtime-content">{children}</div>
  </div>;
}
