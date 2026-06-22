'use client';

import { useEffect, useRef, useState } from 'react';
import type { TranslationVM } from '@/types/generated';
import { useGlossaryTerms } from '@/lib/useGlossaryTerms';
import { GlossaryTermBadge } from './GlossaryTermBadge';
import styles from './TranslationView.module.css';

// TranslationView (US-S2, BR-SF-9) — Korean translation (abstract or full per
// scope) + kept-terms badges (untranslated terms kept as-is). External text is
// escaped by React. No anchors (translation is grounding-free). The scope label is
// not repeated here — the modal heading already names 초록/전문 번역.
// Each kept-term badge is tappable (GlossaryTermBadge) to save a personal rendering
// (개인 용어집 Phase 1). This view owns the "which badge is editing" state so only one
// editor is open at a time, and a click outside the badge row closes it.

interface TranslationViewProps {
  translation: TranslationVM;
  cached?: boolean;
}

export function TranslationView({ translation, cached }: TranslationViewProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const termsRef = useRef<HTMLDivElement | null>(null);
  const { terms, setTerm } = useGlossaryTerms();

  // Close the open editor on any pointer-down outside the badge row (mousedown fires
  // before click, so a tap elsewhere dismisses before it activates anything).
  useEffect(() => {
    if (openIndex === null) return;
    const onPointerDown = (e: MouseEvent) => {
      if (termsRef.current && !termsRef.current.contains(e.target as Node)) {
        setOpenIndex(null);
      }
    };
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, [openIndex]);

  return (
    <div className={styles.root} data-testid="translation-view">
      {cached ? (
        <span className={styles.cached} data-testid="translation-cached">
          저장된 결과
        </span>
      ) : null}

      {translation.keptTerms.length > 0 ? (
        <div className={styles.terms} ref={termsRef}>
          {translation.keptTerms.map((t, i) => (
            <GlossaryTermBadge
              key={`${t}-${i}`}
              term={t}
              open={openIndex === i}
              onOpen={() => setOpenIndex(i)}
              onClose={() => setOpenIndex(null)}
              initialValue={terms[t] ?? ''}
              onSaved={(termTo) => setTerm(t, termTo)}
            />
          ))}
        </div>
      ) : null}

      <p className={styles.text}>{translation.koreanText}</p>
    </div>
  );
}
