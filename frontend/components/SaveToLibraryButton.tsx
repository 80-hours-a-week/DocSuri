'use client';

import { useState } from 'react';
import { getApiClient } from '@/lib/api';
import type { ResultCardVM } from '@/types/generated';
import styles from './library/Library.module.css';

// SaveToLibraryButton (US-L2, FR-9) — adds the card to the user's library with a
// preserved meta snapshot (the 7 card fields, BR-L5; no internal score, SEC-9).
// Add is idempotent server-side, so a repeat add safely lands on "담김".
export function SaveToLibraryButton({ card }: { card: ResultCardVM }) {
  const [state, setState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  const onSave = async () => {
    if (state === 'saving' || state === 'saved') return;
    setState('saving');
    try {
      await getApiClient().addToLibrary({
        arXivId: card.arxivId,
        meta: {
          title: card.title,
          authors: card.authors,
          year: card.year,
          arxivId: card.arxivId,
          abstractSnippet: card.abstractSnippet,
          arxivUrl: card.arxivUrl,
        },
      });
      setState('saved');
    } catch {
      setState('error');
    }
  };

  const label = state === 'saved' ? '담김' : state === 'error' ? '재시도' : '담기';
  return (
    <button
      type="button"
      className={styles.save}
      onClick={() => void onSave()}
      disabled={state === 'saving' || state === 'saved'}
      aria-label={state === 'saved' ? '라이브러리에 담김' : '라이브러리에 담기'}
      data-testid="save-to-library"
    >
      {label}
    </button>
  );
}
