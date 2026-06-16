// Mock account state — derived from shared/dtos/accounts.schema.json (BR-U5-19).
// In-memory session for mock-first development. `password` is never stored or
// echoed (SEC-12/3) — login only flips an authenticated flag.
import type { SessionInfo, SignupResult } from '@/types/generated';

let session: SessionInfo | null = null;

export function mockSignup(): SignupResult {
  return { accountId: 'acct_mock_0001' };
}

export function mockLogin(email: string): SessionInfo {
  session = {
    userId: `user_${hash(email)}`,
    expiresAt: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
  };
  return session;
}

export function mockLogout(): void {
  session = null;
}

export function mockCurrentSession(): SessionInfo | null {
  return session;
}

function hash(s: string): string {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h).toString(36);
}
