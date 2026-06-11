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
