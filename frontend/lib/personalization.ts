import { getApiClient } from '@/lib/api';
import type { AnchorVM, Persona, SummarizeScope } from '@/types/generated';
import type { BehaviorEventCreate } from '@/types/personalization';

function suffix(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function hashQuery(query: string): string {
  let hash = 0x811c9dc5;
  for (const ch of query.trim().toLowerCase()) {
    hash ^= ch.charCodeAt(0);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, '0');
}

export function recordBehaviorEvent(event: BehaviorEventCreate): void {
  void getApiClient().recordBehaviorEvent(event).catch(() => undefined);
}

export function recordSearchExecuted(query: string, resultCount: number): void {
  const queryHash = hashQuery(query);
  recordBehaviorEvent({
    eventType: 'search_executed',
    subject: { kind: 'search', queryHash },
    source: 'frontend_anchor',
    metadata: { resultCount },
    dedupeKey: `search:${queryHash}:${suffix()}`,
  });
}

export function recordPaperOpened(paperId: string): void {
  recordBehaviorEvent({
    eventType: 'paper_opened',
    subject: { kind: 'paper', paperId },
    source: 'frontend_anchor',
    metadata: { entrySurface: 'detail' },
    dedupeKey: `paper:${paperId}:${suffix()}`,
  });
}

export function recordLibraryAdded(paperId: string): void {
  recordBehaviorEvent({
    eventType: 'library_added',
    subject: { kind: 'paper', paperId },
    source: 'frontend_anchor',
    metadata: { savedSource: 'library' },
    dedupeKey: `library:add:${paperId}:${suffix()}`,
  });
}

export function recordLibraryRemoved(paperId: string): void {
  recordBehaviorEvent({
    eventType: 'library_removed',
    subject: { kind: 'paper', paperId },
    source: 'frontend_anchor',
    metadata: {},
    dedupeKey: `library:remove:${paperId}:${suffix()}`,
  });
}

export function recordSummaryRequest(
  paperId: string,
  mode: 'summary' | 'translation',
  options: { persona?: Persona; scope?: SummarizeScope } = {},
): void {
  recordBehaviorEvent({
    eventType: 'summary_translation_requested',
    subject: { kind: mode === 'summary' ? 'summary' : 'translation', paperId },
    source: 'frontend_anchor',
    metadata: {
      mode,
      ...(options.persona ? { selectedPersona: options.persona } : {}),
      ...(options.scope ? { translationScope: options.scope } : {}),
    },
    dedupeKey: `${mode}:${paperId}:${options.persona ?? options.scope ?? 'default'}:${suffix()}`,
  });
}

export function recordSourceAnchorClicked(paperId: string, anchor: AnchorVM): void {
  recordBehaviorEvent({
    eventType: 'source_anchor_clicked',
    subject: { kind: 'source_anchor', paperId, anchorId: anchor.field },
    source: 'frontend_anchor',
    metadata: { anchorId: anchor.field, sectionKind: anchor.target },
    dedupeKey: `anchor:${paperId}:${anchor.field}:${suffix()}`,
  });
}
