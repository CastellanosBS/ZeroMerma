import { useMemo, useState } from "react";

interface CashSessionOpenFormProps {
    branchId: number;
    isSubmitting: boolean;
    errorMessage: string | null;
    onSubmit: (openingAmount: string) => void;
}

export function CashSessionOpenForm({
    branchId,
    isSubmitting,
    errorMessage,
    onSubmit,
}: CashSessionOpenFormProps) {
    const [openingAmount, setOpeningAmount] = useState("1000.00");

    const isValid = useMemo(() => {
        const value = Number(openingAmount);
        return !Number.isNaN(value) && value >= 0;
    }, [openingAmount]);

    function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
        event.preventDefault();

        if (!isValid || isSubmitting) {
            return;
        }

        onSubmit(openingAmount);
    }

    return (
        <form
            onSubmit={handleSubmit}
            className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
        >
            <div className="mb-6">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                    Open cash session
                </p>
                <h2 className="text-2xl font-semibold text-slate-900">
                    Start branch shift
                </h2>
                <p className="mt-2 text-sm text-slate-500">
                    Open a new cash session for branch{" "}
                    <strong>{branchId}</strong>.
                </p>
            </div>

            <div className="space-y-4">
                <div>
                    <label
                        htmlFor="openingAmount"
                        className="mb-2 block text-sm font-medium text-slate-700"
                    >
                        Opening amount
                    </label>
                    <input
                        id="openingAmount"
                        type="text"
                        inputMode="decimal"
                        value={openingAmount}
                        onChange={(event) =>
                            setOpeningAmount(event.target.value)
                        }
                        className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-base outline-none transition focus:border-slate-900"
                        placeholder="0.00"
                    />
                </div>

                {errorMessage ? (
                    <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                        {errorMessage}
                    </div>
                ) : null}
            </div>

            <div className="mt-6 flex justify-end">
                <button
                    type="submit"
                    disabled={!isValid || isSubmitting}
                    className="rounded-2xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                >
                    {isSubmitting ? "Opening..." : "Open session"}
                </button>
            </div>
        </form>
    );
}
