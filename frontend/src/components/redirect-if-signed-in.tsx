"use client";

import { useAuth } from "@clerk/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export function RedirectIfSignedIn({ to = "/dashboard/" }: { to?: string }) {
  const { isSignedIn, isLoaded } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    const t = window.setTimeout(() => router.replace(to), 0);
    return () => clearTimeout(t);
  }, [isLoaded, isSignedIn, router, to]);

  return null;
}
