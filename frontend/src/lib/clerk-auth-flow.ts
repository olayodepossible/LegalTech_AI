/**
 * Clerk may append `__clerk_*` query params (handshake, OAuth return, etc.) while
 * establishing the browser session. Calling `router.replace` during that window
 * drops those params and commonly causes redirect loops with static SPAs
 * (`output: 'export'` + CloudFront).
 */
export function isClerkAuthUrlPending(
  searchParams: Pick<URLSearchParams, "keys">,
): boolean {
  for (const key of searchParams.keys()) {
    if (key.startsWith("__clerk")) return true;
  }
  return false;
}

/** Same check using the live URL (e.g. before `useSearchParams` updates). */
export function isClerkAuthUrlPendingOnWindow(): boolean {
  if (typeof window === "undefined") return false;
  if (isClerkAuthUrlPending(new URLSearchParams(window.location.search))) {
    return true;
  }
  return window.location.hash.includes("__clerk");
}
