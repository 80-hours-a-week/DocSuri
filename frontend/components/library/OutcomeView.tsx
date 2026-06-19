'use client';

import { ResultList } from '../ResultList';
import { StateView } from '../StateView';
import { SummaryAction } from '../SummaryAction';
import type { SearchOutcome } from '@/lib/api';
import type { ResultCardVM } from '@/types/generated';

// Per-card [요약] action on library rerun results too (Q2=A).
const renderSummaryAction = (card: ResultCardVM) => <SummaryAction paperId={card.arxivId} />;

// OutcomeView (US-D7) — renders a classified SearchOutcome (used by saved-search
// and history rerun). Mirrors the search state machine's terminal branches so
// abstain stays distinct from empty (BR-U5-9). Exhaustive over the union.
export function OutcomeView({ outcome }: { outcome: SearchOutcome }) {
  switch (outcome.kind) {
    case 'page':
      return <ResultList cards={outcome.cards} renderAction={renderSummaryAction} />;
    case 'degraded':
      return <ResultList cards={outcome.cards} degraded renderAction={renderSummaryAction} />;
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
