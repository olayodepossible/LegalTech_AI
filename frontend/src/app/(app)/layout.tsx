import { ProtectedLayout } from "@/components/protected-layout";
import { Suspense } from "react";

function AppLoadingFallback() {
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
      Loading…
    </div>
  );
}

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Suspense fallback={<AppLoadingFallback />}>
      <ProtectedLayout>{children}</ProtectedLayout>
    </Suspense>
  );
}
