export default function HomePage() {
    return (
        <main className="min-h-screen bg-slate-100 px-6 py-10 text-slate-900">
            <div className="mx-auto max-w-4xl rounded-3xl bg-white p-8 shadow-sm">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                    ZeroMerma
                </p>
                <h1 className="mt-2 text-3xl font-semibold">
                    Frontend base ready
                </h1>
                <p className="mt-3 text-sm text-slate-600">
                    This is the initial frontend foundation. Next step: POS cash
                    session open screen.
                </p>

                <div className="mt-6">
                    <a
                        href="/pos/cash-session/open"
                        className="inline-flex rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
                    >
                        Go to POS cash session open
                    </a>
                </div>
            </div>
        </main>
    );
}
