import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "@tanstack/react-router";
import { useState } from "react";

import { PosErrorState, PosLoadingState } from "../../components/pos-feedback";
import { PosButton } from "../../components/pos-foundations";
import { appEnv } from "../../env";
import type { CashSessionView, OpenCashSessionRequest } from "../../lib/api-contracts";
import { toOperationalErrorMessage } from "../../lib/http";
import { usePosAuthStore } from "../auth/auth-store";
import { bootstrapQueryKey, usePosBootstrapQuery } from "../pos-bootstrap/queries";
import { useStatusMessageStore } from "../status-messages/store";
import { CashSessionActiveState } from "./cash-session-active-state";
import { openCashSession } from "./cash-session-api";
import { CashSessionOpenForm } from "./cash-session-open-form";
import { currentCashSessionQueryKey, useCurrentCashSessionQuery } from "./queries";

export function CashSessionOpenScreen() {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const bootstrapQuery = usePosBootstrapQuery();
  const currentCashSessionQuery = useCurrentCashSessionQuery();
  const queryClient = useQueryClient();
  const [openedSession, setOpenedSession] = useState<CashSessionView | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const showSuccess = useStatusMessageStore((state) => state.showSuccess);

  function createRequestId(scope: string): string {
    if (
      typeof globalThis.crypto !== "undefined" &&
      typeof globalThis.crypto.randomUUID === "function"
    ) {
      return `${scope}-${globalThis.crypto.randomUUID()}`;
    }

    return `${scope}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }
  const openCashSessionMutation = useMutation({
    mutationFn: (payload: OpenCashSessionRequest) =>
      openCashSession({
        accessToken: accessToken!,
        payload,
        requestId: createRequestId("cash-session-open"),
      }),
    onSuccess: async (cashSession) => {
      setOpenedSession(cashSession);
      setSubmitError(null);
      showSuccess("Caja abierta \u00b7 Turno iniciado");
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: bootstrapQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
        }),
        queryClient.invalidateQueries({
          queryKey: currentCashSessionQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
        }),
      ]);
    },
  });

  if (!accessToken) {
    return <Navigate to="/login" />;
  }

  if (
    openedSession &&
    (currentCashSessionQuery.isPending || currentCashSessionQuery.data === null)
  ) {
    return (
      <CashSessionActiveState
        bootstrap={bootstrapQuery.data!}
        cashSession={openedSession}
        description="La apertura quedo registrada y la estacion esta lista para vender."
        title="Caja abierta"
      />
    );
  }

  if (bootstrapQuery.isPending || currentCashSessionQuery.isPending) {
    return (
      <div className="grid min-h-0 lg:h-full lg:place-items-center">
        <div className="w-full max-w-[46rem]">
          <PosLoadingState
            description="Consultando la sucursal, la estacion y el estado actual de la caja."
            title="Cargando contexto de apertura"
          />
        </div>
      </div>
    );
  }

  if (bootstrapQuery.error) {
    return (
      <div className="grid min-h-0 lg:h-full lg:place-items-center">
        <div className="w-full max-w-[46rem]">
          <PosErrorState
            action={
              <PosButton onClick={() => bootstrapQuery.refetch()} variant="neutral">
                Reintentar
              </PosButton>
            }
            description={toOperationalErrorMessage(
              bootstrapQuery.error,
              "Confirma la configuracion de la estacion y la asignacion de sucursal.",
            )}
            title="El contexto de la estacion no esta disponible"
          />
        </div>
      </div>
    );
  }

  if (currentCashSessionQuery.error) {
    return (
      <div className="grid min-h-0 lg:h-full lg:place-items-center">
        <div className="w-full max-w-[46rem]">
          <PosErrorState
            action={
              <PosButton onClick={() => currentCashSessionQuery.refetch()} variant="neutral">
                Reintentar
              </PosButton>
            }
            description={toOperationalErrorMessage(
              currentCashSessionQuery.error,
              "Confirma la conexion con la API y vuelve a revisar la caja activa.",
            )}
            title="No fue posible consultar la caja actual"
          />
        </div>
      </div>
    );
  }

  if (currentCashSessionQuery.data) {
    return (
      <CashSessionActiveState
        bootstrap={bootstrapQuery.data}
        cashSession={currentCashSessionQuery.data}
        description="Esta caja ya esta abierta. Puedes continuar directamente al POS."
        title="Caja abierta"
      />
    );
  }

  if (openedSession) {
    return (
      <CashSessionActiveState
        bootstrap={bootstrapQuery.data}
        cashSession={openedSession}
        description="La apertura quedo registrada y la estacion esta lista para vender."
        title="Caja abierta"
      />
    );
  }

  return (
    <CashSessionOpenForm
      bootstrap={bootstrapQuery.data}
      isSubmitDisabled={openCashSessionMutation.isPending || openedSession !== null}
      onSubmit={async (values) => {
        openCashSessionMutation.reset();
        setSubmitError(null);

        try {
          await openCashSessionMutation.mutateAsync({
            opening_amount: values.openingAmount,
            workstation_code: appEnv.VITE_POS_WORKSTATION_CODE,
          });
        } catch (error) {
          setSubmitError(
            toOperationalErrorMessage(
              error,
              "No fue posible abrir la caja. Revisa el estado de la estacion e intentalo de nuevo.",
            ),
          );
        }
      }}
      submitError={submitError}
    />
  );
}
