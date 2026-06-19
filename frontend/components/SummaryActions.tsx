'use client';

// SummaryActions (Q6, SSOT §5) — the 3 explicit detail-page actions. Each maps to
// a distinct task/scope request (BR-SF-3). Full translation is the heavy one; the
// surface shows a loading indicator rather than a hard gate (BR-SF-3b).
import styles from './SummaryActions.module.css';

export type DetailView = 'summary' | 'abstractTrans' | 'fullTrans';

interface SummaryActionsProps {
  active: DetailView;
  onSelect: (view: DetailView) => void;
}

const ACTIONS: { view: DetailView; label: string }[] = [
  { view: 'summary', label: '요약' },
  { view: 'abstractTrans', label: '초록 번역' },
  { view: 'fullTrans', label: '전문 번역' },
];

export function SummaryActions({ active, onSelect }: SummaryActionsProps) {
  return (
    <div className={styles.root} role="tablist" aria-label="요약/번역 액션">
      {ACTIONS.map((a) => (
        <button
          key={a.view}
          type="button"
          role="tab"
          aria-selected={active === a.view}
          className={active === a.view ? styles.active : styles.action}
          onClick={() => onSelect(a.view)}
          data-testid={`detail-action-${a.view}`}
        >
          {a.label}
        </button>
      ))}
    </div>
  );
}
