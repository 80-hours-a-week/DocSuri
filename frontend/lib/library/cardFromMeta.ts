import type { LibraryItemMeta, ResultCardVM } from '@/types/generated';

// Map a preserved library meta snapshot (BR-L5) onto the shared ResultCardVM so
// the library reuses ResultCard — WITHOUT the live index (availability isolation,
// NFR-R1). relevance is intentionally absent (a saved card has no live ranking,
// SEC-9). Missing optional fields are normalized so ResultCard can guard them.
export function cardFromMeta(meta: LibraryItemMeta): ResultCardVM {
  return {
    title: meta.title,
    authors: meta.authors ?? [],
    year: meta.year ?? 0,
    arxivId: meta.arxivId,
    abstractSnippet: meta.abstractSnippet ?? '',
    relevance: null,
    arxivUrl: meta.arxivUrl ?? '',
  };
}
