"use client";

import { ChatSidebarHistory } from "@/components/chat-sidebar-history";
import { UserButton, useUser } from "@clerk/react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense, useState } from "react";

const nav: {
  href: string;
  label: string;
  isActive: (p: string) => boolean;
}[] = [
  {
    href: "/dashboard/",
    label: "Home",
    isActive: (p) => p === "/dashboard" || p === "/dashboard/",
  },
  {
    href: "/chat",
    label: "New Chat",
    isActive: (p) => p === "/chat",
  },
  {
    href: "/chat/contract",
    label: "Contract analysis",
    isActive: (p) => p.startsWith("/chat/contract"),
  },
  { href: "/rag", label: "Upload documents", isActive: (p) => p.startsWith("/rag") },
];

function IconHome({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  );
}

function IconMessage({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
    </svg>
  );
}

function IconScale({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1z" />
      <path d="M2 16l1-8 1 8" />
      <path d="M7 10h.01" />
      <path d="M7 16h.01" />
      <path d="M10 4 8 2H4a2 2 0 0 0-2 2v2l8 8" />
    </svg>
  );
}

function IconLayers({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z" />
      <path d="m22 12-8.58 3.91a2 2 0 0 1-1.66 0L2 12" />
      <path d="m2 17 8.58 3.91a2 2 0 0 0 1.66 0L22 17" />
    </svg>
  );
}

function IconMenu({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <line x1="4" x2="20" y1="6" y2="6" />
      <line x1="4" x2="20" y1="12" y2="12" />
      <line x1="4" x2="20" y1="18" y2="18" />
    </svg>
  );
}

const iconFor = (href: string) => {
  switch (href) {
    case "/dashboard/":
    case "/dashboard":
      return IconHome;
    case "/chat":
      return IconMessage;
    case "/chat/contract":
      return IconScale;
    case "/rag":
      return IconLayers;
    default:
      return IconHome;
  }
};

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user } = useUser();
  const pathname = usePathname() || "";
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const displayName =
    user?.fullName ||
    user?.firstName ||
    user?.primaryEmailAddress?.emailAddress ||
    "Account";

  return (
    <div className="flex min-h-full flex-1 flex-col bg-zinc-100/80 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100">
      {mobileNavOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-40 cursor-default bg-zinc-950/50 backdrop-blur-sm lg:hidden"
          aria-label="Close menu"
          onClick={() => setMobileNavOpen(false)}
        />
      ) : null}

      <div className="flex min-h-0 flex-1">
        <aside
          className={[
            "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-zinc-200/90 bg-white shadow-sm transition-transform duration-200 dark:border-zinc-800/90 dark:bg-zinc-900",
            "lg:static lg:z-0 lg:translate-x-0 lg:shadow-none",
            mobileNavOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
          ].join(" ")}
        >
          <div className="flex h-14 shrink-0 items-center gap-3 border-b border-zinc-100 px-4 dark:border-zinc-800/80">
            <Link
              href="/dashboard/"
              className="flex min-w-0 items-center gap-2.5 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50"
              onClick={() => setMobileNavOpen(false)}
            >
              <Image
                src="/legal_logo.png"
                alt="Legal Companion"
                width={40}
                height={40}
                className="h-9 w-auto shrink-0 object-contain"
                priority
              />
              <span className="truncate text-base font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
                Legal Bot
              </span>
            </Link>
          </div>

          <nav
            className="flex min-h-0 flex-1 flex-col gap-0 p-3"
            aria-label="Main"
          >
            <div className="flex flex-col gap-0.5">
              {nav.map((item) => {
                const active = item.isActive(pathname);
                const Icon = iconFor(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileNavOpen(false)}
                    className={[
                      "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                      active
                        ? "bg-indigo-100 text-indigo-950 dark:bg-indigo-950/50 dark:text-indigo-100"
                        : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800/80",
                    ].join(" ")}
                  >
                    <Icon
                      className={[
                        "h-5 w-5 shrink-0",
                        active
                          ? "text-indigo-700 dark:text-indigo-200"
                          : "text-zinc-500 dark:text-zinc-500",
                      ].join(" ")}
                    />
                    {item.label}
                  </Link>
                );
              })}
            </div>
            <Suspense fallback={null}>
              <ChatSidebarHistory
                onNavigate={() => setMobileNavOpen(false)}
              />
            </Suspense>
          </nav>

          <div className="shrink-0 border-t border-zinc-100 p-3 text-xs text-zinc-500 dark:border-zinc-800 dark:text-zinc-500">
            Signed in as{" "}
            <span className="font-medium text-zinc-700 dark:text-zinc-300">
              {displayName}
            </span>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col lg:pl-0">
          <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center justify-between gap-3 border-b border-zinc-200/80 bg-white/95 px-4 backdrop-blur dark:border-zinc-800/80 dark:bg-zinc-950/95">
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800 lg:hidden"
                onClick={() => setMobileNavOpen(true)}
                aria-label="Open menu"
              >
                <IconMenu className="h-5 w-5" />
              </button>
              <p className="text-sm text-zinc-500 dark:text-zinc-400 lg:hidden">
                Menu
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="hidden max-w-[14rem] truncate text-xs text-zinc-500 sm:block dark:text-zinc-400">
                {displayName}
              </span>
              <UserButton />
            </div>
          </header>

          <main className="mx-auto w-full min-w-0 max-w-6xl flex-1 overflow-y-auto px-4 py-6 sm:px-6 sm:py-8">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
