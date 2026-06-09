import withPWA from "next-pwa";

const isDev = process.env.NODE_ENV !== "production";

const pwaConfig = {
  dest: "public",
  disable: isDev,
  register: true,
  skipWaiting: true,
};

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    serverActions: { allowedOrigins: ["localhost:3000"] },
  },
  async rewrites() {
    // Proxy /api/backend/* to the FastAPI app during local dev. Production
    // sets NEXT_PUBLIC_BACKEND_BASE and the rewrite becomes a no-op route.
    const backend = process.env.BACKEND_URL ?? "http://localhost:8000";
    return [{ source: "/api/backend/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default withPWA(pwaConfig)(nextConfig);
