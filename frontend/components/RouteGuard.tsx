'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from './session/SessionContext';
import { StateView } from './StateView';

// RouteGuard (LC-4, BR-U5-15, SEC-8) — client-side reflection of protected
// routes. Anonymous users are redirected to login with the destination
// preserved. Backend 401/403 remains authoritative.

export function RouteGuard({ redirectTo, children }: { redirectTo: string; children: React.ReactNode }) {
  const { status, signingOut } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === 'anonymous' && !signingOut) {
      router.replace(`/login?redirect=${encodeURIComponent(redirectTo)}`);
    }
  }, [status, signingOut, redirectTo, router]);

  if (status === 'authenticated') return <>{children}</>;
  if (signingOut) {
    return <StateView kind="loading" title="로그아웃 중…" message="잠시만 기다려 주세요." />;
  }
  return <StateView kind="loading" />;
}
