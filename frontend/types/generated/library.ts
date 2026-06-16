/* Curated from shared/dtos/library.schema.json (exposed contract). Run `pnpm gen:types`
 * to refresh the raw schema dump under types/.schema-raw/ for drift review.
 * Producer: U4. Consumer: U5. SEC-8/9: owner userId NOT exposed. Cursor pagination. */

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
  createdAt: string;
}
