/**
 * Next.js config — U5 Frontend (SSR phone-first, deploy unit ④).
 * Security headers / CSP are applied in middleware.ts (LC-8, SEC-4).
 * @type {import('next').NextConfig}
 */
const nextConfig = {
  reactStrictMode: true,
  // Standalone output keeps the SSR server stateless and deployable as an
  // independent unit (P-SC1). Concrete hosting topology is Infra-stage.
  output: 'standalone',
};

export default nextConfig;
