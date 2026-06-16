import { describe, it, expect } from 'vitest';
import type { ResultCardVM, SearchResultPageDTO, SessionInfo } from '@/types/generated';
import { pageResponse, degradedResponse } from '@/mocks/searchFixtures';
import { mockLogin } from '@/mocks/accountFixtures';

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
