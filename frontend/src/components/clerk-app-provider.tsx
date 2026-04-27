"use client";

import { ClerkProvider } from "@clerk/react";

export function ClerkAppProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const key = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  if (!key) {
    throw new Error("Missing NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY");
  }
  return <ClerkProvider publishableKey={key}>{children}</ClerkProvider>;
}
