'use client';

// useSummarize (P1·P5, BR-SF-4/14) — drives one summarize/translate request to a
// terminal classified outcome. real-first: calls ApiClient -> real BFF transport
// (no production mock). In-flight dedup + stale-response guard; errors normalize
// to an `error` outcome so the surface never hangs (NFR-FR1, no infinite loading).
import { useCallback, useRef, useState } from 'react';
import { getApiClient, type SummarizeOutcome } from '@/lib/api';
import type { SummarizeRequest } from '@/types/generated';

export type SummarizeState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'done'; outcome: SummarizeOutcome };

export function useSummarize() {
  const [state, setState] = useState<SummarizeState>({ status: 'idle' });
  // Identifies the latest request; completions for any other key are stale (P5).
  const activeKey = useRef<string | null>(null);

  const run = useCallback(async (req: SummarizeRequest) => {
    const key = JSON.stringify(req);
    if (activeKey.current === key && state.status === 'loading') return; // dedup (BR-SF-4)
    activeKey.current = key;
    setState({ status: 'loading' });
    try {
      const outcome = await getApiClient().summarize(req);
      if (activeKey.current !== key) return; // a newer request superseded this one
      setState({ status: 'done', outcome });
    } catch {
      if (activeKey.current !== key) return;
      setState({ status: 'done', outcome: { kind: 'error', message: '문제가 발생했어요.' } });
    }
  }, [state.status]);

  const reset = useCallback(() => {
    activeKey.current = null;
    setState({ status: 'idle' });
  }, []);

  return { state, run, reset };
}
