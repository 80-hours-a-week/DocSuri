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
  // Hide the dev route/build indicator (the bottom-left "Static route" badge). The granular
  // appIsrStatus/buildActivity flags used earlier were removed in Next 15.2+, so the badge
  // returned; `false` disables the indicator wholesale (dev-only overlay, no prod effect).
  devIndicators: false,
};

export default nextConfig;
