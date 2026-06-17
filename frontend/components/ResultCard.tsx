import styles from './ResultCard.module.css';
import type { ResultCardVM } from '@/types/generated';

// ResultCard (LC-6, FR-4/5, SEC-9) — single paper, phone-optimized.
// Renders ONLY the 7 exposed fields (BR-U5-4). External text is escaped by
// React (BR-U5-6). arxivUrl is scheme-checked + noopener (BR-U5-7). relevance is
// rendered as the display value U2 provides — U5 never derives a score (BR-U5-5).

interface ResultCardProps {
  card: ResultCardVM;
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

export function ResultCard({ card }: ResultCardProps) {
  const href = safeHref(card.arxivUrl);
  const relevance = card.relevance == null ? null : String(card.relevance);

  return (
    <article className={styles.card} data-testid="result-card">
      <h3 className={styles.title} data-testid="result-card-title">
        {card.title}
      </h3>
      <p className={styles.meta}>
        <span data-testid="result-card-authors">{card.authors.join(', ')}</span>
        <span aria-hidden="true"> · </span>
        <span data-testid="result-card-year">{card.year}</span>
        <span aria-hidden="true"> · </span>
        <span data-testid="result-card-arxiv-id">arXiv:{card.arxivId}</span>
      </p>
      <p className={styles.snippet} data-testid="result-card-snippet">
        {card.abstractSnippet}
      </p>
      <div className={styles.footer}>
        {relevance ? (
          <span className={styles.relevance} data-testid="result-card-relevance">
            관련도 {relevance}
          </span>
        ) : (
          <span />
        )}
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
      </div>
    </article>
  );
}
