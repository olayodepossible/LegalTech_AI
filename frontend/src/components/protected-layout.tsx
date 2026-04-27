"use client";

import { AppShell } from "@/components/app-shell";
import { isClerkAuthUrlPending } from "@/lib/clerk-auth-flow";
import { useAuth } from "@clerk/react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo } from "react";

/**
 * While Clerk finishes handshake / session sync, avoid `router.replace` so we
 * do not strip `__clerk_*` params or bounce before `isSignedIn` matches `userId`.
 */
export function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { isLoaded, isSignedIn } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const clerkFlowPending = useMemo(
    () => isClerkAuthUrlPending(searchParams),
    [searchParams],
  );

  useEffect(() => {
    if (clerkFlowPending || !isLoaded || isSignedIn) return;
    const t = window.setTimeout(() => {
      router.replace("/login");
    }, 400);
    return () => clearTimeout(t);
  }, [isLoaded, isSignedIn, router, clerkFlowPending]);

  if (!isLoaded || clerkFlowPending) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
        {clerkFlowPending ? "Completing sign-in…" : "Loading…"}
      </div>
    );
  }

  if (!isSignedIn) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
        Redirecting to sign in…
      </div>
    );
  }

  return (
    <div className="flex min-h-full w-full flex-1 flex-col">
      <AppShell>{children}</AppShell>
    </div>
  );
}
