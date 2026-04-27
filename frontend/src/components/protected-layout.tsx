"use client";

import { AppShell } from "@/components/app-shell";
import { useAuth } from "@clerk/react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo } from "react";

/**
 * Clerk may land on a protected route with `?__clerk_handshake=...` while it
 * exchanges cookies. If we redirect to /login before that finishes, we strip the
 * handshake and Clerk redirects back — an infinite loop.
 */
export function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { isLoaded, userId } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const clerkHandshakePending = useMemo(
    () => Boolean(searchParams.get("__clerk_handshake")),
    [searchParams],
  );

  useEffect(() => {
    if (clerkHandshakePending) return;
    if (isLoaded && !userId) {
      router.replace("/login");
    }
  }, [isLoaded, userId, router, clerkHandshakePending]);

  if (!isLoaded || clerkHandshakePending) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
        {clerkHandshakePending ? "Completing sign-in…" : "Loading…"}
      </div>
    );
  }

  if (!userId) {
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
