import type { CashSession } from "@/types/pos/cash-session";

interface CurrentCashSessionCardProps {
    session: CashSession;
    onContinue: () => void;
    onClose?: () => void;
}

export function CurrentCashSessionCard({
    session,
    onContinue,
    onClose,
}: CurrentCashSessionCardProps) {
    return (
        <div className="rounded-3xl border border-emerald-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
                <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                        Current cash session
                    </p>
                    <h2 className="text-2xl font-semibold text-slate-900">
                        Session #{session.id}
                    </h2>
                </div>

                <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
                    {session.status}
                </span>
            </div>

            <div className="grid grid-cols-2 gap-4 rounded-2xl bg-slate-50 p-4 text-sm">
                <div>
                    <p className="text-slate-500">Branch ID</p>
                    <p className="font-medium text-slate-900">
                        {session.branch_id}
                    </p>
                </div>
                <div>
                    <p className="text-slate-500">Opened by</p>
                    <p className="font-medium text-slate-900">
                        {session.opened_by_id}
                    </p>
                </div>
                <div>
                    <p className="text-slate-500">Opened at</p>
                    <p className="font-medium text-slate-900">
                        {session.opened_at}
                    </p>
                </div>
                <div>
                    <p className="text-slate-500">Opening amount</p>
                    <p className="font-medium text-slate-900">
                        ${session.opening_amount}
                    </p>
                </div>
            </div>

            <div className="mt-5 flex flex-wrap justify-end gap-3">
                {onClose ? (
                    <button
                        type="button"
                        onClick={onClose}
                        className="rounded-2xl border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
                    >
                        Close session
                    </button>
                ) : null}

                <button
                    type="button"
                    onClick={onContinue}
                    className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:opacity-90"
                >
                    Go to POS
                </button>
            </div>
        </div>
    );
}
