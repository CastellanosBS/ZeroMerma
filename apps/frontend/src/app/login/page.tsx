"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/modules/auth/AuthProvider";
import { ApiClientError } from "@/services/http/errors";

function normalizeNextPath(rawValue: string | null): string {
    if (!rawValue) {
        return "/pos";
    }

    if (!rawValue.startsWith("/") || rawValue.startsWith("//")) {
        return "/pos";
    }

    return rawValue;
}

export default function LoginPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { status, session, login } = useAuth();

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const nextPath = useMemo(
        () => normalizeNextPath(searchParams.get("next")),
        [searchParams],
    );

    useEffect(() => {
        if (status === "authenticated" && session) {
            router.replace(nextPath);
        }
    }, [status, session, nextPath, router]);

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();

        if (isSubmitting) {
            return;
        }

        setIsSubmitting(true);
        setErrorMessage(null);

        try {
            await login({ email, password });
            router.replace(nextPath);
        } catch (error) {
            if (error instanceof ApiClientError) {
                setErrorMessage(error.message);
            } else {
                setErrorMessage("Unexpected error while signing in.");
            }
        } finally {
            setIsSubmitting(false);
        }
    }

    if (status === "loading") {
        return (
            <main className="min-h-screen bg-slate-100 px-6 py-10 text-slate-900">
                <div className="mx-auto max-w-md rounded-3xl bg-white p-8 shadow-sm">
                    <p className="text-sm text-slate-500">Loading session...</p>
                </div>
            </main>
        );
    }

    return (
        <main className="min-h-screen bg-slate-100 px-6 py-10 text-slate-900">
            <div className="mx-auto max-w-md rounded-3xl bg-white p-8 shadow-sm">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                    ZeroMerma
                </p>
                <h1 className="mt-2 text-3xl font-semibold">Sign in</h1>
                <p className="mt-3 text-sm text-slate-600">
                    Authenticate against the real ZeroMerma backend.
                </p>

                <form onSubmit={handleSubmit} className="mt-8 space-y-4">
                    <div>
                        <label
                            htmlFor="email"
                            className="mb-2 block text-sm font-medium text-slate-700"
                        >
                            Email
                        </label>
                        <input
                            id="email"
                            type="email"
                            autoComplete="username"
                            value={email}
                            onChange={(event) => setEmail(event.target.value)}
                            className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-base outline-none transition focus:border-slate-900"
                            placeholder="admin@example.com"
                            required
                        />
                    </div>

                    <div>
                        <label
                            htmlFor="password"
                            className="mb-2 block text-sm font-medium text-slate-700"
                        >
                            Password
                        </label>
                        <input
                            id="password"
                            type="password"
                            autoComplete="current-password"
                            value={password}
                            onChange={(event) =>
                                setPassword(event.target.value)
                            }
                            className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-base outline-none transition focus:border-slate-900"
                            placeholder="********"
                            required
                        />
                    </div>

                    {errorMessage ? (
                        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                            {errorMessage}
                        </div>
                    ) : null}

                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className="w-full rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {isSubmitting ? "Signing in..." : "Sign in"}
                    </button>
                </form>

                <div className="mt-6 rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
                    <p className="font-medium text-slate-800">
                        Development credentials
                    </p>
                    <p className="mt-2">Admin: admin@example.com / admin1234</p>
                    <p>Cashier: cashier@example.com / cashier1234</p>
                </div>
            </div>
        </main>
    );
}
