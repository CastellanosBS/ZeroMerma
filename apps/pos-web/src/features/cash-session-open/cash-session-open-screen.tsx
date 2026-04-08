import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "@tanstack/react-router";
import { useState } from "react";

import { OperationalStatus } from "../../components/operational-status";
import { Button } from "../../components/ui/button";
import { appEnv } from "../../env";
import type { CashSessionView, OpenCashSessionRequest } from "../../lib/api-contracts";
import { toOperationalErrorMessage } from "../../lib/http";
import { usePosAuthStore } from "../auth/auth-store";
import { bootstrapQueryKey, usePosBootstrapQuery } from "../pos-bootstrap/queries";
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

  const openCashSessionMutation = useMutation({
    mutationFn: (payload: OpenCashSessionRequest) =>
      openCashSession({
        accessToken: accessToken!,
        payload,
        requestId: crypto.randomUUID(),
      }),
    onSuccess: async (cashSession) => {
      setOpenedSession(cashSession);
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

  if (openedSession && (currentCashSessionQuery.isPending || currentCashSessionQuery.data === null)) {
    return (
      <CashSessionActiveState
        bootstrap={bootstrapQuery.data!}
        cashSession={openedSession}
        successMessage="Cash session opened successfully. Confirming the active register state."
      />
    );
  }

  if (bootstrapQuery.isPending || currentCashSessionQuery.isPending) {
    return (
      <OperationalStatus
        description="Retrieving the current workstation and cash-session state."
        title="Loading cash session"
      />
    );
  }

  if (bootstrapQuery.error) {
    return (
      <OperationalStatus
        action={<Button onClick={() => bootstrapQuery.refetch()}>Retry context load</Button>}
        description={toOperationalErrorMessage(
          bootstrapQuery.error,
          "Confirm the workstation configuration and branch assignment.",
        )}
        title="Workstation context is unavailable"
      />
    );
  }

  if (currentCashSessionQuery.error) {
    return (
      <OperationalStatus
        action={<Button onClick={() => currentCashSessionQuery.refetch()}>Retry session check</Button>}
        description={toOperationalErrorMessage(
          currentCashSessionQuery.error,
          "Confirm the API connection and retry the active-session check.",
        )}
        title="Current cash session is unavailable"
      />
    );
  }

  if (currentCashSessionQuery.data) {
    if (openedSession && currentCashSessionQuery.data.id === openedSession.id) {
      return (
        <CashSessionActiveState
          bootstrap={bootstrapQuery.data}
          cashSession={currentCashSessionQuery.data}
          successMessage="Cash session opened successfully."
        />
      );
    }

    return <Navigate to="/" />;
  }

  if (openedSession) {
    return (
      <CashSessionActiveState
        bootstrap={bootstrapQuery.data}
        cashSession={openedSession}
        successMessage="Cash session opened successfully. Confirming the active register state."
      />
    );
  }

  return (
    <CashSessionOpenForm
      bootstrap={bootstrapQuery.data}
      errorMessage={
        openCashSessionMutation.error
          ? toOperationalErrorMessage(
              openCashSessionMutation.error,
              "Cash session opening failed. Confirm the workstation state and retry.",
            )
          : undefined
      }
      isSubmitDisabled={openCashSessionMutation.isPending || openedSession !== null}
      onSubmit={async (values) => {
        openCashSessionMutation.reset();
        await openCashSessionMutation.mutateAsync({
          opening_amount: values.openingAmount,
          workstation_code: appEnv.VITE_POS_WORKSTATION_CODE,
        });
      }}
    />
  );
}
