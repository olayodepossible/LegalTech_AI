"use client";

import { RedirectIfSignedIn } from "@/components/redirect-if-signed-in";
import { Show, SignInButton, SignUpButton } from "@clerk/react";
import Image from "next/image";
import Link from "next/link";

const DASHBOARD = "/dashboard";

export default function LoginPage() {
  return (
    <>
      <Show when="signed-in">
        <RedirectIfSignedIn to={DASHBOARD} />
      </Show>
      <Show when="signed-out">
        <div className="flex min-h-screen flex-col">
          <header className="sticky top-0 z-30 border-b border-zinc-200/90 bg-white/95 shadow-sm backdrop-blur-md dark:border-zinc-800 dark:bg-zinc-950/95">
            <div className="mx-auto flex h-16 w-full max-w-7xl items-center gap-4 px-4 sm:h-[4.5rem] sm:px-8">
              <Link
                href="/login"
                className="flex min-w-0 items-center gap-3 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40"
              >
                <Image
                  src="/legal_logo.png"
                  alt="Legal Companion"
                  width={48}
                  height={48}
                  className="h-10 w-auto shrink-0 object-contain sm:h-11"
                  priority
                />
                <span className="truncate text-lg font-semibold tracking-tight text-zinc-900 sm:text-xl dark:text-zinc-50">
                  Legal Companion
                </span>
              </Link>
              <div className="flex min-w-[1rem] flex-1" aria-hidden />
              <div className="flex shrink-0 items-center gap-2 sm:gap-3">
                <SignUpButton
                  mode="modal"
                  forceRedirectUrl={DASHBOARD}
                  fallbackRedirectUrl={DASHBOARD}
                >
                  <button
                    type="button"
                    className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm font-semibold text-zinc-800 shadow-sm transition hover:bg-zinc-50 dark:border-zinc-600 dark:bg-zinc-900 dark:text-zinc-100 dark:hover:bg-zinc-800 sm:px-4"
                  >
                    Create account
                  </button>
                </SignUpButton>
                <SignInButton
                  mode="modal"
                  forceRedirectUrl={DASHBOARD}
                  fallbackRedirectUrl={DASHBOARD}
                >
                  <button
                    type="button"
                    className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 sm:px-4"
                  >
                    Sign in
                  </button>
                </SignInButton>
              </div>
            </div>
          </header>

          <main className="flex flex-1 flex-col">
            <section className="relative w-full flex-1 min-h-[320px] sm:min-h-[440px] lg:min-h-[min(72vh,760px)]">
              <Image
                src="/law-firm.jpg"
                alt="Law firm professionals collaborating"
                fill
                priority
                className="object-cover"
                sizes="100vw"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-zinc-950/85 via-zinc-950/30 to-zinc-950/10" />
              <div className="absolute inset-x-0 bottom-0 p-6 sm:p-10 lg:p-14">
                <div className="mx-auto max-w-7xl">
                  <h1 className="max-w-2xl text-3xl font-semibold tracking-tight text-white sm:text-4xl lg:text-5xl">
                    Your intelligent legal workspace
                  </h1>
                  <p className="mt-4 max-w-xl text-base leading-relaxed text-zinc-200 sm:text-lg">
                    Research, documents, and AI assistance in one place. Sign
                    in to open your workspace dashboard.
                  </p>
                </div>
              </div>
            </section>
          </main>
        </div>
      </Show>
    </>
  );
}
