'use client';

// usePaperMeta — loads paper header metadata (title/authors/abstract) for the
// detail route via the ApiClient seam (mock in dev, real BFF when configured).
// PROVISIONAL backend contract (see ApiClient.getPaperMeta). Failure normalizes to
// `null` so the detail page still renders the arXiv id + link-out (no hard error).
import { useCallback, useEffect, useState } from 'react';
import { getApiClient } from '@/lib/api';
import type { PaperMetaVM } from '@/types/paperMeta';

export type PaperMetaState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'done'; meta: PaperMetaVM | null };

export function usePaperMeta(arxivId: string) {
  const [state, setState] = useState<PaperMetaState>({ status: 'idle' });

  const load = useCallback(async (id: string) => {
    setState({ status: 'loading' });
    try {
      const meta = await getApiClient().getPaperMeta(id);
      setState({ status: 'done', meta });
    } catch {
      setState({ status: 'done', meta: null });
    }
  }, []);

  useEffect(() => {
    void load(arxivId);
  }, [arxivId, load]);

  return state;
}
