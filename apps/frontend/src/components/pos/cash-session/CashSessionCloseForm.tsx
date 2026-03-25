"use client";

import { useState } from "react";

interface CashSessionCloseFormProps {
    sessionId: number;
    openingAmount: string;
    isSubmitting: boolean;
    errorMessage: string | null;
    onSubmit: (payload: {
        closing_amount: string;
        counted_card_total?: string;
        counted_transfer_total?: string;
        counted_other_total?: string;
        note?: string;
    }) => void;
}

export function CashSessionCloseForm({
    sessionId,
    openingAmount,
    isSubmitting,
    errorMessage,
    onSubmit,
}: CashSessionCloseFormProps) {
    const [closingAmount, setClosingAmount] = useState("");
    const [countedCardTotal, setCountedCardTotal] = useState("");
    const [countedTransferTotal, setCountedTransferTotal] = useState("");
    const [countedOtherTotal, setCountedOtherTotal] = useState("");
    const [note, setNote] = useState("");

    function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
        event.preventDefault();

        onSubmit({
            closing_amount: closingAmount.trim(),
            counted_card_total: countedCardTotal.trim() || undefined,
            counted_transfer_total: countedTransferTotal.trim() || undefined,
            counted_other_total: countedOtherTotal.trim() || undefined,
            note: note.trim() || undefined,
        });
    }

    return (
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-6">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                    Cash session close
                </p>
                <h2 className="mt-2 text-2xl font-semibold text-slate-900">
                    Close session #{sessionId}
                </h2>
                <p className="mt-2 text-sm text-slate-500">
                    Record the counted cash and optional non-cash reconciliation
                    amounts before closing the current session.
                </p>
            </div>

            <div className="mb-6 grid grid-cols-1 gap-4 rounded-2xl bg-slate-50 p-4 text-sm md:grid-cols-2">
                <div>
                    <p className="text-slate-500">Opening amount</p>
                    <p className="font-medium text-slate-900">
                        ${openingAmount}
                    </p>
                </div>
                <div>
                    <p className="text-slate-500">Session status</p>
                    <p className="font-medium text-emerald-700">OPEN</p>
                </div>
            </div>

            {errorMessage ? (
                <div className="mb-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                    {errorMessage}
                </div>
            ) : null}

            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label
                        htmlFor="closing-amount"
                        className="mb-2 block text-sm font-medium text-slate-700"
                    >
                        Counted cash in drawer
                    </label>
                    <input
                        id="closing-amount"
                        type="text"
                        inputMode="decimal"
                        value={closingAmount}
                        onChange={(event) =>
                            setClosingAmount(event.target.value)
                        }
                        placeholder="1000.00"
                        required
                        disabled={isSubmitting}
                        className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    />
                </div>

                <div>
                    <label
                        htmlFor="counted-card-total"
                        className="mb-2 block text-sm font-medium text-slate-700"
                    >
                        Counted card total
                    </label>
                    <input
                        id="counted-card-total"
                        type="text"
                        inputMode="decimal"
                        value={countedCardTotal}
                        onChange={(event) =>
                            setCountedCardTotal(event.target.value)
                        }
                        placeholder="Optional"
                        disabled={isSubmitting}
                        className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    />
                </div>

                <div>
                    <label
                        htmlFor="counted-transfer-total"
                        className="mb-2 block text-sm font-medium text-slate-700"
                    >
                        Counted transfer total
                    </label>
                    <input
                        id="counted-transfer-total"
                        type="text"
                        inputMode="decimal"
                        value={countedTransferTotal}
                        onChange={(event) =>
                            setCountedTransferTotal(event.target.value)
                        }
                        placeholder="Optional"
                        disabled={isSubmitting}
                        className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    />
                </div>

                <div>
                    <label
                        htmlFor="counted-other-total"
                        className="mb-2 block text-sm font-medium text-slate-700"
                    >
                        Counted other non-cash total
                    </label>
                    <input
                        id="counted-other-total"
                        type="text"
                        inputMode="decimal"
                        value={countedOtherTotal}
                        onChange={(event) =>
                            setCountedOtherTotal(event.target.value)
                        }
                        placeholder="Optional"
                        disabled={isSubmitting}
                        className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    />
                </div>

                <div>
                    <label
                        htmlFor="close-note"
                        className="mb-2 block text-sm font-medium text-slate-700"
                    >
                        Note
                    </label>
                    <textarea
                        id="close-note"
                        value={note}
                        onChange={(event) => setNote(event.target.value)}
                        placeholder="Optional reconciliation note"
                        rows={4}
                        disabled={isSubmitting}
                        className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    />
                </div>

                <div className="pt-2">
                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:opacity-90 disabled:opacity-50"
                    >
                        {isSubmitting
                            ? "Closing session..."
                            : "Close cash session"}
                    </button>
                </div>
            </form>
        </div>
    );
}
