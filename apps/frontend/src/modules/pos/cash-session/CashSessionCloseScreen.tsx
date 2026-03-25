"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import { CashSessionCloseForm } from "@/components/pos/cash-session/CashSessionCloseForm";
import { useCloseCashSession } from "@/hooks/pos/useCloseCashSession";
import { useCurrentCashSession } from "@/hooks/pos/useCurrentCashSession";
import { getActivePosContext } from "@/lib/pos/session";
import { ApiClientError } from "@/services/http/errors";
import type { CashSession } from "@/types/pos/cash-session";

function MetricCard(props: { label: string; value: string }) {
    return (
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">
                {props.label}
            </p>
            <p className="mt-2 text-lg font-semibold text-slate-900">
                {props.value}
            </p>
        </div>
    );
}

function ClosedSessionSummary({ session }: { session: CashSession }) {
    const snapshot = session.reconciliation_snapshot;

    if (!snapshot) {
        return (
            <div className="rounded-3xl border border-emerald-200 bg-white p-6 shadow-sm">
                <p className="text-sm text-emerald-700">
                    Session closed successfully.
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-6 rounded-3xl border border-emerald-200 bg-white p-6 shadow-sm">
            <div>
                <p className="text-xs uppercase tracking-[0.2em] text-emerald-600">
                    Session closed
                </p>
                <h2 className="mt-2 text-2xl font-semibold text-slate-900">
                    Session #{session.id}
                </h2>
                <p className="mt-2 text-sm text-slate-500">
                    The reconciliation snapshot was persisted successfully.
                </p>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <MetricCard
                    label="Expected cash"
                    value={`$${snapshot.expected_cash}`}
                />
                <MetricCard
                    label="Counted cash"
                    value={`$${snapshot.counted_cash}`}
                />
                <MetricCard
                    label="Cash difference"
                    value={`$${snapshot.cash_difference}`}
                />
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <MetricCard
                    label="Expected non-cash total"
                    value={`$${snapshot.total_expected_non_cash}`}
                />
                <MetricCard
                    label="Counted non-cash total"
                    value={`$${snapshot.total_counted_non_cash}`}
                />
                <MetricCard
                    label="Global difference"
                    value={`$${snapshot.total_difference}`}
                />
            </div>

            <div className="rounded-2xl bg-slate-50 p-4 text-sm">
                <p className="font-medium text-slate-800">
                    Assumed non-cash methods
                </p>
                <p className="mt-2 text-slate-600">
                    {snapshot.assumed_counted_non_cash_methods.length
                        ? snapshot.assumed_counted_non_cash_methods.join(", ")
                        : "None"}
                </p>
            </div>

            <div className="rounded-2xl bg-slate-50 p-4 text-sm">
                <p className="font-medium text-slate-800">Note</p>
                <p className="mt-2 text-slate-600">
                    {snapshot.note ?? "No note provided."}
                </p>
            </div>

            <div className="flex flex-wrap gap-3">
                <Link
                    href="/pos/cash-session/open"
                    className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:opacity-90"
                >
                    Back to session access
                </Link>
            </div>
        </div>
    );
}

export function CashSessionCloseScreen() {
    const { branchId, token } = getActivePosContext();
    const [closedSession, setClosedSession] = useState<CashSession | null>(
        null,
    );

    const currentSessionQuery = useCurrentCashSession({
        branchId,
        token,
    });

    const closeMutation = useCloseCashSession({
        branchId,
        token,
    });

    const errorMessage = useMemo(() => {
        const error = closeMutation.error ?? currentSessionQuery.error;

        if (!error) {
            return null;
        }

        if (error instanceof ApiClientError) {
            return error.message;
        }

        return "Unexpected error while closing cash session.";
    }, [closeMutation.error, currentSessionQuery.error]);

    function handleSubmit(payload: {
        closing_amount: string;
        counted_card_total?: string;
        counted_transfer_total?: string;
        counted_other_total?: string;
        note?: string;
    }) {
        const current = currentSessionQuery.data;

        if (branchId === null || !token || !current) {
            return;
        }

        closeMutation.mutate(
            {
                sessionId: current.id,
                input: payload,
            },
            {
                onSuccess: (data) => {
                    setClosedSession(data);
                },
            },
        );
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
                            Close cash session
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
                        Close cash session
                    </h1>
                    <p className="mt-2 text-sm text-slate-500">
                        Reconcile the current open session before ending the
                        shift.
                    </p>
                </div>
            </div>

            <div className="mx-auto max-w-4xl px-6 py-8">
                {closedSession ? (
                    <ClosedSessionSummary session={closedSession} />
                ) : null}

                {!closedSession && currentSessionQuery.isLoading ? (
                    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                        <p className="text-sm text-slate-500">
                            Loading current cash session...
                        </p>
                    </div>
                ) : null}

                {!closedSession &&
                !currentSessionQuery.isLoading &&
                !currentSessionQuery.data ? (
                    <div className="rounded-3xl border border-amber-200 bg-white p-6 shadow-sm">
                        <p className="text-sm font-medium text-amber-700">
                            There is no open cash session for this branch.
                        </p>
                        <div className="mt-4">
                            <Link
                                href="/pos/cash-session/open"
                                className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:opacity-90"
                            >
                                Go to session access
                            </Link>
                        </div>
                    </div>
                ) : null}

                {!closedSession &&
                !currentSessionQuery.isLoading &&
                currentSessionQuery.data ? (
                    <CashSessionCloseForm
                        sessionId={currentSessionQuery.data.id}
                        openingAmount={currentSessionQuery.data.opening_amount}
                        isSubmitting={closeMutation.isPending}
                        errorMessage={errorMessage}
                        onSubmit={handleSubmit}
                    />
                ) : null}
            </div>
        </div>
    );
}
