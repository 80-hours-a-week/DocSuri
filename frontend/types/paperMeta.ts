// PaperMetaVM — hand-authored view model for paper header metadata
// (title/authors/year/abstract) shown on the detail route.
//
// NOT a generated DTO: there is no backend paper-metadata endpoint yet, so this is
// PROVISIONAL (same status as the full-text contract). When the backend lands a
// metadata endpoint with a shared schema, replace this with the generated type.
export interface PaperMetaVM {
  arxivId: string;
  title: string;
  authors: string[];
  year?: number;
  abstract: string;
  /** Canonical arXiv abstract page; rendered as a safe external link-out. */
  arxivUrl?: string;
}
