import { isCommandIntentionPending } from "@zeromerma/api-client";
import { cashIntentions } from "../cash-commands/cash-command-intent";
import { useCashIntention, useCashDraftIdentity } from "../cash-commands/use-cash-intention";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Navigate, useNavigate } from "@tanstack/react-router";
import { useCallback, useState } from "react";

import { PosErrorState, PosLoadingState } from "../../components/pos-feedback";
import { PosButton } from "../../components/pos-foundations";
import { appEnv } from "../../env";
import type { OpenCashSessionRequest } from "../../lib/api-contracts";
import { toOperationalErrorMessage } from "../../lib/http";
import { usePosAuthStore } from "../auth/auth-store";
import { bootstrapQueryKey, usePosBootstrapQuery } from "../pos-bootstrap/queries";
import { useStatusMessageStore } from "../status-messages/store";
import { CashSessionOpenForm } from "./cash-session-open-form";
import { currentCashSessionQueryKey, useCurrentCashSessionQuery } from "./queries";

export function CashSessionOpenScreen() {
  const navigate = useNavigate();
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);
  const bootstrapQuery = usePosBootstrapQuery();
  const currentCashSessionQuery = useCurrentCashSessionQuery();
  const queryClient = useQueryClient();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const showSuccess = useStatusMessageStore((state) => state.showSuccess);

  const { metadata, error: intentionError } = useCashIntention(
    bootstrapQuery.data?.workstation.id ?? "",
  );
  const [formVersion, setFormVersion] = useState(0);
  const clearDraft = useCallback(() => setFormVersion((version) => version + 1), []);
  const observedKey = useCashDraftIdentity(metadata, Boolean(bootstrapQuery.data), clearDraft);
  const isIntentionBlocked = Boolean(intentionError) || isCommandIntentionPending(metadata);
  const openCashSessionMutation = useMutation({
    mutationFn: (payload: OpenCashSessionRequest) => {
      const bootstrap = bootstrapQuery.data;
      if (!bootstrap) throw new Error("Espera el contexto de la estación.");
      return cashIntentions.begin(
        {
          userId: bootstrap.user.id,
          branchId: bootstrap.branch.id,
          workstationId: bootstrap.workstation.id,
          workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
          cashSessionId: null,
          commandCode: "open",
        },
        payload,
        observedKey.current ?? null,
      );
    },
    onSuccess: () => {
      setSubmitError(null);
      showSuccess("Caja abierta \u00b7 Turno iniciado");
      void Promise.all([
        queryClient.invalidateQueries({
          queryKey: bootstrapQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
        }),
        queryClient.invalidateQueries({
          queryKey: currentCashSessionQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
        }),
      ]);
      void navigate({ to: "/pos" });
    },
  });

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
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
    return <Navigate to="/pos" />;
  }

  return (
    <CashSessionOpenForm
      key={formVersion}
      bootstrap={bootstrapQuery.data}
      isSubmitDisabled={openCashSessionMutation.isPending || isIntentionBlocked}
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
      submitError={intentionError ?? submitError}
    />
  );
}
