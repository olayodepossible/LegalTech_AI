"use client";

import { RedirectIfSignedIn } from "@/components/redirect-if-signed-in";
import { Show, SignInButton, SignUpButton } from "@clerk/nextjs";
import Image from "next/image";
import Link from "next/link";

const DASHBOARD = "/dashboard";

const btnClass =
  "inline-flex w-full items-center justify-center rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500";

const outlineBtnClass =
  "inline-flex w-full items-center justify-center rounded-lg border border-zinc-200 bg-white px-4 py-2.5 text-sm font-semibold text-zinc-800 shadow-sm transition hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:hover:bg-zinc-900";

export default function SignupPage() {
  return (
    <>
      <Show when="signed-in">
        <RedirectIfSignedIn to={DASHBOARD} />
      </Show>
      <Show when="signed-out">
        <div className="flex min-h-screen flex-col">
          <header className="border-b border-zinc-200/90 bg-white/95 backdrop-blur-md dark:border-zinc-800 dark:bg-zinc-950/95">
            <div className="mx-auto flex h-14 w-full max-w-6xl items-center px-4 sm:px-6">
              <Link
                href="/login"
                className="flex items-center gap-3 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40"
              >
                <Image
                  src="/legal_logo.png"
                  alt="Legal Companion"
                  width={40}
                  height={40}
                  className="h-9 w-auto object-contain"
                />
                <span className="text-lg font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
                  Legal Companion
                </span>
              </Link>
            </div>
          </header>
          <div className="flex flex-1 flex-col items-center justify-center px-4 py-12">
            <div className="w-full max-w-md">
              <div className="rounded-2xl border border-zinc-200/80 bg-white p-8 shadow-xl shadow-zinc-200/50 dark:border-zinc-800 dark:bg-zinc-900 dark:shadow-none">
                <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
                  Create account
                </h1>
                <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
                  Start your Legal Companion workspace
                </p>
                <div className="mt-8 flex flex-col gap-3">
                  <SignUpButton
                    mode="modal"
                    forceRedirectUrl={DASHBOARD}
                    fallbackRedirectUrl={DASHBOARD}
                  >
                    <button type="button" className={btnClass}>
                      Sign up
                    </button>
                  </SignUpButton>
                  <SignInButton
                    mode="modal"
                    forceRedirectUrl={DASHBOARD}
                    fallbackRedirectUrl={DASHBOARD}
                  >
                    <button type="button" className={outlineBtnClass}>
                      Already have an account? Sign in
                    </button>
                  </SignInButton>
                </div>
                <p className="mt-6 text-center text-sm text-zinc-500 dark:text-zinc-400">
                  <Link
                    href="/login"
                    className="font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
                  >
                    Back to home
                  </Link>
                </p>
              </div>
            </div>
          </div>
        </div>
      </Show>
    </>
  );
}
