import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { Navigate, useNavigate } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "../../components/ui/button";
import type { LoginRequest } from "../../lib/api-contracts";
import { toOperationalErrorMessage } from "../../lib/http";
import { loginOperator } from "./auth-api";
import { usePosAuthStore } from "./auth-store";

const loginSchema = z.object({
  email: z.string().trim().min(1, "Enter the operator email."),
  password: z.string().min(1, "Enter the operator password."),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export function LoginForm() {
  const navigate = useNavigate();
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const setAccessToken = usePosAuthStore((state) => state.setAccessToken);
  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
    setError,
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
      setAccessToken(response.access_token);
      await navigate({ to: "/" });
    },
  });

  if (accessToken) {
    return <Navigate to="/" />;
  }

  const onSubmit = handleSubmit(async (values) => {
    loginMutation.reset();

    try {
      await loginMutation.mutateAsync({
        email: values.email.trim(),
        password: values.password,
      });
    } catch (error) {
      setError("root", {
        message: toOperationalErrorMessage(
          error,
          "Login failed. Confirm the operator credentials and API connectivity.",
        ),
      });
    }
  });

  return (
    <section className="mx-auto flex min-h-screen max-w-md items-center px-4 py-10">
      <div className="w-full rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm font-medium uppercase tracking-wide text-green-800">ZeroMerma POS</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-950">Operator sign in</h1>
        <p className="mt-3 text-sm leading-6 text-slate-700">
          Sign in before opening the register for this workstation.
        </p>

        <form className="mt-8 grid gap-5" onSubmit={onSubmit}>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-slate-800">Operator email</span>
            <input
              {...register("email")}
              autoComplete="username"
              className="h-11 rounded-md border border-slate-300 px-3 text-sm text-slate-950 outline-none transition focus:border-green-700 focus:ring-2 focus:ring-green-700/20"
              placeholder="cashier@zeromerma.local"
            />
            {errors.email ? (
              <span className="text-sm text-rose-700">{errors.email.message}</span>
            ) : null}
          </label>

          <label className="grid gap-2">
            <span className="text-sm font-medium text-slate-800">Password</span>
            <input
              {...register("password")}
              autoComplete="current-password"
              className="h-11 rounded-md border border-slate-300 px-3 text-sm text-slate-950 outline-none transition focus:border-green-700 focus:ring-2 focus:ring-green-700/20"
              placeholder="Enter password"
              type="password"
            />
            {errors.password ? (
              <span className="text-sm text-rose-700">{errors.password.message}</span>
            ) : null}
          </label>

          {errors.root?.message ? (
            <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
              {errors.root.message}
            </div>
          ) : null}

          <Button className="h-11 w-full" disabled={isSubmitting || loginMutation.isPending} type="submit">
            {loginMutation.isPending ? "Signing in..." : "Sign in"}
          </Button>
        </form>
      </div>
    </section>
  );
}
