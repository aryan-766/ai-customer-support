import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Ambrane AI Customer Support",
  description: "AI-powered voice customer support dashboard for Ambrane",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-slate-950 text-slate-50">
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto overflow-x-hidden relative">
            {/* Ambient glow effects behind main content */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-[500px] bg-blue-500/10 blur-[120px] rounded-full pointer-events-none -z-10" />
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
