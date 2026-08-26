import { useMutation } from "@tanstack/react-query";
import { Navigate, useNavigate } from "@tanstack/react-router";
import type { FormEvent } from "react";
import { useEffect, useRef, useState } from "react";

import { loginBackofficeUser, toBackofficeErrorMessage } from "../../lib/api";
import { isBackofficeUser, redirectToPos } from "./auth-surfaces";
import { useBackofficeAuthStore } from "./backoffice-auth-store";

export function BackofficeLoginPage() {
  const navigate = useNavigate();
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const setAccessToken = useBackofficeAuthStore((state) => state.setAccessToken);
  const [email, setEmail] = useState("admin@zeromerma.local");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const passwordInputRef = useRef<HTMLInputElement>(null);

  const loginMutation = useMutation({
    mutationFn: loginBackofficeUser,
    onSuccess: async (response) => {
      if (!isBackofficeUser(response.user)) {
        redirectToPos();
        return;
      }

      setAccessToken(response.access_token);
      await navigate({ to: "/admin" });
    },
  });

  useEffect(() => {
    if (!accessToken) {
      passwordInputRef.current?.focus();
    }
  }, [accessToken]);

  if (accessToken) {
    return <Navigate to="/admin" />;
  }

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    loginMutation.reset();
    setFormError(null);

    const resolvedEmail = email.trim();
    if (!resolvedEmail || !password) {
      setFormError("Ingresa el correo y la contraseña.");
      return;
    }

    try {
      await loginMutation.mutateAsync({
        email: resolvedEmail,
        password,
      });
    } catch (error) {
      setFormError(
        toBackofficeErrorMessage(
          error,
          "No fue posible iniciar sesión. Verifica las credenciales y la conexión con la API.",
        ),
      );
      passwordInputRef.current?.focus();
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-slate-50 px-4 py-10 text-slate-950">
      <section className="w-full max-w-[30rem] overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)]">
        <div className="border-b border-[var(--ui-color-border)] px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[var(--ui-color-primary)] text-sm font-semibold text-white">
              ZM
            </div>
            <div>
              <h1 className="text-xl font-semibold text-slate-950">Acceso administrativo</h1>
              <p className="text-sm text-slate-600">Ingresa para abrir el backoffice.</p>
            </div>
          </div>
        </div>

        <form className="grid gap-4 px-6 py-6" onSubmit={submitLogin}>
          <label className="grid gap-2 text-sm font-semibold text-slate-700" htmlFor="admin-email">
            Correo
            <input
              autoComplete="username"
              className="h-11 rounded-2xl border border-[var(--ui-color-border)] bg-white px-4 text-sm font-medium text-slate-950 outline-none transition focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]"
              id="admin-email"
              placeholder="admin@zeromerma.local"
              type="email"
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                setFormError(null);
              }}
            />
          </label>

          <label className="grid gap-2 text-sm font-semibold text-slate-700" htmlFor="admin-password">
            Contraseña
            <input
              autoComplete="current-password"
              className="h-11 rounded-2xl border border-[var(--ui-color-border)] bg-white px-4 text-sm font-medium text-slate-950 outline-none transition focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]"
              id="admin-password"
              placeholder="Ingresa tu contraseña"
              ref={passwordInputRef}
              type="password"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
                setFormError(null);
              }}
            />
          </label>

          {formError ? (
            <p className="rounded-2xl border border-rose-200 bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm font-medium text-[var(--ui-color-danger)]">
              {formError}
            </p>
          ) : null}

          <button
            className="h-11 rounded-2xl bg-[var(--ui-color-primary)] px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--ui-color-primary-strong)] disabled:cursor-not-allowed disabled:bg-slate-300"
            disabled={loginMutation.isPending}
            type="submit"
          >
            {loginMutation.isPending ? "Entrando..." : "Entrar al backoffice"}
          </button>

          <p className="text-xs leading-5 text-slate-500">
            Usuario local: admin@zeromerma.local. La contraseña se define en el seed de desarrollo.
          </p>
        </form>
      </section>
    </main>
  );
}
