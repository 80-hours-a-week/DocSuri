import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Security headers / CSP (LC-8, P-S2, SEC-4).
 *
 * frame-ancestors 'self' satisfies the phone-mockup carve-out (NFR-U2): the
 * desktop mockup frame is same-origin, so the app is never embedded by a third
 * party. Concrete values / nonce strategy are refined at code/Infra stage.
 */
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "frame-ancestors 'self'",
  "form-action 'self'",
].join('; ');

export function middleware(_request: NextRequest) {
  const response = NextResponse.next();
  response.headers.set('Content-Security-Policy', CSP);
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set('X-Frame-Options', 'SAMEORIGIN');
  return response;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
