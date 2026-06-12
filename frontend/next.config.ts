import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Amplify WEB_COMPUTE 함정 대응 (env-setup-report §3): 콘솔 환경 변수는 빌드
  // 컨테이너에만 존재하고 SSR 런타임에 자동 전파되지 않는다 → 빌드 시점에 값이
  // 있으면 서버 번들에 인라인한다 (값 변경 시 재빌드 필요 — 데모 운영 전제).
  // 빌드 시 변수가 없으면 인라인하지 않는다 — 로컬의 "빌드 후 셸 env로 주입"
  // 워크플로(BACKEND_URL=... npm run start)는 런타임 조회 그대로 동작.
  ...(process.env.BACKEND_URL
    ? { env: { BACKEND_URL: process.env.BACKEND_URL } }
    : {}),
};

export default nextConfig;
