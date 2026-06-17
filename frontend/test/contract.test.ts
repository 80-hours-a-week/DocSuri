import { describe, it, expect } from 'vitest';
import type {
  ResultCardVM,
  SearchResultPageDTO,
  SessionInfo,
  LibraryPageDTO,
  SavedSearchPageDTO,
  HistoryPageDTO,
} from '@/types/generated';
import { pageResponse, degradedResponse } from '@/mocks/searchFixtures';
import { mockLogin } from '@/mocks/accountFixtures';
import { mockListLibrary, mockListSaved, mockListHistory } from '@/mocks/libraryFixtures';

// DTO contract test (LC-7) — the mock fixtures must conform to the generated
// types (which derive from shared/dtos). If the schema/types drift, this fails.

const CARD_FIELDS: (keyof ResultCardVM)[] = [
  'title',
  'authors',
  'year',
  'arxivId',
  'abstractSnippet',
  'relevance',
  'arxivUrl',
];

describe('DTO contract', () => {
  it('page fixture conforms to SearchResultPageDTO', () => {
    const page: SearchResultPageDTO = pageResponse;
    expect(page.meta.resultCount).toBe(page.cards.length);
    expect(typeof page.meta.degraded).toBe('boolean');
  });

  it('every card exposes exactly the 7 contract fields (SEC-9)', () => {
    for (const card of pageResponse.cards) {
      expect(Object.keys(card).sort()).toEqual([...CARD_FIELDS].sort());
    }
  });

  it('degraded fixture carries meta.degraded=true', () => {
    expect(degradedResponse.meta.degraded).toBe(true);
  });

  it('session fixture conforms to SessionInfo and hides the token', () => {
    const s: SessionInfo = mockLogin('a@b.co');
    expect(s.userId).toBeTruthy();
    expect('token' in s).toBe(false);
  });
});

const META_FIELDS = ['title', 'authors', 'year', 'arxivId', 'abstractSnippet', 'arxivUrl'];

describe('U4 library DTO contract', () => {
  it('library page conforms to LibraryPageDTO; meta carries only card fields (SEC-9)', () => {
    const page: LibraryPageDTO = mockListLibrary(20, undefined);
    expect(page.items.length).toBeGreaterThan(0);
    const item = page.items[0];
    expect(Object.keys(item.meta).sort()).toEqual([...META_FIELDS].sort());
    // No internal score/relevance and no owner userId leak into the snapshot.
    expect('relevance' in item.meta).toBe(false);
    expect('userId' in (item as unknown as Record<string, unknown>)).toBe(false);
    expect('score' in (item as unknown as Record<string, unknown>)).toBe(false);
  });

  it('saved-search page conforms to SavedSearchPageDTO (owner not exposed)', () => {
    const page: SavedSearchPageDTO = mockListSaved(20, undefined);
    expect(page.items[0].query).toBeTruthy();
    expect('userId' in (page.items[0] as unknown as Record<string, unknown>)).toBe(false);
  });

  it('history page conforms to HistoryPageDTO', () => {
    const page: HistoryPageDTO = mockListHistory(20, undefined);
    expect(typeof page.items[0].resultCount).toBe('number');
    expect(page.items[0].executedAt).toBeTruthy();
  });
});
