import styles from './StateView.module.css';

// StateView (LC-6, FR-11, US-D7) — non-technical empty/abstain/degraded/loading/
// error/invalid surface. Abstain and empty are DISTINCT messages (BR-U5-9). No
// stack traces or internal identifiers (SEC-15, BR-U5-11).

export type StateViewKind =
  | 'loading'
  | 'empty'
  | 'abstain'
  | 'invalid'
  | 'error';

interface StateViewProps {
  kind: StateViewKind;
  message?: string;
  onRetry?: () => void;
}

const COPY: Record<StateViewKind, { title: string; body: string }> = {
  loading: { title: '검색 중…', body: '결과를 불러오고 있어요.' },
  empty: { title: '검색 결과가 없습니다', body: '다른 검색어로 다시 시도해 보세요.' },
  abstain: {
    title: '확실한 근거를 찾지 못했습니다',
    body: '신뢰할 만한 결과가 없어 표시하지 않았어요. 검색어를 바꿔 다시 시도해 보세요.',
  },
  invalid: { title: '입력을 확인해 주세요', body: '검색어를 다시 확인해 주세요.' },
  error: { title: '문제가 발생했습니다', body: '잠시 후 다시 시도해 주세요.' },
};

export function StateView({ kind, message, onRetry }: StateViewProps) {
  const copy = COPY[kind];
  return (
    <div
      className={styles.root}
      role="status"
      aria-live="polite"
      aria-busy={kind === 'loading'}
      data-testid={`state-view-${kind}`}
    >
      {kind === 'loading' ? (
        <div className={styles.spinner} aria-hidden="true" />
      ) : null}
      <p className={styles.title}>{copy.title}</p>
      <p className={styles.body}>{message ?? copy.body}</p>
      {onRetry && kind === 'error' ? (
        <button type="button" className={styles.retry} onClick={onRetry} data-testid="state-view-retry">
          다시 시도
        </button>
      ) : null}
    </div>
  );
}
