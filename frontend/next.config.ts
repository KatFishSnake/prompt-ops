import type { NextConfig } from "next";
import packageJson from "./package.json";

const backendUrl = process.env.BACKEND_URL || "http://backend:8000";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_APP_VERSION: packageJson.version,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
