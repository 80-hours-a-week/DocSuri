/* Curated from shared/dtos/library.schema.json (exposed contract). Run `pnpm gen:types`
 * to refresh the raw schema dump under types/.schema-raw/ for drift review.
 * Producer: U4. Consumer: U5. SEC-8/9: owner userId NOT exposed. Cursor pagination. */

import type { SearchResultPageDTO } from './search';

/** Cursor-based pagination input common to all collection queries. */
export interface PageParams {
  limit: number;
  /** Opaque continuation token; absent on the first-page request. */
  cursor?: string;
}

/** New saved-search input. owner is server-determined from session (SEC-8). */
export interface SavedSearchCreateDTO {
  query: string;
  label?: string;
}

/** Single saved search (owner userId NOT exposed, SEC-9). */
export interface SavedSearchDTO {
  id: unknown;
  query: string;
  label?: string;
  /** RFC 3339 / ISO 8601 date-time. */
  createdAt: string;
}

/** Page of the user's saved searches, most-recent first (owner-scoped server-side). */
export interface SavedSearchPageDTO {
  items: SavedSearchDTO[];
  /** Continuation cursor for the next page (absent on the last page). */
  nextCursor?: string;
}

/**
 * Refined shape of LibraryItemDTO.meta (BR-L5): a bounded snapshot of the result
 * card so the library renders without the live index (availability isolation).
 * NOTE: the schema declares `meta` as `Any` and defers the shape to U4 FD; this
 * mirrors the backend `LibraryItemMeta`. Field is `arxivId` (lowercase x) here —
 * matching the card — distinct from the top-level wire field `arXivId` (capital X).
 */
export interface LibraryItemMeta {
  title: string;
  authors: string[];
  year?: number | null;
  arxivId: string;
  abstractSnippet?: string | null;
  arxivUrl?: string | null;
}

/** Idempotent library-add input. owner NOT in the body (SEC-8). */
export interface LibraryItemCreateDTO {
  /** Display arXiv ID (wire field name is `arXivId`, capital X — per the schema). */
  arXivId: string;
  /** Metadata snapshot captured at add time (availability isolation). */
  meta: LibraryItemMeta;
}

/** Single library item (owner userId NOT exposed, SEC-9). Idempotent add returns the same shape. */
export interface LibraryItemDTO {
  id: unknown;
  /** Display arXiv ID (wire field name is `arXivId`, capital X — per the schema). */
  arXivId: string;
  meta: LibraryItemMeta;
  /** RFC 3339 / ISO 8601 date-time. */
  addedAt: string;
}

/** Page of the user's library (owner-scoped server-side). Preserved meta snapshots only. */
export interface LibraryPageDTO {
  items: LibraryItemDTO[];
  /** Continuation cursor for the next page (absent on the last page). */
  nextCursor?: string;
}

/** Single search-history entry (source: SearchExecutedEvent; owner userId NOT exposed, SEC-9). */
export interface HistoryEntry {
  id: unknown;
  query: string;
  /** RFC 3339 / ISO 8601 date-time. */
  executedAt: string;
  resultCount: number;
}

/** Page of recent search history, most-recent first (owner-scoped server-side). */
export interface HistoryPageDTO {
  items: HistoryEntry[];
  /** Continuation cursor for the next page (absent on the last page). */
  nextCursor?: string;
}

/**
 * Saved-search / history RERUN result. Surfaces a gateway-fronted search
 * (U6.ApiGatewayMiddleware -> U2) as the §1 search card page DTO — it REUSES
 * SearchResultPageDTO (NOT a direct U2 call). Branched by classifySearchResponse.
 */
export type SearchResultSetDTO = SearchResultPageDTO;
