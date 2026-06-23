'use client';

// useDocModel (D4, BR-SF-11) — fetches the structured doc-model for the rich view.
// real-first transport, in-flight dedup, OA-license-gated (same shape as useAssets). The
// backend reads the lazily-built cached artifact (a not-yet-built doc-model →
// source_unavailable); the lazy build trigger is a separate backend step.
import { useCallback, useRef, useState } from 'react';
import { getApiClient, type DocModelOutcome } from '@/lib/api';
import type { DocModelRequest } from '@/types/generated';

export type DocModelState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'done'; outcome: DocModelOutcome };

export function useDocModel() {
  const [state, setState] = useState<DocModelState>({ status: 'idle' });
  const activeKey = useRef<string | null>(null);

  const load = useCallback(
    async (req: DocModelRequest) => {
      const key = JSON.stringify(req);
      if (activeKey.current === key && state.status !== 'idle') return; // dedup / already loaded
      activeKey.current = key;
      setState({ status: 'loading' });
      try {
        const outcome = await getApiClient().getDocModel(req);
        if (activeKey.current !== key) return;
        setState({ status: 'done', outcome });
      } catch {
        if (activeKey.current !== key) return;
        // Clear the dedup key so a retry (StateView onRetry → load(same req)) can re-fetch;
        // the key only guards in-flight / successfully-loaded requests, not failed ones.
        activeKey.current = null;
        setState({ status: 'done', outcome: { kind: 'error', message: '본문을 불러올 수 없어요.' } });
      }
    },
    [state.status],
  );

  const reset = useCallback(() => {
    activeKey.current = null;
    setState({ status: 'idle' });
  }, []);

  return { state, load, reset };
}
