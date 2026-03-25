import Link from "next/link";

export default function HomePage() {
    return (
        <main className="min-h-screen bg-slate-100 px-6 py-10 text-slate-900">
            <div className="mx-auto max-w-4xl rounded-3xl bg-white p-8 shadow-sm">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                    ZeroMerma
                </p>
                <h1 className="mt-2 text-3xl font-semibold">Frontend ready</h1>
                <p className="mt-3 text-sm text-slate-600">
                    Login is now the entry point for protected POS flows.
                </p>

                <div className="mt-6 flex flex-wrap gap-3">
                    <Link
                        href="/login"
                        className="inline-flex rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
                    >
                        Go to login
                    </Link>

                    <Link
                        href="/pos"
                        className="inline-flex rounded-2xl border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                    >
                        Go to POS
                    </Link>
                </div>
            </div>
        </main>
    );
}
