"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/modules/auth/AuthProvider";

export function RequireAdmin({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const { status, session } = useAuth();

    const isAuthenticated = status === "authenticated" && session !== null;
    const isAdmin = isAuthenticated && session.user.roleCode === "ADMIN";

    useEffect(() => {
        if (status === "anonymous") {
            router.replace("/login?next=/admin");
            return;
        }

        if (
            status === "authenticated" &&
            session &&
            session.user.roleCode !== "ADMIN"
        ) {
            router.replace("/pos");
        }
    }, [status, session, router]);

    if (!isAuthenticated) {
        return (
            <main className="min-h-screen bg-slate-100 px-6 py-10 text-slate-900">
                <div className="mx-auto max-w-5xl rounded-3xl bg-white p-8 shadow-sm">
                    <p className="text-sm text-slate-500">
                        Validating administrative access...
                    </p>
                </div>
            </main>
        );
    }

    if (!isAdmin) {
        return (
            <main className="min-h-screen bg-slate-100 px-6 py-10 text-slate-900">
                <div className="mx-auto max-w-5xl rounded-3xl bg-white p-8 shadow-sm">
                    <p className="text-sm text-rose-700">
                        You do not have access to the administration area.
                    </p>
                </div>
            </main>
        );
    }

    return <>{children}</>;
}
