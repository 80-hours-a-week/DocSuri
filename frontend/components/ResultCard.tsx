import type { ReactNode } from 'react';
import styles from './ResultCard.module.css';
import type { ResultCardVM } from '@/types/generated';

// ResultCard (LC-6, FR-4/5, SEC-9) — single paper, phone-optimized.
// Renders ONLY the 7 exposed fields (BR-U5-4). External text is escaped by
// React (BR-U5-6). arxivUrl is scheme-checked + noopener (BR-U5-7). relevance is
// rendered as the display value U2 provides — U5 never derives a score (BR-U5-5).
// `action` is an optional footer slot (e.g. save/remove) so the same card serves
// both live results and the library; optional fields (year/snippet/url) are
// guarded for library meta snapshots that may omit them.

interface ResultCardProps {
  card: ResultCardVM;
  action?: ReactNode;
}

/** Allow only http/https links; otherwise drop the href (BR-U5-7). */
function safeHref(url: string): string | undefined {
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:' ? parsed.toString() : undefined;
  } catch {
    return undefined;
  }
}

export function ResultCard({ card, action }: ResultCardProps) {
  const href = safeHref(card.arxivUrl);
  const relevance = card.relevance == null ? null : String(card.relevance);

  return (
    <article className={styles.card} data-testid="result-card">
      <h3 className={styles.title} data-testid="result-card-title">
        {card.title}
      </h3>
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
        <p className={styles.snippet} data-testid="result-card-snippet">
          {card.abstractSnippet}
        </p>
      ) : null}
      <div className={styles.footer}>
        {relevance ? (
          <span className={styles.relevance} data-testid="result-card-relevance">
            관련도 {relevance}
          </span>
        ) : (
          <span />
        )}
        <span className={styles.footerActions}>
          {href ? (
            <a
              className={styles.link}
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              data-testid="result-card-link"
            >
              arXiv에서 보기
            </a>
          ) : null}
          {action}
        </span>
      </div>
    </article>
  );
}
