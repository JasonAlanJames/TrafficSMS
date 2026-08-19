import { existsSync } from "node:fs";

import type { NextConfig } from "next";

const internalApiOrigin = (
  process.env.INTERNAL_API_URL ??
  (existsSync("/.dockerenv")
    ? "http://api:8000"
    : "http://localhost:8000")
).replace(/\/+$/, "");

const nextConfig: NextConfig = {
  output: "standalone",

  poweredByHeader: false,

  reactStrictMode: true,

  compress: true,

  productionBrowserSourceMaps: false,

  async rewrites() {
    if (process.env.NODE_ENV !== "development") {
      return [];
    }

    return [
      {
        source: "/api/:path*",
        destination: `${internalApiOrigin}/:path*`,
      },
    ];
  },
};

export default nextConfig;