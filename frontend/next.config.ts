import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "export",
  images: {
    unoptimized: true,
  },
  // S3 website hosting serves `/dashboard/` from `dashboard/index.html`.
  // Without this, `/dashboard` falls through to `/index.html` and loops.
  trailingSlash: true,
};

export default nextConfig;
