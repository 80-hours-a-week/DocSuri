import type { ReactNode } from 'react';
import styles from './ResultList.module.css';
import { ResultCard } from './ResultCard';
import type { ResultCardVM } from '@/types/generated';

// ResultList (LC-1/6, FR-3) — ranking-ordered top-N list. When degraded, a
// non-technical banner sits on top; the degradationMode is never shown
// verbatim (BR-U5-8/12). Card order is preserved as received (PBT-03).
// `renderAction` optionally adds a per-card footer control (e.g. save).

interface ResultListProps {
  cards: ResultCardVM[];
  degraded?: boolean;
  renderAction?: (card: ResultCardVM, index: number) => ReactNode;
}

export function ResultList({ cards, degraded = false, renderAction }: ResultListProps) {
  return (
    <section className={styles.list} aria-label="검색 결과" data-testid="result-list">
      {degraded ? (
        <p className={styles.banner} role="status" data-testid="degraded-banner">
          일부 결과만 표시됩니다.
        </p>
      ) : null}
      {cards.map((card, i) => (
        <ResultCard key={`${card.arxivId}-${i}`} card={card} action={renderAction?.(card, i)} />
      ))}
    </section>
  );
}
