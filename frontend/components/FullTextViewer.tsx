'use client';

// FullTextViewer (Q5=C, P4·P6, BR-SF-8/11/12) — fetches normalized full text via
// the (provisional) backend full-text API and highlights the anchor span. real-first:
// real BFF transport, no production mock. OA-license-gated: license_unavailable →
// arXiv link-out guidance. External text escaped by React (BR-SF-9).
//
// NOTE: rendered in a scrollable container with single-span highlight. Windowing/
// virtualization for very large papers is a perf follow-up once real full-text
// sizes are measured (Build & Test) — not added preemptively.
import { useEffect, useRef } from 'react';
import type { AnchorVM } from '@/types/generated';
import { useFullText } from '@/lib/useFullText';
import { StateView } from './StateView';
import styles from './FullTextViewer.module.css';

interface FullTextViewerProps {
  paperId: string;
  version: number;
  /** Anchor whose span to highlight + scroll to, if any. */
  anchor?: AnchorVM | null;
  arxivUrl?: string;
}

function splitOnSpan(text: string, span?: string): [string, string | null, string] {
  if (!span) return [text, null, ''];
  const idx = text.indexOf(span);
  if (idx < 0) return [text, null, ''];
  return [text.slice(0, idx), span, text.slice(idx + span.length)];
}

export function FullTextViewer({ paperId, version, anchor, arxivUrl }: FullTextViewerProps) {
  const { state, load } = useFullText();
  const markRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    void load({ paperId, version });
  }, [paperId, version, load]);

  const text = state.status === 'done' && state.outcome.kind === 'page' ? state.outcome.text : null;

  useEffect(() => {
    if (text && markRef.current) {
      markRef.current.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
  }, [text, anchor]);

  if (state.status === 'idle' || state.status === 'loading') {
    return <StateView kind="loading" title="원문 불러오는 중…" message="원문을 가져오고 있어요." />;
  }

  const { outcome } = state;
  switch (outcome.kind) {
    case 'licenseUnavailable':
      return (
        <div className={styles.gate} data-testid="fulltext-license">
          <StateView kind="licenseUnavailable" />
          {arxivUrl ? (
            <a className={styles.link} href={arxivUrl} target="_blank" rel="noopener noreferrer">
              arXiv에서 원문 보기
            </a>
          ) : null}
        </div>
      );
    case 'sourceUnavailable':
      return <StateView kind="sourceUnavailable" />;
    case 'error':
      return <StateView kind="error" message={outcome.message} onRetry={() => load({ paperId, version })} />;
    case 'page': {
      const [before, match, after] = splitOnSpan(outcome.text, anchor?.span);
      return (
        <div className={styles.root} data-testid="fulltext-viewer">
          <p className={styles.note}>
            원문은 참고문헌·저자 정보 등이 제거된 정규화 텍스트예요. 정확한 원문은{' '}
            {arxivUrl ? (
              <a href={arxivUrl} target="_blank" rel="noopener noreferrer">
                arXiv
              </a>
            ) : (
              'arXiv'
            )}
            에서 확인하세요.
          </p>
          <div className={styles.text}>
            {before}
            {match ? (
              <mark ref={markRef as React.RefObject<HTMLElement>} className={styles.mark}>
                {match}
              </mark>
            ) : null}
            {after}
          </div>
        </div>
      );
    }
  }
}
