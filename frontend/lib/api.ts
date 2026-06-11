// 클라이언트 → BFF(/api/search) 호출. 백엔드 연결/폴백은 BFF가 결정한다.

import type { SearchRequestBody, SearchResponse } from "./types";
import type { SearchState } from "./url-state";

export function stateToRequest(state: SearchState): SearchRequestBody {
  return {
    query: state.query,
    filters: state.filters,
    sort_key: state.sortKey,
    selected_terms: state.selectedTerms,
  };
}

export async function searchPapers(state: SearchState): Promise<SearchResponse> {
  const res = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(stateToRequest(state)),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`검색 요청 실패 (${res.status}) ${detail}`.trim());
  }
  return (await res.json()) as SearchResponse;
}
