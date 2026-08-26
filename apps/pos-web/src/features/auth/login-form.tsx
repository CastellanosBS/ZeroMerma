import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { Navigate, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { PosInlineValidationMessage } from "../../components/pos-feedback";
import { PosButton, PosFieldLabel, PosPanel, PosSectionTitle } from "../../components/pos-foundations";
import { ProgressStepper } from "../../components/pos-module-primitives";
import { appEnv } from "../../env";
import type { LoginRequest } from "../../lib/api-contracts";
import { ApiError, toOperationalErrorMessage } from "../../lib/http";
import { cn } from "../../lib/utils";
import { useFocusFlow } from "../pos-shell/keyboard";
import { posInputClass } from "../pos-theme/theme";
import { loginOperator } from "./auth-api";
import { buildBackofficeAdminUrl, shouldRouteToBackoffice } from "./auth-surfaces";
import { usePosAuthStore } from "./auth-store";

const loginSchema = z.object({
  email: z.string().trim().min(1, "Ingresa el correo del cajero."),
  password: z.string().min(1, "Ingresa la contrasena."),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export function LoginForm() {
  const navigate = useNavigate();
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const setAccessToken = usePosAuthStore((state) => state.setAccessToken);
  const [formError, setFormError] = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const passwordInputRef = useRef<HTMLInputElement | null>(null);
  const { scopeProps } = useFocusFlow({
    containerRef: formRef,
  });
  const {
    clearErrors,
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
    setError,
    setFocus,
    trigger,
  } = useForm<LoginFormValues>({
    defaultValues: {
      email: "",
      password: "",
    },
    resolver: zodResolver(loginSchema),
  });

  const loginMutation = useMutation({
    mutationFn: (payload: LoginRequest) => loginOperator(payload),
    onSuccess: async (response) => {
      if (shouldRouteToBackoffice(response.user)) {
        window.location.assign(
          buildBackofficeAdminUrl(appEnv.VITE_BACKOFFICE_BASE_URL, response.access_token),
        );
        return;
      }

      setAccessToken(response.access_token);
      await navigate({ to: "/" });
    },
  });

  useEffect(() => {
    if (!accessToken) {
      setFocus("email");
    }
  }, [accessToken, setFocus]);

  if (accessToken) {
    return <Navigate to="/" />;
  }

  const submitLogin = handleSubmit(async (values) => {
    loginMutation.reset();
    setFormError(null);

    try {
      await loginMutation.mutateAsync({
        email: values.email.trim(),
        password: values.password,
      });
    } catch (error) {
      if (error instanceof ApiError && error.statusCode === 401) {
        setError("password", {
          message: "Verifica el correo y la contrasena.",
          type: "server",
        });
        passwordInputRef.current?.focus();
        return;
      }

      setFormError(
        toOperationalErrorMessage(
          error,
          "No fue posible iniciar sesion. Verifica las credenciales y la conexion con la API.",
        ),
      );
    }
  });

  const emailField = register("email", {
    onChange: () => {
      setFormError(null);
      clearErrors("email");
    },
  });
  const passwordField = register("password", {
    onChange: () => {
      setFormError(null);
      clearErrors("password");
    },
  });

  return (
    <section className="mx-auto grid min-h-screen max-w-4xl place-items-center px-4 py-10">
      <div className="w-full max-w-[39rem]">
        <PosPanel className="px-6 py-6 sm:px-7 sm:py-7">
          <PosSectionTitle
            description="Inicia sesion para confirmar la estacion y abrir la caja."
            eyebrow="Identidad de cajero"
            title="Acceso del cajero"
          />

          <div className="mt-3">
            <ProgressStepper
              currentLabel="Cajero"
              currentStep={1}
              stepLabels={["Cajero", "Estacion", "Apertura"]}
              totalSteps={3}
            />
          </div>

          <form className="mt-6 grid gap-4" onSubmit={submitLogin} ref={formRef} {...scopeProps}>
            <div className="grid gap-2">
              <PosFieldLabel htmlFor="cashier-email">Correo</PosFieldLabel>
              <input
                {...emailField}
                autoComplete="username"
                className={cn(
                  posInputClass,
                  "h-12 rounded-[var(--pos-radius-control)] px-4 text-[15px]",
                )}
                id="cashier-email"
                onKeyDown={(event) => {
                  if (event.key !== "Enter" && event.key !== "NumpadEnter") {
                    return;
                  }

                  event.preventDefault();
                  void trigger("email").then((isValid) => {
                    if (isValid) {
                      passwordInputRef.current?.focus();
                    }
                  });
                }}
                placeholder="cashier@zeromerma.local"
                ref={(node) => {
                  emailField.ref(node);
                }}
              />
              {errors.email?.message ? (
                <PosInlineValidationMessage tone="error">
                  {errors.email.message}
                </PosInlineValidationMessage>
              ) : null}
            </div>

            <div className="grid gap-2">
              <PosFieldLabel htmlFor="cashier-password">Contrasena</PosFieldLabel>
              <input
                {...passwordField}
                autoComplete="current-password"
                className={cn(
                  posInputClass,
                  "h-12 rounded-[var(--pos-radius-control)] px-4 text-[15px]",
                )}
                id="cashier-password"
                onKeyDown={(event) => {
                  if (event.key !== "Enter" && event.key !== "NumpadEnter") {
                    return;
                  }

                  event.preventDefault();
                  void submitLogin();
                }}
                placeholder="Ingresa tu contrasena"
                ref={(node) => {
                  passwordField.ref(node);
                  passwordInputRef.current = node;
                }}
                type="password"
              />
              {errors.password?.message ? (
                <PosInlineValidationMessage tone="error">
                  {errors.password.message}
                </PosInlineValidationMessage>
              ) : null}
            </div>

            {formError ? (
              <PosInlineValidationMessage tone="error">{formError}</PosInlineValidationMessage>
            ) : null}

            <PosButton
              className="mt-1 h-12 w-full"
              disabled={isSubmitting || loginMutation.isPending}
              type="submit"
              variant="primary"
            >
              {loginMutation.isPending ? "Entrando..." : "Entrar"}
            </PosButton>
          </form>
        </PosPanel>
      </div>
    </section>
  );
}
