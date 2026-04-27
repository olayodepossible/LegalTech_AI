"use client";

import { useAuth } from "@clerk/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export function RedirectIfSignedIn({ to = "/dashboard" }: { to?: string }) {
  const { isSignedIn, isLoaded } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoaded && isSignedIn) router.replace(to);
  }, [isLoaded, isSignedIn, router, to]);

  return null;
}
