'use client';

// SummaryAction (Q1·Q2, card inline) — the card's [요약] action. Tapping requests an
// expert summary and shows the tldr (3-line) inline (a quick peek without navigating;
// the card title links to the full detail route). Heavy/full actions (translation,
// full text, persona switch) live on the detail page, not the card (BR-SF-1).
// External text escaped by React (BR-SF-9).
import { useSummarize } from '@/lib/useSummarize';
import styles from './SummaryAction.module.css';

interface SummaryActionProps {
  paperId: string;
  version?: number;
}

export function SummaryAction({ paperId, version = 1 }: SummaryActionProps) {
  const { state, run } = useSummarize();

  const onSummarize = () => void run({ task: 'summary', paperId, version, persona: 'expert' });

  return (
    <span className={styles.root}>
      {state.status === 'idle' ? (
        <button
          type="button"
          className={styles.button}
          onClick={onSummarize}
          data-testid="card-summary-action"
        >
          요약
        </button>
      ) : null}

      {state.status === 'loading' ? <span className={styles.loading}>요약 생성 중…</span> : null}

      {state.status === 'done' ? (
        <span className={styles.result}>
          {state.outcome.kind === 'summary' ? (
            <span className={styles.tldr} data-testid="card-summary-tldr">
              {state.outcome.summary.tldr}
            </span>
          ) : state.outcome.kind === 'abstain' ? (
            <span className={styles.note}>근거가 부족해 요약을 보류했어요.</span>
          ) : state.outcome.kind === 'degraded' ? (
            <span className={styles.note}>AI 요약이 일시 중단됐어요.</span>
          ) : state.outcome.kind === 'sourceUnavailable' ? (
            <span className={styles.note}>원문을 가져올 수 없어요.</span>
          ) : (
            <span className={styles.note}>요약을 불러오지 못했어요.</span>
          )}
        </span>
      ) : null}
    </span>
  );
}
