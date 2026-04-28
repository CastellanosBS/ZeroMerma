import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useRef } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { PosInlineValidationMessage } from "../../components/pos-feedback";
import { PosButton, PosFieldLabel, PosPanel, PosSectionTitle, PosStatusBadge } from "../../components/pos-foundations";
import { FlowGuide } from "../../components/pos-module-primitives";
import {
  ClockIcon,
  MoneyIcon,
  OperatorIcon,
  StationIcon,
} from "../../components/pos-icons";
import type { PosBootstrapResponse } from "../../lib/api-contracts";
import { formatLocalDateTime } from "../../lib/formatters";
import { cn } from "../../lib/utils";
import { useFocusFlow, useNumpadSubmit } from "../pos-shell/keyboard";
import { posInputClass } from "../pos-theme/theme";
import { CashSessionContextGrid } from "./cash-session-context-grid";

const openCashSessionSchema = z.object({
  openingAmount: z
    .string()
    .trim()
    .min(1, "Ingresa el monto de apertura.")
    .regex(/^\d+(\.\d{1,2})?$/, "Usa solo numeros con hasta dos decimales."),
});

type OpenCashSessionFormValues = z.infer<typeof openCashSessionSchema>;

export function CashSessionOpenForm({
  bootstrap,
  isSubmitDisabled,
  onSubmit,
  submitError,
}: {
  bootstrap: PosBootstrapResponse;
  isSubmitDisabled: boolean;
  onSubmit: (values: OpenCashSessionFormValues) => Promise<void>;
  submitError?: string | null;
}) {
  const formRef = useRef<HTMLFormElement>(null);
  const openingAmountRef = useRef<HTMLInputElement | null>(null);
  const { scopeProps } = useFocusFlow({
    containerRef: formRef,
  });
  const {
    clearErrors,
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
    setFocus,
  } = useForm<OpenCashSessionFormValues>({
    defaultValues: {
      openingAmount: "",
    },
    resolver: zodResolver(openCashSessionSchema),
  });

  useEffect(() => {
    openingAmountRef.current?.focus();
    setFocus("openingAmount");
  }, [setFocus]);

  const submitOpening = handleSubmit(async (values) => {
    await onSubmit(values);
  });

  const amountSubmitHandler = useNumpadSubmit({
    onSubmit: () => {
      void submitOpening();
    },
  });

  const openingAmountField = register("openingAmount", {
    onChange: () => {
      clearErrors("openingAmount");
    },
  });

  return (
    <div className="grid min-h-0 lg:h-full lg:place-items-center">
      <div className="w-full max-w-[46rem]">
        <PosPanel className="grid gap-5 px-5 py-5 lg:px-6 lg:py-6">
          <PosSectionTitle
            action={<PosStatusBadge status="pending">Paso 3 de 3</PosStatusBadge>}
            description="Confirma la estacion activa y registra el efectivo inicial para empezar a vender."
            eyebrow="Apertura de caja"
            title="Registrar apertura"
          />

          <FlowGuide
            activeStepKey="opening"
            steps={[
              { key: "identity", label: "Cajero", state: "completed" },
              { key: "station", label: "Estacion", state: "completed" },
              { key: "opening", label: "Apertura", state: "current" },
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
                icon: <MoneyIcon className="h-4 w-4" />,
                key: "session-status",
                label: "Estado de sesion",
                tone: "warning",
                value: "Apertura pendiente",
              },
              {
                icon: <ClockIcon className="h-4 w-4" />,
                key: "local-time",
                label: "Hora local",
                value: formatLocalDateTime(bootstrap.local_timestamp, bootstrap.branch.timezone),
              },
            ]}
          />

          <form className="grid gap-4" onSubmit={submitOpening} ref={formRef} {...scopeProps}>
            <div className="grid gap-2">
              <PosFieldLabel helper="Captura el efectivo contado antes de la primera venta." htmlFor="opening-amount">
                Monto de apertura
              </PosFieldLabel>
              <input
                {...openingAmountField}
                className={cn(
                  posInputClass,
                  "h-20 rounded-[1.15rem] px-4 text-[2.2rem] font-semibold tracking-tight shadow-sm",
                )}
                id="opening-amount"
                inputMode="decimal"
                onKeyDown={amountSubmitHandler}
                placeholder="0.00"
                ref={(node) => {
                  openingAmountRef.current = node;
                  openingAmountField.ref(node);
                }}
              />
              {errors.openingAmount?.message ? (
                <PosInlineValidationMessage tone="error">
                  {errors.openingAmount.message}
                </PosInlineValidationMessage>
              ) : null}
            </div>

            {submitError ? (
              <PosInlineValidationMessage tone="error">{submitError}</PosInlineValidationMessage>
            ) : null}

            <PosButton
              className="h-12 w-full"
              disabled={isSubmitting || isSubmitDisabled}
              type="submit"
              variant="primary"
            >
              {isSubmitting || isSubmitDisabled ? "Abriendo caja..." : "Abrir caja"}
            </PosButton>
          </form>
        </PosPanel>
      </div>
    </div>
  );
}
