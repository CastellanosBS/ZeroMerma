import { Navigate } from "@tanstack/react-router";

import { OperationalStatus } from "../components/operational-status";
import { Button } from "../components/ui/button";
import { useCurrentCashSessionQuery } from "../features/cash-session-open/queries";
import { usePosBootstrapQuery } from "../features/pos-bootstrap/queries";
import { PosTerminalWorkspace } from "../features/pos-terminal/pos-terminal-workspace";
import { toOperationalErrorMessage } from "../lib/http";

export function PosRoutePage() {
  const bootstrapQuery = usePosBootstrapQuery();
  const currentCashSessionQuery = useCurrentCashSessionQuery();

  if (bootstrapQuery.isPending || currentCashSessionQuery.isPending) {
    return (
      <OperationalStatus
        description="Consultando el estado actual del punto de venta."
        title="Cargando POS"
      />
    );
  }

  if (bootstrapQuery.error) {
    return (
      <OperationalStatus
        action={<Button onClick={() => bootstrapQuery.refetch()}>Reintentar</Button>}
        description={toOperationalErrorMessage(
          bootstrapQuery.error,
          "Confirma la configuracion de la estacion y la asignacion de sucursal.",
        )}
        title="El contexto del POS no esta disponible"
      />
    );
  }

  if (currentCashSessionQuery.error) {
    return (
      <OperationalStatus
        action={<Button onClick={() => currentCashSessionQuery.refetch()}>Reintentar</Button>}
        description={toOperationalErrorMessage(
          currentCashSessionQuery.error,
          "Confirma la conexion con la API y el estado actual de la caja.",
        )}
        title="No fue posible consultar el estado del POS"
      />
    );
  }

  if (!currentCashSessionQuery.data) {
    return <Navigate to="/cash-session/open" />;
  }

  return <PosTerminalWorkspace />;
}
