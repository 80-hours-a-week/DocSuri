'use client';

import { useCallback, useId, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import styles from './SearchScreen.module.css';
import { StateView, type StateViewKind } from './StateView';
import { ResultList } from './ResultList';
import { SaveToLibraryButton } from './SaveToLibraryButton';
import { SaveSearchButton } from './SaveSearchButton';
import { SummaryAction } from './SummaryAction';
import { getApiClient, UserFacingError, type SearchOutcome } from '@/lib/api';
import { validateQuery, MAX_QUERY_LENGTH } from '@/lib/api/validate';
import type { ResultCardVM } from '@/types/generated';

// Per-card actions: U7 [요약] (inline tldr + 상세히 보기) + U4 "담기" (US-L2/S1, Q2=A).
const renderCardActions = (card: ResultCardVM) => (
  <>
    <SummaryAction paperId={card.arxivId} />
    <SaveToLibraryButton card={card} />
  </>
);

// SearchScreen (LC-1/6, US-H1/D1, FR-1/11) — the hero surface. Owns the search
// state machine and branches the SearchResponse union. Single request/response
// with in-flight lock (NFR-P1, BR-U5-18). Client validation is a UX aid; the
// backend ValidationErrorDTO is also honored (BR-U5-3).

type ScreenState =
  | { tag: 'idle' }
  | { tag: 'loading' }
  | { tag: 'outcome'; outcome: SearchOutcome }
  | { tag: 'error'; message: string };

export function SearchScreen() {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [state, setState] = useState<ScreenState>({ tag: 'idle' });
  const [executedQuery, setExecutedQuery] = useState<string | null>(null);
  const [inlineError, setInlineError] = useState<string | null>(null);
  const inFlight = useRef(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const inputId = useId();

  const clearQuery = useCallback(() => {
    setQuery('');
    setInlineError(null);
    inputRef.current?.focus();
  }, []);

  const runSearch = useCallback(async () => {
    if (inFlight.current) return;
    const result = validateQuery(query);
    if (!result.ok) {
      setInlineError(result.message);
      return;
    }
    setInlineError(null);
    inFlight.current = true;
    setState({ tag: 'loading' });
    try {
      const outcome = await getApiClient().search(result.value);
      setExecutedQuery(result.value);
      setState({ tag: 'outcome', outcome });
    } catch (err) {
      if (err instanceof UserFacingError && err.isAuth) {
        router.push('/login?redirect=/search');
        return;
      }
      const message = err instanceof UserFacingError ? err.message : '문제가 발생했습니다. 다시 시도해 주세요.';
      setState({ tag: 'error', message });
    } finally {
      inFlight.current = false;
    }
  }, [query, router]);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void runSearch();
  };

  return (
    <div className={styles.root}>
      <form className={styles.form} onSubmit={onSubmit} data-testid="search-form" role="search">
        <label htmlFor={inputId} className={styles.label}>
          논문 검색
        </label>
        <div className={styles.row}>
          <div className={styles.inputWrap}>
            <input
              ref={inputRef}
              id={inputId}
              className={styles.input}
              type="text"
              value={query}
              maxLength={MAX_QUERY_LENGTH}
              placeholder="무엇이 궁금한가요?"
              spellCheck={false}
              autoCapitalize="none"
              autoCorrect="off"
              onChange={(e) => setQuery(e.target.value)}
              aria-invalid={inlineError ? true : undefined}
              aria-describedby={inlineError ? `${inputId}-err` : undefined}
              data-testid="search-input"
            />
            <button
              type="button"
              className={styles.clear}
              onClick={clearQuery}
              aria-label="검색어 지우기"
              data-testid="search-clear"
            >
              ✕
            </button>
          </div>
          <button
            type="submit"
            className={styles.submit}
            disabled={state.tag === 'loading'}
            data-testid="search-submit"
          >
            검색
          </button>
        </div>
        {inlineError ? (
          <p id={`${inputId}-err`} className={styles.inlineError} role="alert" data-testid="search-inline-error">
            {inlineError}
          </p>
        ) : null}
      </form>

      {state.tag === 'outcome' && executedQuery ? (
        <div className={styles.actions} data-testid="search-actions">
          <SaveSearchButton key={executedQuery} query={executedQuery} />
        </div>
      ) : null}

      <div className={styles.results} aria-live="polite">
        {renderState(state, () => void runSearch())}
      </div>
    </div>
  );
}

function renderState(state: ScreenState, onRetry: () => void) {
  if (state.tag === 'idle') return null;
  if (state.tag === 'loading') return <StateView kind="loading" />;
  if (state.tag === 'error') return <StateView kind="error" message={state.message} onRetry={onRetry} />;

  const { outcome } = state;
  switch (outcome.kind) {
    case 'page':
      return <ResultList cards={outcome.cards} renderAction={renderCardActions} />;
    case 'degraded':
      return <ResultList cards={outcome.cards} degraded renderAction={renderCardActions} />;
    case 'empty':
      return <StateView kind="empty" />;
    case 'abstain':
      return <StateView kind="abstain" />;
    case 'invalid':
      return <StateView kind="invalid" message={outcome.message} />;
    default: {
      const _exhaustive: never = outcome;
      return _exhaustive;
    }
  }
}
