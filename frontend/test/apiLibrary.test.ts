import { describe, it, expect } from 'vitest';
import { ApiClient } from '@/lib/api/apiClient';
import { UserFacingError } from '@/lib/api/errors';
import type { Transport, TransportRequest, TransportResponse } from '@/lib/api/transport';
import { pageResponse } from '@/mocks/searchFixtures';

// ApiClient U4 (library/saved/history) methods — exercised against an injected
// transport so paths, methods, DTO passthrough, pagination and error
// normalization are asserted deterministically (no MockTransport).

const fast = { timeoutMs: 1000, retryBackoffMs: 1 };

function recorder(
  impl: (req: TransportRequest) => TransportResponse,
): { transport: Transport; calls: TransportRequest[] } {
  const calls: TransportRequest[] = [];
  return {
    calls,
    transport: {
      async send(req) {
        calls.push(req);
        return impl(req);
      },
    },
  };
}

describe('ApiClient library methods', () => {
  it('lists library items with a default cursor page (GET /library/items)', async () => {
    const r = recorder(() => ({ status: 200, body: { items: [], nextCursor: 'c2' } }));
    const page = await new ApiClient(r.transport, fast).listLibrary();
    expect(page).toEqual({ items: [], nextCursor: 'c2' });
    expect(r.calls[0]).toMatchObject({ method: 'GET', path: '/library/items?limit=20', idempotent: true });
  });

  it('passes a cursor through to the query string', async () => {
    const r = recorder(() => ({ status: 200, body: { items: [] } }));
    await new ApiClient(r.transport, fast).listLibrary({ cursor: 'abc', limit: 5 });
    expect(r.calls[0].path).toBe('/library/items?limit=5&cursor=abc');
  });

  it('adds to library (POST /library/items, 201) and returns the item', async () => {
    const item = { id: 'li1', arXivId: '1706.03762', meta: { title: 't', authors: [], arxivId: '1706.03762' }, addedAt: 'x' };
    const r = recorder(() => ({ status: 201, body: item }));
    const out = await new ApiClient(r.transport, fast).addToLibrary({
      arXivId: '1706.03762',
      meta: { title: 't', authors: [], arxivId: '1706.03762' },
    });
    expect(out).toEqual(item);
    expect(r.calls[0]).toMatchObject({ method: 'POST', path: '/library/items', idempotent: false });
  });

  it('removes a library item (DELETE /library/items/{id}, 204) and resolves', async () => {
    const r = recorder(() => ({ status: 204, body: null }));
    await expect(new ApiClient(r.transport, fast).removeFromLibrary('li 1')).resolves.toBeUndefined();
    expect(r.calls[0]).toMatchObject({ method: 'DELETE', path: '/library/items/li%201' });
  });

  it('saves a search (POST /library/saved-searches, 201)', async () => {
    const r = recorder(() => ({ status: 201, body: { id: 's1', query: 'q', createdAt: 'x' } }));
    const out = await new ApiClient(r.transport, fast).saveSearch({ query: 'q' });
    expect(out).toMatchObject({ id: 's1', query: 'q' });
    expect(r.calls[0]).toMatchObject({ method: 'POST', path: '/library/saved-searches' });
  });

  it('reruns a saved search through the gateway and classifies the result', async () => {
    const r = recorder(() => ({ status: 200, body: pageResponse }));
    const out = await new ApiClient(r.transport, fast).rerunSavedSearch('s1');
    expect(out.kind).toBe('page');
    expect(r.calls[0]).toMatchObject({ method: 'POST', path: '/library/saved-searches/s1/rerun' });
  });

  it('lists history (GET /library/history) and clears it (DELETE /library/history)', async () => {
    const r = recorder((req) =>
      req.method === 'GET'
        ? { status: 200, body: { items: [{ id: 'h1', query: 'q', executedAt: 'x', resultCount: 3 }] } }
        : { status: 204, body: null },
    );
    const client = new ApiClient(r.transport, fast);
    const page = await client.listHistory();
    expect(page.items).toHaveLength(1);
    await expect(client.clearHistory()).resolves.toBeUndefined();
    expect(r.calls[1]).toMatchObject({ method: 'DELETE', path: '/library/history' });
  });

  it('normalizes a 401 on a list to a user-facing auth error (fail-closed)', async () => {
    const r = recorder(() => ({ status: 401, body: null }));
    await expect(new ApiClient(r.transport, fast).listLibrary()).rejects.toMatchObject({ kind: 'auth' });
  });

  it('does NOT retry a state-changing delete on 5xx', async () => {
    const r = recorder(() => ({ status: 500, body: null }));
    await expect(new ApiClient(r.transport, fast).removeFromLibrary('x')).rejects.toBeInstanceOf(UserFacingError);
    expect(r.calls).toHaveLength(1);
  });
});
