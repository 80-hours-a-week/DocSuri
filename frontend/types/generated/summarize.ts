/* Provisional — curated ahead of shared/dtos/summarization.schema.json.
 * Producer: U7 Summarization. Consumer: U7 frontend slice. SEC-9: only the fields
 * below are exposed (no tokens/cost/cache-key/model id).
 *
 * NOTE (Q5=C, 2026-06-19): `scope`, `getFullText`/FullText* are a NEW backend
 * contract. These shapes are provisional; re-align via `pnpm gen:types` once the
 * backend full-text-return API + `scope` param are finalized (plan §6). */

export type SummarizeTask = 'summary' | 'translate';
/** translate only; summary is fixed `full`. */
export type SummarizeScope = 'abstract' | 'full';
/** summary only; translation is single (no persona). */
export type Persona = 'expert' | 'beginner';

/** Request to POST /api/summarize. paperId = ResultCardVM.arxivId, version = 1 (Q8=A). */
export interface SummarizeRequest {
  task: SummarizeTask;
  paperId: string;
  version: number;
  scope?: SummarizeScope;
  persona?: Persona;
  targetLang?: 'ko';
  abstract?: string;
}

/** Per-claim grounding anchor (§3). Drives "출처 보기" → full-text highlight (Q5=C). */
export interface AnchorVM {
  field: string;
  target: 'section' | 'table' | 'figure';
  span: string;
  label: string;
}

export interface ReproducibilityVM {
  code: string;
  data: string;
}

/** Structured summary — the 6 persona-driven fields + grounding anchors (§3). */
export interface SummaryVM {
  tldr: string;
  contributions: string[];
  method: string;
  results: string;
  limitations: string;
  reproducibility: ReproducibilityVM;
  anchors: AnchorVM[];
}

/** Korean translation (abstract or full per scope). keptTerms = untranslated terms. */
export interface TranslationVM {
  koreanText: string;
  keptTerms: string[];
}

/** Honest source note (e.g. abstract-based fallback). Internal — no sensitive fields. */
export interface SummaryMeta {
  source?: string;
  fallback?: string;
}

// ---- Response union (status-discriminated; mirrors backend to_dict / SEC-9) ----

export interface SummaryOkDTO {
  status: 'ok';
  task: 'summary';
  meta: SummaryMeta;
  cached: boolean;
  summary: SummaryVM;
}

export interface TranslationOkDTO {
  status: 'ok';
  task: 'translate';
  meta: SummaryMeta;
  cached: boolean;
  translation: TranslationVM;
  scope?: SummarizeScope;
}

export interface SummaryAbstainDTO {
  status: 'abstain';
  reason: unknown;
}

export interface CostDegradedDTO {
  status: 'cost_degraded';
  message: string;
}

export interface SourceUnavailableDTO {
  status: 'source_unavailable';
  reason: unknown;
}

export type SummarizeResponseDTO =
  | SummaryOkDTO
  | TranslationOkDTO
  | SummaryAbstainDTO
  | CostDegradedDTO
  | SourceUnavailableDTO;

// ---- Full-text return (Q5=C, provisional) ----

export interface FullTextRequest {
  paperId: string;
  version: number;
}

export interface FullTextOkDTO {
  status: 'ok';
  /** Normalized full text (references/author info stripped — BR-SF-12). */
  text: string;
}

/** OA license not permitted → viewer not opened; arXiv link-out instead (BR-SF-11). */
export interface FullTextLicenseDTO {
  status: 'license_unavailable';
}

export interface FullTextSourceUnavailableDTO {
  status: 'source_unavailable';
}

export type FullTextResponseDTO =
  | FullTextOkDTO
  | FullTextLicenseDTO
  | FullTextSourceUnavailableDTO;
