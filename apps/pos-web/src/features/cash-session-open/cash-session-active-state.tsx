import { useNavigate } from "@tanstack/react-router";

import { PosButton, PosPanel, PosSectionTitle, PosStatusBadge } from "../../components/pos-foundations";
import { FlowGuide } from "../../components/pos-module-primitives";
import {
  CheckCircleIcon,
  ClockIcon,
  MoneyIcon,
  OperatorIcon,
  StationIcon,
} from "../../components/pos-icons";
import type { CashSessionView, PosBootstrapResponse } from "../../lib/api-contracts";
import { formatCurrency, formatLocalDateTime } from "../../lib/formatters";
import { CashSessionContextGrid } from "./cash-session-context-grid";

export function CashSessionActiveState({
  bootstrap,
  cashSession,
  description,
  title,
}: {
  bootstrap: PosBootstrapResponse;
  cashSession: CashSessionView;
  description: string;
  title: string;
}) {
  const navigate = useNavigate();

  return (
    <div className="grid min-h-0 lg:h-full lg:place-items-center">
      <div className="w-full max-w-[46rem]">
        <PosPanel className="grid gap-5 px-5 py-5 lg:px-6 lg:py-6">
          <PosSectionTitle
            action={<PosStatusBadge status="confirmed">Caja abierta</PosStatusBadge>}
            description={description}
            eyebrow="Sesion activa"
            title={title}
          />

          <FlowGuide
            activeStepKey="opening"
            steps={[
              { key: "identity", label: "Cajero", state: "completed" },
              { key: "station", label: "Estacion", state: "completed" },
              { key: "opening", label: "Apertura", state: "completed" },
            ]}
            variant="compact"
          />

          <CashSessionContextGrid
            items={[
              {
                icon: <OperatorIcon className="h-4 w-4" />,
                key: "cashier",
                label: "Cajero",
                value: bootstrap.user.full_name,
              },
              {
                icon: <StationIcon className="h-4 w-4" />,
                key: "branch",
                label: "Sucursal",
                value: bootstrap.branch.name,
              },
              {
                icon: <StationIcon className="h-4 w-4" />,
                key: "workstation",
                label: "Caja",
                value: bootstrap.workstation.name,
              },
              {
                icon: <CheckCircleIcon className="h-4 w-4" />,
                key: "session-status",
                label: "Estado de sesion",
                tone: "success",
                value: "Lista para vender",
              },
              {
                icon: <MoneyIcon className="h-4 w-4" />,
                key: "opening-amount",
                label: "Monto de apertura",
                value: formatCurrency(cashSession.opening_amount),
              },
              {
                icon: <ClockIcon className="h-4 w-4" />,
                key: "opened-at",
                label: "Hora de apertura",
                value: formatLocalDateTime(cashSession.opened_at, bootstrap.branch.timezone),
              },
            ]}
          />

          <div className="flex justify-start">
            <PosButton
              className="min-w-[11rem]"
              onClick={() => {
                void navigate({ to: "/pos" });
              }}
              variant="primary"
            >
              Ir al POS
            </PosButton>
          </div>
        </PosPanel>
      </div>
    </div>
  );
}
