'use client';

// PaperDetailIsland (P3·P5) — the client island inside the SSR /paper/[id] shell.
// Owns activeView/persona/anchor, runs useSummarize, maps the outcome union to the
// rendered surface (BR-SF-14, no infinite loading). Anchor click opens the
// full-text viewer + highlight (Q5=C). real-first: real BFF transport, no mock.
import { useEffect, useState } from 'react';
import type { AnchorVM, Persona, SummarizeRequest, SummarizeScope } from '@/types/generated';
import { useSummarize } from '@/lib/useSummarize';
import { SummaryActions, type DetailView } from './SummaryActions';
import { PersonaToggle } from './PersonaToggle';
import { SummaryView } from './SummaryView';
import { TranslationView } from './TranslationView';
import { FullTextViewer } from './FullTextViewer';
import { StateView } from './StateView';
import styles from './PaperDetailIsland.module.css';

interface PaperDetailIslandProps {
  paperId: string;
  version: number;
  arxivUrl?: string;
}

function buildRequest(
  view: DetailView,
  persona: Persona,
  paperId: string,
  version: number,
): SummarizeRequest {
  if (view === 'summary') return { task: 'summary', paperId, version, persona };
  const scope: SummarizeScope = view === 'fullTrans' ? 'full' : 'abstract';
  return { task: 'translate', paperId, version, scope };
}

const LOADING_TITLE: Record<DetailView, string> = {
  summary: '요약 생성 중…',
  abstractTrans: '초록 번역 중…',
  fullTrans: '전문 번역 중… (시간이 걸릴 수 있어요)',
};

export function PaperDetailIsland({ paperId, version, arxivUrl }: PaperDetailIslandProps) {
  const [view, setView] = useState<DetailView>('summary');
  const [persona, setPersona] = useState<Persona>('expert');
  const [anchor, setAnchor] = useState<AnchorVM | null>(null);
  const { state, run } = useSummarize();

  // Re-request on view/persona change; the backend cache returns cached results
  // instantly (BR-SF-5/6), so switching is cheap.
  useEffect(() => {
    setAnchor(null);
    void run(buildRequest(view, persona, paperId, version));
  }, [view, persona, paperId, version, run]);

  const retry = () => void run(buildRequest(view, persona, paperId, version));

  function renderResult() {
    if (state.status === 'idle' || state.status === 'loading') {
      return <StateView kind="loading" title={LOADING_TITLE[view]} message="잠시만 기다려 주세요." />;
    }
    const { outcome } = state;
    switch (outcome.kind) {
      case 'summary':
        return <SummaryView summary={outcome.summary} cached={outcome.cached} onAnchor={setAnchor} />;
      case 'translation':
        return (
          <TranslationView
            translation={outcome.translation}
            scope={view === 'fullTrans' ? 'full' : 'abstract'}
            cached={outcome.cached}
          />
        );
      case 'abstain':
        return <StateView kind="abstain" message="근거가 부족해 요약/번역을 보류했어요." />;
      case 'degraded':
        return <StateView kind="degraded" message={outcome.message} onRetry={retry} />;
      case 'sourceUnavailable':
        return <StateView kind="sourceUnavailable" />;
      case 'invalid':
        return <StateView kind="invalid" message={outcome.message} />;
      case 'error':
        return <StateView kind="error" message={outcome.message} onRetry={retry} />;
    }
  }

  return (
    <div className={styles.root}>
      <div className={styles.actionsBar}>
        <SummaryActions active={view} onSelect={setView} />
        {view === 'summary' ? (
          <section className={styles.personaSection} aria-label="요약 수준">
            <span className={styles.personaLabel}>요약 수준</span>
            <PersonaToggle value={persona} onChange={setPersona} />
          </section>
        ) : null}
      </div>

      <div className={styles.result} data-testid="detail-result">
        {renderResult()}
      </div>

      {anchor ? (
        <section className={styles.viewer} aria-label="원문 출처 보기">
          <h3 className={styles.viewerTitle}>출처: {anchor.label}</h3>
          <FullTextViewer paperId={paperId} version={version} anchor={anchor} arxivUrl={arxivUrl} />
        </section>
      ) : null}
    </div>
  );
}
