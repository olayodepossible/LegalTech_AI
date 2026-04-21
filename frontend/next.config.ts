import type { NextConfig } from "next";

/**
 * Next.js dev blocks HMR WebSockets and internal assets (e.g. __nextjs_font)
 * unless the browser's origin host matches this list. Access via LAN IP needs
 * an entry here (wildcards supported: see Next.js allowedDevOrigins docs).
 *
 * Override with comma-separated host patterns: ALLOWED_DEV_ORIGINS=myhost.local,10.0.0.*
 */
const fromEnv =
  process.env.ALLOWED_DEV_ORIGINS?.split(",")
    .map((s) => s.trim())
    .filter(Boolean) ?? [];

const nextConfig: NextConfig = {
  allowedDevOrigins: [
    // Common private LAN ranges (dev only). For 172.16–172.31.x.x, set ALLOWED_DEV_ORIGINS.
    "192.168.*.*",
    "10.*.*.*",
    ...fromEnv,
  ],
};

export default nextConfig;
