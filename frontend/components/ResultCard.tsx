import type { ReactNode } from 'react';
import Link from 'next/link';
import styles from './ResultCard.module.css';
import type { ResultCardVM } from '@/types/generated';

// ResultCard (LC-6, FR-4/5, SEC-9) — single paper, phone-optimized.
// Renders ONLY the exposed fields (BR-U5-4). External text is escaped by React
// (BR-U5-6). relevance is the display value U2 provides — U5 never derives a score
// (BR-U5-5). Title and abstract snippet link to the paper detail route (/paper/[id]).
// `action` is an optional footer slot (e.g. [요약], save/remove) so the same card
// serves both live results and the library.

interface ResultCardProps {
  card: ResultCardVM;
  action?: ReactNode;
}

export function ResultCard({ card, action }: ResultCardProps) {
  const relevance = card.relevance == null ? null : String(card.relevance);
  const detailHref = `/paper/${encodeURIComponent(card.arxivId)}`;

  return (
    <article className={styles.card} data-testid="result-card">
      <Link className={styles.titleLink} href={detailHref} data-testid="result-card-title">
        <h3 className={styles.title}>{card.title}</h3>
      </Link>
      <p className={styles.meta}>
        <span data-testid="result-card-authors">{card.authors.join(', ')}</span>
        {card.year ? (
          <>
            <span aria-hidden="true"> · </span>
            <span data-testid="result-card-year">{card.year}</span>
          </>
        ) : null}
        <span aria-hidden="true"> · </span>
        <span data-testid="result-card-arxiv-id">arXiv:{card.arxivId}</span>
      </p>
      {card.abstractSnippet ? (
        <Link className={styles.snippetLink} href={detailHref} data-testid="result-card-snippet">
          <p className={styles.snippet}>{card.abstractSnippet}</p>
        </Link>
      ) : null}
      <div className={styles.footer}>
        {relevance ? (
          <span className={styles.relevance} data-testid="result-card-relevance">
            관련도 {relevance}
          </span>
        ) : (
          <span />
        )}
        <span className={styles.footerActions}>{action}</span>
      </div>
    </article>
  );
}
