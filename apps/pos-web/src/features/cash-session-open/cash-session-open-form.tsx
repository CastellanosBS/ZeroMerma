import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useRef } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { PosInlineValidationMessage } from "../../components/pos-feedback";
import {
  PosButton,
  PosFieldLabel,
  PosPanel,
  PosSectionTitle,
} from "../../components/pos-foundations";
import { ProgressStepper } from "../../components/pos-module-primitives";
import { ClockIcon, OperatorIcon, StationIcon } from "../../components/pos-icons";
import type { PosBootstrapResponse } from "../../lib/api-contracts";
import { cn } from "../../lib/utils";
import { useFocusFlow, useNumpadSubmit } from "../pos-shell/keyboard";
import { posInputClass } from "../pos-theme/theme";
import { CashSessionContextSummary } from "./cash-session-context-grid";

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
            description="Confirma la estacion activa y registra el efectivo inicial para empezar a vender."
            eyebrow="Apertura de caja"
            title="Registrar apertura"
          />

          <ProgressStepper
            currentLabel="Apertura"
            currentStep={3}
            stepLabels={["Cajero", "Estacion", "Apertura"]}
            totalSteps={3}
          />

          <CashSessionContextSummary
            groups={[
              {
                icon: <OperatorIcon className="h-4 w-4" />,
                items: [
                  {
                    className: "md:min-w-0",
                    key: "cashier",
                    label: "Cajero",
                    title: bootstrap.user.full_name,
                    value: bootstrap.user.full_name,
                  },
                ],
                key: "identity",
                title: "Identidad",
              },
              {
                icon: <StationIcon className="h-4 w-4" />,
                items: [
                  {
                    className: "md:min-w-0",
                    key: "branch",
                    label: "Sucursal",
                    title: bootstrap.branch.name,
                    value: bootstrap.branch.name,
                  },
                  {
                    className: "md:min-w-0",
                    key: "workstation",
                    label: "Caja",
                    title: bootstrap.workstation.name,
                    value: bootstrap.workstation.name,
                  },
                ],
                key: "location",
                title: "Ubicacion",
              },
              {
                icon: <ClockIcon className="h-4 w-4" />,
                items: [
                  {
                    className: "md:min-w-[8rem]",
                    key: "session-status",
                    label: "Estado",
                    title: "Apertura pendiente",
                    valueClassName: "overflow-visible",
                    value: (
                      <span className="inline-flex w-fit max-w-none whitespace-nowrap rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-[0.74rem] font-semibold leading-5 text-amber-800">
                        Pendiente
                      </span>
                    ),
                  },
                ],
                key: "session",
                title: "Sesion",
              },
            ]}
          />

          <form className="grid gap-4" onSubmit={submitOpening} ref={formRef} {...scopeProps}>
            <div className="grid gap-2">
              <PosFieldLabel
                helper="Captura el efectivo contado antes de la primera venta."
                htmlFor="opening-amount"
              >
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
