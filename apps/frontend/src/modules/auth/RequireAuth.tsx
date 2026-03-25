"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/modules/auth/AuthProvider";

export function RequireAuth({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const { status } = useAuth();

    useEffect(() => {
        if (status === "anonymous") {
            const next =
                pathname && pathname !== "/login"
                    ? `?next=${encodeURIComponent(pathname)}`
                    : "";

            router.replace(`/login${next}`);
        }
    }, [status, pathname, router]);

    if (status !== "authenticated") {
        return (
            <main className="min-h-screen bg-slate-100 px-6 py-10 text-slate-900">
                <div className="mx-auto max-w-3xl rounded-3xl bg-white p-8 shadow-sm">
                    <p className="text-sm text-slate-500">
                        Validating session...
                    </p>
                </div>
            </main>
        );
    }

    return <>{children}</>;
}
