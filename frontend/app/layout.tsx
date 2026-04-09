import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "@/components/providers/QueryProvider";

export const metadata: Metadata = {
  title: "MoneyClaw — Agent Network",
  description: "Multi-agent crypto trading dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased bg-[#0a0e1a] text-slate-200">
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
