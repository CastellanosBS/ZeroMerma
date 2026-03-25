"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";

import { CurrentCashSessionCard } from "@/components/pos/cash-session/CurrentCashSessionCard";
import { CashSessionOpenForm } from "@/components/pos/cash-session/CashSessionOpenForm";
import { useCurrentCashSession } from "@/hooks/pos/useCurrentCashSession";
import { useOpenCashSession } from "@/hooks/pos/useOpenCashSession";
import { getActivePosContext } from "@/lib/pos/session";
import { ApiClientError } from "@/services/http/errors";

export function CashSessionOpenScreen() {
    const router = useRouter();
    const { branchId, token } = getActivePosContext();

    const currentSessionQuery = useCurrentCashSession({
        branchId,
        token,
    });

    const openSessionMutation = useOpenCashSession({
        branchId,
        token,
    });

    const openErrorMessage = useMemo(() => {
        const error = openSessionMutation.error;

        if (!error) {
            return null;
        }

        if (error instanceof ApiClientError) {
            return error.message;
        }

        return "Unexpected error while opening cash session.";
    }, [openSessionMutation.error]);

    function handleOpenSession(openingAmount: string) {
        if (branchId === null || !token) {
            return;
        }

        openSessionMutation.mutate({
            branch_id: branchId,
            opening_amount: openingAmount,
        });
    }

    function handleContinue() {
        router.push("/pos");
    }

    function handleClose() {
        router.push("/pos/cash-session/close");
    }

    if (branchId === null || !token) {
        return (
            <div className="min-h-screen bg-slate-100 text-slate-900">
                <div className="border-b bg-white shadow-sm">
                    <div className="mx-auto max-w-4xl px-6 py-5">
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                            ZeroMerma POS
                        </p>
                        <h1 className="text-3xl font-semibold">
                            Cash Session Access
                        </h1>
                        <p className="mt-2 text-sm text-slate-500">
                            No authenticated POS context is available.
                        </p>
                    </div>
                </div>

                <div className="mx-auto max-w-4xl px-6 py-8">
                    <div className="rounded-3xl border border-amber-200 bg-white p-6 shadow-sm">
                        <p className="text-sm font-medium text-amber-700">
                            Session context is missing. Please sign in again.
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-100 text-slate-900">
            <div className="border-b bg-white shadow-sm">
                <div className="mx-auto max-w-4xl px-6 py-5">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                        ZeroMerma POS
                    </p>
                    <h1 className="text-3xl font-semibold">
                        Cash Session Access
                    </h1>
                    <p className="mt-2 text-sm text-slate-500">
                        Validate the current branch session before entering
                        checkout.
                    </p>
                </div>
            </div>

            <div className="mx-auto max-w-4xl px-6 py-8">
                {currentSessionQuery.isLoading ? (
                    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                        <p className="text-sm text-slate-500">
                            Loading current cash session...
                        </p>
                    </div>
                ) : null}

                {currentSessionQuery.isError ? (
                    <div className="rounded-3xl border border-rose-200 bg-white p-6 shadow-sm">
                        <p className="text-sm font-medium text-rose-700">
                            Failed to load current cash session.
                        </p>
                    </div>
                ) : null}

                {!currentSessionQuery.isLoading &&
                !currentSessionQuery.isError ? (
                    currentSessionQuery.data ? (
                        <CurrentCashSessionCard
                            session={currentSessionQuery.data}
                            onContinue={handleContinue}
                            onClose={handleClose}
                        />
                    ) : (
                        <CashSessionOpenForm
                            branchId={branchId}
                            isSubmitting={openSessionMutation.isPending}
                            errorMessage={openErrorMessage}
                            onSubmit={handleOpenSession}
                        />
                    )
                ) : null}
            </div>
        </div>
    );
}
