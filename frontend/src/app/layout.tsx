import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ClerkAppProvider } from "@/components/clerk-app-provider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "LegalTech AI",
  description: "Legal workspace — dashboard and AI assistance",
  icons: {
    icon: [{ url: "/favicon.ico", type: "image/x-icon" }],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkAppProvider>
      <html
        lang="en"
        className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
        suppressHydrationWarning
      >
        <body
          className="min-h-full flex flex-col font-sans"
          suppressHydrationWarning
        >
          {children}
        </body>
      </html>
    </ClerkAppProvider>
  );
}
