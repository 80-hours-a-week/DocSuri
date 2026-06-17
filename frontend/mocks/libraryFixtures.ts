// Mock U4 (saved searches / library / history) state — derived from
// shared/dtos/library.schema.json (BR-U5-19). In-memory + stateful so the screens
// demo add/delete/save/clear and cursor pagination without live infra. owner
// userId is never present (SEC-8/9); cursors are opaque (offset-encoded here).
import type {
  SavedSearchDTO,
  SavedSearchCreateDTO,
  SavedSearchPageDTO,
  LibraryItemDTO,
  LibraryItemCreateDTO,
  LibraryItemMeta,
  LibraryPageDTO,
  HistoryEntry,
  HistoryPageDTO,
} from '@/types/generated';
import { pageResponse } from './searchFixtures';

function metaFromCard(i: number): LibraryItemMeta {
  const c = pageResponse.cards[i % pageResponse.cards.length];
  return {
    title: c.title,
    authors: c.authors,
    year: c.year,
    arxivId: c.arxivId,
    abstractSnippet: c.abstractSnippet,
    arxivUrl: c.arxivUrl,
  };
}

let seq = 0;
const id = (prefix: string): string => `${prefix}_${(++seq).toString(36)}_mock`;
const now = (offsetMin: number): string => new Date(Date.now() - offsetMin * 60_000).toISOString();

// ── seeded state ─────────────────────────────────────────────────────────────
let savedSearches: SavedSearchDTO[] = [
  { id: id('ss'), query: 'transformer attention', label: '서베이용', createdAt: now(30) },
  { id: id('ss'), query: '한국어 임베딩', createdAt: now(120) },
];

// 22 items so a default page (limit 20) leaves a nextCursor — demoing "더 보기".
let libraryItems: LibraryItemDTO[] = Array.from({ length: 22 }, (_, i) => ({
  id: id('li'),
  arXivId: metaFromCard(i).arxivId,
  meta: metaFromCard(i),
  addedAt: now(i * 7),
}));

let history: HistoryEntry[] = [
  { id: id('h'), query: 'transformer', executedAt: now(5), resultCount: 3 },
  { id: id('h'), query: '없음 테스트', executedAt: now(45), resultCount: 0 },
  { id: id('h'), query: 'residual learning', executedAt: now(90), resultCount: 12 },
];

// ── opaque cursor (offset) ───────────────────────────────────────────────────
function decodeCursor(cursor?: string): number {
  if (!cursor) return 0;
  const n = Number.parseInt(cursor, 10);
  return Number.isFinite(n) && n >= 0 ? n : 0;
}
function paginate<T>(all: T[], limit: number, cursor?: string): { items: T[]; nextCursor?: string } {
  const start = decodeCursor(cursor);
  const items = all.slice(start, start + limit);
  const next = start + limit;
  return next < all.length ? { items, nextCursor: String(next) } : { items };
}

// ── saved searches ───────────────────────────────────────────────────────────
export function mockListSaved(limit: number, cursor?: string): SavedSearchPageDTO {
  return paginate(savedSearches, limit, cursor);
}
export function mockCreateSaved(dto: SavedSearchCreateDTO): SavedSearchDTO {
  const item: SavedSearchDTO = {
    id: id('ss'),
    query: dto.query,
    ...(dto.label ? { label: dto.label } : {}),
    createdAt: new Date().toISOString(),
  };
  savedSearches = [item, ...savedSearches];
  return item;
}
export function mockDeleteSaved(itemId: string): boolean {
  const before = savedSearches.length;
  savedSearches = savedSearches.filter((s) => s.id !== itemId);
  return savedSearches.length < before;
}

// ── library ──────────────────────────────────────────────────────────────────
export function mockListLibrary(limit: number, cursor?: string): LibraryPageDTO {
  return paginate(libraryItems, limit, cursor);
}
export function mockAddLibrary(dto: LibraryItemCreateDTO): LibraryItemDTO {
  // Idempotent on arXivId (BR-L3): return the existing item if already present.
  const existing = libraryItems.find((it) => it.arXivId === dto.arXivId);
  if (existing) return existing;
  const item: LibraryItemDTO = {
    id: id('li'),
    arXivId: dto.arXivId,
    meta: dto.meta,
    addedAt: new Date().toISOString(),
  };
  libraryItems = [item, ...libraryItems];
  return item;
}
export function mockRemoveLibrary(itemId: string): boolean {
  const before = libraryItems.length;
  libraryItems = libraryItems.filter((it) => it.id !== itemId);
  return libraryItems.length < before;
}

// ── history ──────────────────────────────────────────────────────────────────
export function mockListHistory(limit: number, cursor?: string): HistoryPageDTO {
  return paginate(history, limit, cursor);
}
export function mockClearHistory(): void {
  history = [];
}
