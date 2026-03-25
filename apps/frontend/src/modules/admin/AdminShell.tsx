"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/modules/auth/AuthProvider";
import { RequireAdmin } from "./RequireAdmin";

function NavItem({ href, label }: { href: string; label: string }) {
    const pathname = usePathname();
    const isActive = pathname === href || pathname.startsWith(`${href}/`);

    return (
        <Link
            href={href}
            className={[
                "block rounded-2xl px-4 py-3 text-sm font-medium transition",
                isActive
                    ? "bg-slate-900 text-white"
                    : "text-slate-700 hover:bg-slate-100",
            ].join(" ")}
        >
            {label}
        </Link>
    );
}

export function AdminShell({ children }: { children: React.ReactNode }) {
    const { session, logout } = useAuth();

    return (
        <RequireAdmin>
            <div className="min-h-screen bg-slate-100 text-slate-900">
                <div className="mx-auto grid min-h-screen max-w-7xl grid-cols-1 gap-6 px-6 py-6 lg:grid-cols-[280px_1fr]">
                    <aside className="rounded-3xl bg-white p-6 shadow-sm">
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                            ZeroMerma
                        </p>
                        <h1 className="mt-2 text-2xl font-semibold">
                            Administration
                        </h1>

                        <div className="mt-4 rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
                            <p className="font-medium text-slate-800">
                                {session?.user.fullName}
                            </p>
                            <p>{session?.user.email}</p>
                            <p className="mt-1">
                                Role: <strong>{session?.user.roleCode}</strong>
                            </p>
                        </div>

                        <nav className="mt-6 space-y-2">
                            <NavItem href="/admin/roles" label="Roles" />
                            <NavItem
                                href="/admin/users"
                                label="User Accounts"
                            />
                            <NavItem href="/admin/products" label="Products" />
                        </nav>

                        <div className="mt-6 flex flex-col gap-3">
                            <Link
                                href="/pos"
                                className="rounded-2xl border border-slate-300 px-4 py-3 text-center text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                            >
                                Back to POS
                            </Link>

                            <button
                                type="button"
                                onClick={logout}
                                className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:opacity-90"
                            >
                                Sign out
                            </button>
                        </div>
                    </aside>

                    <main className="rounded-3xl bg-white p-6 shadow-sm">
                        {children}
                    </main>
                </div>
            </div>
        </RequireAdmin>
    );
}
