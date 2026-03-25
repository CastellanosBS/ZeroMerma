import type { Metadata } from "next";

import { GlobalLogoutButton } from "@/components/auth/GlobalLogoutButton";

import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
    title: "ZeroMerma",
    description: "ZeroMerma frontend",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body className="bg-slate-100 text-slate-900 antialiased">
                <Providers>
                    <GlobalLogoutButton />
                    {children}
                </Providers>
            </body>
        </html>
    );
}
