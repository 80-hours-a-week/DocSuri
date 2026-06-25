import { describe, expect, it } from 'vitest';
import { ApiClient } from '@/lib/api/apiClient';
import type { Transport, TransportRequest, TransportResponse } from '@/lib/api/transport';

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

describe('ApiClient personalization methods', () => {
  it('records behavior events through the U9 endpoint', async () => {
    const r = recorder(() => ({
      status: 200,
      body: { recorded: true, duplicate: false, reason: 'recorded' },
    }));
    const out = await new ApiClient(r.transport, fast).recordBehaviorEvent({
      eventType: 'paper_opened',
      subject: { kind: 'paper', paperId: '2401.1' },
      source: 'frontend_anchor',
      metadata: { entrySurface: 'detail' },
      dedupeKey: 'd1',
    });

    expect(out.recorded).toBe(true);
    expect(r.calls[0]).toMatchObject({
      method: 'POST',
      path: '/api/personalization/events',
      idempotent: false,
    });
  });
});
