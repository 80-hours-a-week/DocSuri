'use client';

// useFullText (P4·P6, Q5=C, BR-SF-11) — fetches normalized full text for the
// in-app viewer. real-first: real BFF transport, no production mock. PROVISIONAL
// backend contract — integrates when the backend full-text-return API lands (§6).
import { useCallback, useRef, useState } from 'react';
import { getApiClient, type FullTextOutcome } from '@/lib/api';
import type { FullTextRequest } from '@/types/generated';

export type FullTextState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'done'; outcome: FullTextOutcome };

export function useFullText() {
  const [state, setState] = useState<FullTextState>({ status: 'idle' });
  const activeKey = useRef<string | null>(null);

  const load = useCallback(async (req: FullTextRequest) => {
    const key = JSON.stringify(req);
    if (activeKey.current === key && state.status !== 'idle') return; // dedup / already loaded
    activeKey.current = key;
    setState({ status: 'loading' });
    try {
      const outcome = await getApiClient().getFullText(req);
      if (activeKey.current !== key) return;
      setState({ status: 'done', outcome });
    } catch {
      if (activeKey.current !== key) return;
      setState({ status: 'done', outcome: { kind: 'error', message: '원문을 불러올 수 없어요.' } });
    }
  }, [state.status]);

  const reset = useCallback(() => {
    activeKey.current = null;
    setState({ status: 'idle' });
  }, []);

  return { state, load, reset };
}
