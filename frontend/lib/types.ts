// 백엔드 계약 미러 — 단일 진실: backend/src/docsuri/u1/dtos.py
// 필드를 임의로 추가/변경하지 않는다 (SearchResult는 U3·U4와의 약속).

export type SortKey = "similarity" | "citations" | "recency";
export type DifficultyLabel = "입문" | "중급" | "고급";
export type Lang = "ko" | "en";

export interface SearchFilters {
  year_min: number | null;
  year_max: number | null;
  field_tags: string[];
}

export interface ExpandedTerm {
  term: string;
  checked: boolean;
}

export interface SearchResultPaper {
  id: string;
  title: string;
  authors: string[];
  year: number;
  citations: number;
  similarity: number;
  difficulty: DifficultyLabel;
}

export interface SearchResult {
  query: string;
  expanded_terms: ExpandedTerm[];
  papers: SearchResultPaper[];
  filters: SearchFilters;
  lang: Lang;
}

export interface QueryMapping {
  en_keywords: string[];
  explanation: string;
}

export interface SearchResponse {
  result: SearchResult;
  query_mapping: QueryMapping | null;
}

// /api/search 요청 본문 (백엔드 SearchRequest와 동일)
export interface SearchRequestBody {
  query: string;
  filters: SearchFilters;
  sort_key: SortKey;
  selected_terms: string[];
}

export const EMPTY_FILTERS: SearchFilters = {
  year_min: null,
  year_max: null,
  field_tags: [],
};

// ── U4 Trace — 백엔드 계약 미러: backend/src/docsuri/u4/views.py (CitationView §6.6 동결)
//    + u4/api.py 엔벨로프. 필드를 임의로 추가/변경하지 않는다.

export type Persona = "pro" | "undergrad";
export type CitationRenderMode = "graph" | "list";

export interface CitationPaper {
  id: string;
  title: string;
  authors: string[];
  year: number;
  citations: number;
  similarity: number;
  field_tags: string[];
  abstract_len: number;
}

export interface CitationView {
  center: CitationPaper;
  outgoing: CitationPaper[];
  incoming: CitationPaper[];
  render: CitationRenderMode;
  max_nodes: number;
}

export interface CitationResponse {
  view: CitationView;
  top_influence: CitationPaper[]; // TRACE-02 — 피인용 가중 Top-3
}

// /api/citations 요청 본문 (백엔드 CitationRequest와 동일)
export interface CitationRequestBody {
  paper: {
    id: string;
    title: string;
    authors: string[];
    year: number;
    citations: number;
    similarity: number;
  };
  viewport_width: number;
  persona?: Persona;
}

// ── U2 Comprehend — 백엔드 계약 미러: backend/src/docsuri/u2/models.py(§3 동결)
//    + u2/api.py 엔벨로프. 필드를 임의로 추가/변경하지 않는다.

export type SectionKey = "question" | "method" | "result" | "limit";

export interface SummarySections {
  question: string;
  method: string;
  result: string;
  limit: string;
}

export interface VocabExplanation {
  term: string;
  ko: string;
  note: string;
}

export interface SummaryResult {
  paper_id: string;
  mode: Persona;
  sections: SummarySections;
  vocab_explanations: VocabExplanation[];
  cost: { tokens_in: number; tokens_out: number };
}

export interface ReadabilityReport {
  mode: Persona;
  passed: boolean;
  metrics: {
    sentence_count: number;
    average_eojeol_per_sentence: number;
    max_eojeol_per_sentence: number;
    difficult_token_count: number;
  };
  issues: string[];
}

export interface SummaryResponse {
  summary: SummaryResult;
  readability: ReadabilityReport | null;
  paper: { title: string; abstract: string }; // UI 보조 — COMP-04 원문 패널
}

export interface SummaryRequestBody {
  paper_id: string;
  mode: Persona;
}

export interface TranslationResult {
  source_excerpt: string;
  target_text: string;
  glossary_hits: VocabExplanation[];
}

export interface TranslationRequestBody {
  source_excerpt: string;
  input_mode: "desktop" | "mobile";
}
