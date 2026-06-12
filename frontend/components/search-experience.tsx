"use client";

// U1 Discover 컨테이너 — 초기 상태·결과는 서버(page)가 props로 주입(SSR, 새로고침 복원).
// 이후 검색/정렬/필터/확장칩 변경 시: 상태 갱신 → URL replace(유지) → BFF 재검색.

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { BookOpenText, Network } from "lucide-react";

import { CitationFlow } from "@/components/citation-flow";
import { ComprehendFlow } from "@/components/comprehend-flow";
import { FilterSortBar } from "@/components/filter-sort-bar";
import { ExpandedTerms } from "@/components/expanded-terms";
import { QueryMappingNote } from "@/components/query-mapping";
import { ResultList } from "@/components/result-list";
import { SearchBar } from "@/components/search-bar";
import { Button } from "@/components/ui/button";
import { searchPapers } from "@/lib/api";
import type {
  ExpandedTerm,
  QueryMapping,
  SearchFilters,
  SearchResponse,
  SearchResultPaper,
  SortKey,
} from "@/lib/types";
import { type SearchState, stateToParams } from "@/lib/url-state";

interface SearchExperienceProps {
  initialState: SearchState;
  initialResponse: SearchResponse | null;
}

export function SearchExperience({ initialState, initialResponse }: SearchExperienceProps) {
  const router = useRouter();

  const [state, setState] = useState<SearchState>(initialState);
  const [papers, setPapers] = useState<SearchResultPaper[]>(initialResponse?.result.papers ?? []);
  const [terms, setTerms] = useState<ExpandedTerm[]>(initialResponse?.result.expanded_terms ?? []);
  const [mapping, setMapping] = useState<QueryMapping | null>(initialResponse?.query_mapping ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(initialResponse !== null);
  // U4 — "인용 흐름 보기" 대상 (TRACE-01 진입점)
  const [citationPaper, setCitationPaper] = useState<SearchResultPaper | null>(null);
  // U2 — "요약 보기" 대상 (COMP-01 진입점)
  const [summaryPaper, setSummaryPaper] = useState<SearchResultPaper | null>(null);

  const reqId = useRef(0);

  const run = useCallback(
    async (next: SearchState) => {
      setState(next);
      router.replace(`/?${stateToParams(next).toString()}`, { scroll: false });
      if (!next.query.trim()) return;

      const id = ++reqId.current;
      setLoading(true);
      setError(null);
      try {
        const resp = await searchPapers(next);
        if (id !== reqId.current) return; // 경쟁 상태 — 최신 응답만 반영
        setPapers(resp.result.papers);
        setTerms(resp.result.expanded_terms);
        setMapping(resp.query_mapping);
        setSearched(true);
      } catch (e) {
        if (id !== reqId.current) return;
        setError(e instanceof Error ? e.message : "검색 중 오류가 발생했습니다.");
        setPapers([]);
        setSearched(true);
      } finally {
        if (id === reqId.current) setLoading(false);
      }
    },
    [router],
  );

  const onSearch = (query: string) => void run({ ...state, query, selectedTerms: [] });
  const onFiltersChange = (filters: SearchFilters) => void run({ ...state, filters });
  const onSortChange = (sortKey: SortKey) => void run({ ...state, sortKey });
  const onToggleTerm = (term: string) => {
    const selectedTerms = state.selectedTerms.includes(term)
      ? state.selectedTerms.filter((t) => t !== term)
      : [...state.selectedTerms, term];
    void run({ ...state, selectedTerms });
  };

  return (
    <div className="space-y-5">
      <SearchBar initialQuery={state.query} onSearch={onSearch} />

      {searched && (
        <>
          <QueryMappingNote mapping={mapping} />
          <ExpandedTerms terms={terms} selected={state.selectedTerms} onToggle={onToggleTerm} />
          <FilterSortBar
            filters={state.filters}
            sortKey={state.sortKey}
            onFiltersChange={onFiltersChange}
            onSortChange={onSortChange}
          />
        </>
      )}

      {error && (
        <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      )}

      <ResultList
        papers={papers}
        loading={loading}
        searched={searched}
        renderFooter={(p) => (
          <div className="flex flex-col gap-2 md:flex-row">
            <Button
              variant="outline"
              size="sm"
              className="h-11 w-full md:w-auto"
              onClick={() => setSummaryPaper(p)}
            >
              <BookOpenText className="size-4" aria-hidden />
              요약 보기
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-11 w-full md:w-auto"
              onClick={() => setCitationPaper(p)}
            >
              <Network className="size-4" aria-hidden />
              인용 흐름 보기
            </Button>
          </div>
        )}
      />

      <ComprehendFlow paper={summaryPaper} onClose={() => setSummaryPaper(null)} />
      <CitationFlow paper={citationPaper} onClose={() => setCitationPaper(null)} />
    </div>
  );
}
