// MockTransport (LC-2, BR-U5-19) — serves shared/dtos-derived fixtures so U5
// develops without the U6 gateway / real U2. Search branch is keyword-driven so
// every terminal state is demoable:
//   query contains 없음/empty     -> empty page
//                  기권/abstain    -> abstain
//                  저하/degraded   -> degraded
//                  오류/error      -> 500 (server error)
//                  네트워크/fail   -> thrown (network failure)
//   otherwise                      -> result page
import type { Transport, TransportRequest, TransportResponse } from './transport';
import {
  pageResponse,
  emptyResponse,
  abstainResponse,
  degradedResponse,
} from '@/mocks/searchFixtures';
import {
  mockSignup,
  mockLogin,
  mockLogout,
  mockCurrentSession,
} from '@/mocks/accountFixtures';

function matches(q: string, ...needles: string[]): boolean {
  const lower = q.toLowerCase();
  return needles.some((n) => lower.includes(n));
}

export class MockTransport implements Transport {
  async send(req: TransportRequest): Promise<TransportResponse> {
    // Small latency so loading states are observable.
    await new Promise((r) => setTimeout(r, 120));

    if (req.path === '/search' && req.method === 'POST') {
      const query = String((req.body as { query?: unknown })?.query ?? '');
      if (matches(query, '네트워크', 'fail')) throw new Error('mock network failure');
      if (matches(query, '오류', 'error')) return { status: 500, body: null };
      if (matches(query, '없음', 'empty')) return { status: 200, body: emptyResponse };
      if (matches(query, '기권', 'abstain')) return { status: 200, body: abstainResponse };
      if (matches(query, '저하', 'degraded')) return { status: 200, body: degradedResponse };
      return { status: 200, body: pageResponse };
    }

    if (req.path === '/accounts/signup' && req.method === 'POST') {
      return { status: 201, body: mockSignup() };
    }
    if (req.path === '/accounts/login' && req.method === 'POST') {
      const email = String((req.body as { email?: unknown })?.email ?? 'mock@docsuri.dev');
      return { status: 200, body: mockLogin(email) };
    }
    if (req.path === '/accounts/logout' && req.method === 'POST') {
      mockLogout();
      return { status: 204, body: null };
    }
    if (req.path === '/accounts/session' && req.method === 'GET') {
      const session = mockCurrentSession();
      return session ? { status: 200, body: session } : { status: 401, body: null };
    }

    return { status: 404, body: null };
  }
}
