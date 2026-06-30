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
  // Hide the Next.js dev-mode indicator (route status / build spinner). Dev-only UI; it
  // never appears in a production build regardless.
  devIndicators: {
    appIsrStatus: false,
    buildActivity: false,
  },
};

export default nextConfig;
