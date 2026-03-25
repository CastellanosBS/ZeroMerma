"use client";

import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/modules/auth/AuthProvider";

export function GlobalLogoutButton() {
    const pathname = usePathname();
    const router = useRouter();
    const { status, logout } = useAuth();

    function handleLogout() {
        logout();
        router.replace("/login");
    }

    if (status !== "authenticated") {
        return null;
    }

    if (pathname === "/login") {
        return null;
    }

    return (
        <div className="fixed right-4 top-4 z-50">
            <button
                type="button"
                onClick={handleLogout}
                className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white shadow-lg transition hover:opacity-90"
            >
                Logout
            </button>
        </div>
    );
}
