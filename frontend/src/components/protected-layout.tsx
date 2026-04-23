"use client";

import { AppShell } from "@/components/app-shell";
import { useAuth } from "@clerk/nextjs";

export function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { isLoaded, userId } = useAuth();

  if (!isLoaded) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
        Loading…
      </div>
    );
  }

  if (!userId) {
    return null;
  }

  return (
    <div className="flex min-h-full w-full flex-1 flex-col">
      <AppShell>{children}</AppShell>
    </div>
  );
}
