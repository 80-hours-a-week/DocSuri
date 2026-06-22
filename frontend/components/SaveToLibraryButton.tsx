'use client';

import { useState } from 'react';
import { getApiClient } from '@/lib/api';
import styles from './SaveToLibraryButton.module.css';

// SaveToLibraryButton (US-L2, FR-9) — saves the paper to the user's library with a
// preserved meta snapshot (BR-L5; no internal score, SEC-9). Add is idempotent
// server-side, so a repeat add safely lands on the saved state. Rendered as a
// bookmark icon (a result card's top-right corner, or the paper detail header); the
// visible label is the accessible name, and the icon fills once saved.

// Minimal save target — satisfied by ResultCardVM and by the detail page's PaperMeta.
export interface SaveTarget {
  arxivId: string;
  title: string;
  authors: string[];
  year?: number | null;
  abstractSnippet?: string;
  arxivUrl?: string;
}

export function SaveToLibraryButton({ card }: { card: SaveTarget }) {
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
          year: card.year ?? null,
          arxivId: card.arxivId,
          abstractSnippet: card.abstractSnippet ?? '',
          arxivUrl: card.arxivUrl ?? '',
        },
      });
      setState('saved');
    } catch {
      setState('error');
    }
  };

  const saved = state === 'saved';
  const label = saved
    ? '라이브러리에 담김'
    : state === 'error'
      ? '담기 실패 — 다시 시도'
      : state === 'saving'
        ? '담는 중'
        : '라이브러리에 담기';

  return (
    <button
      type="button"
      className={styles.bookmark}
      data-state={state}
      onClick={() => void onSave()}
      disabled={state === 'saving' || saved}
      aria-pressed={saved}
      aria-label={label}
      title={label}
      data-testid="save-to-library"
    >
      <svg
        className={styles.icon}
        width="20"
        height="20"
        viewBox="0 0 24 24"
        aria-hidden="true"
        fill={saved ? 'currentColor' : 'none'}
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z" />
      </svg>
    </button>
  );
}
