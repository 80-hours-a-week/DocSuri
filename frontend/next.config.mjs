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
  // Hide the dev route/build indicator (the bottom-left "Static route" badge). This pins the object
  // form the installed Next (15.1.x) validates; the wholesale `false` shorthand only lands in 15.2+
  // (passing it here trips an "Expected object, received boolean" config warning). Dev-only overlay,
  // no prod effect. Revisit if Next is bumped to 15.2+ (these keys were folded into `false` there).
  devIndicators: {
    appIsrStatus: false,
    buildActivity: false,
  },
};

export default nextConfig;
