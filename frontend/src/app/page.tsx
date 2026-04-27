"use client";

import { isClerkAuthUrlPending } from "@/lib/clerk-auth-flow";
import { useAuth } from "@clerk/react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";

function HomeRedirect() {
  const { isSignedIn, isLoaded } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const clerkPending = isClerkAuthUrlPending(searchParams);
  const waitingForClerk = !isLoaded || (clerkPending && !isSignedIn);

  useEffect(() => {
    if (waitingForClerk) return;
    const t = window.setTimeout(() => {
      router.replace(isSignedIn ? "/dashboard/" : "/login/");
    }, 0);
    return () => clearTimeout(t);
  }, [waitingForClerk, isSignedIn, router]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-zinc-50 text-zinc-600 dark:bg-zinc-950 dark:text-zinc-400">
      <div className="h-10 w-10 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
      <p className="text-sm">
        {waitingForClerk ? "Completing sign-in…" : "Redirecting…"}
      </p>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-zinc-50 text-zinc-600 dark:bg-zinc-950 dark:text-zinc-400">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
          <p className="text-sm">Loading…</p>
        </div>
      }
    >
      <HomeRedirect />
    </Suspense>
  );
}
