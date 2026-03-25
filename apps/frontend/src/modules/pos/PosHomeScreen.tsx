"use client";

import Link from "next/link";

import { useAuth } from "@/modules/auth/AuthProvider";

export function PosHomeScreen() {
    const { session, logout } = useAuth();

    if (!session) {
        return null;
    }

    return (
        <main className="min-h-screen bg-slate-100 px-6 py-10 text-slate-900">
            <div className="mx-auto max-w-4xl rounded-3xl bg-white p-8 shadow-sm">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                    ZeroMerma POS
                </p>

                <h1 className="mt-2 text-3xl font-semibold">
                    Welcome, {session.user.fullName}
                </h1>

                <p className="mt-3 text-sm text-slate-600">
                    Authenticated as {session.user.roleCode} for branch{" "}
                    {session.user.branchId}.
                </p>

                <div className="mt-6 flex flex-wrap gap-3">
                    <Link
                        href="/pos/cash-session/open"
                        className="inline-flex rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
                    >
                        Cash session access
                    </Link>

                    {session.user.roleCode === "ADMIN" ? (
                        <Link
                            href="/admin"
                            className="inline-flex rounded-2xl border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                        >
                            Administration
                        </Link>
                    ) : null}

                    <button
                        type="button"
                        onClick={logout}
                        className="inline-flex rounded-2xl border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                    >
                        Sign out
                    </button>
                </div>
            </div>
        </main>
    );
}
