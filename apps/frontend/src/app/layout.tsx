import type { Metadata } from "next";
import "./globals.css";

import { Providers } from "./providers";

export const metadata: Metadata = {
    title: "ZeroMerma Frontend",
    description: "ZeroMerma POS frontend",
};

interface RootLayoutProps {
    children: React.ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
    return (
        <html lang="en">
            <body>
                <Providers>{children}</Providers>
            </body>
        </html>
    );
}
