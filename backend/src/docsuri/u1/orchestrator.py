"""SearchOrchestrator — component-model §3.1 · US-DISC-01 (시퀀스 §7.1).

검색 1건의 전체 흐름 조율:
  캐시 → (한국어면) 매핑 → 임베딩 → 검색(k=20, 필터) → 난이도 부착 → 정렬 →
  SearchResult 조립 → 캐시 set(24h) → Telemetry.record(op=search).

U0 포트만 호출한다. 캐시 값은 SearchResponse(SearchResult + query_mapping) 1덩어리로,
캐시 적중 시 매핑 재계산 없이 그대로 돌려준다.
"""

from __future__ import annotations

import time

from ..u0.adapters import U0Ports
from ..u0.ports import SearchFilters, TelemetryEvent
from .difficulty import DifficultyEstimator
from .dtos import SearchResponse, SearchResult, SearchResultPaper, SortKey
from .filter_sort import sort_papers
from .keyword_expander import KeywordExpander
from .query_mapper import KoEnQueryMapper
from .safety import MAX_SELECTED_TERMS, normalize_query, sanitize_query

TOP_K = 20
CACHE_TTL_S = 24 * 3600  # NFR-DATA-03 검색 24h


class SearchOrchestrator:
    def __init__(
        self,
        u0: U0Ports,
        mapper: KoEnQueryMapper,
        expander: KeywordExpander,
        estimator: DifficultyEstimator,
        clock=time.perf_counter,
    ) -> None:
        self._u0 = u0
        self._mapper = mapper
        self._expander = expander
        self._estimator = estimator
        self._clock = clock

    def search_for(
        self,
        query: str,
        filters: SearchFilters | None = None,
        sort_key: SortKey = "similarity",
        selected_terms: list[str] | None = None,
    ) -> SearchResponse:
        # #3 입력 검증·무해화 — 비용 발생 경로 진입 전 차단 (CLAUDE.md Part 2-A)
        query = sanitize_query(query)
        if not query:
            raise ValueError("검색어가 비어 있습니다.")
        filters = filters or SearchFilters()
        selected_terms = [
            t for t in (sanitize_query(s) for s in (selected_terms or [])) if t
        ][:MAX_SELECTED_TERMS]
        started = self._clock()

        cache_key = _cache_key(query, filters, sort_key, selected_terms)
        cached = self._u0.cache.get(cache_key)
        if cached is not None:
            self._record(op="search", started=started, cache_hit=True)
            return SearchResponse.model_validate_json(cached)

        lang = self._mapper.detect(query)
        mapping = self._mapper.map_explain(query) if lang == "ko" else None

        # 검색에 쓸 텍스트: 한국어면 매핑된 영문 키워드, + 선택된 확장 키워드
        search_terms = list(mapping.en_keywords) if mapping else [query]
        search_terms += selected_terms
        search_text = " ".join(search_terms).strip() or query

        vec = self._u0.embedding.embed(search_text, lang)
        hits = self._u0.embedding.search(vec, k=TOP_K, filters=filters)

        papers = [
            SearchResultPaper.from_hit(hit, self._estimator.estimate(hit).label)
            for hit in hits
        ]
        papers = sort_papers(papers, sort_key, lang)

        expanded_terms = self._expander.expand(query)
        for term in expanded_terms:
            if term.term in selected_terms:
                term.checked = True

        result = SearchResult(
            query=query,
            expanded_terms=expanded_terms,
            papers=papers,
            filters=filters,
            lang=lang,
        )
        response = SearchResponse(result=result, query_mapping=mapping)

        self._u0.cache.set(cache_key, response.model_dump_json().encode(), CACHE_TTL_S)
        self._record(op="search", started=started, cache_hit=False)
        return response

    def _record(self, op: str, started: float, cache_hit: bool) -> None:
        latency_ms = (self._clock() - started) * 1000
        self._u0.telemetry.record(
            TelemetryEvent(op=op, latency_ms=round(latency_ms, 3), cache_hit=cache_hit)
        )


def _cache_key(
    query: str, filters: SearchFilters, sort_key: str, selected_terms: list[str]
) -> str:
    # component-model §8.1: search:{query_norm}:{filters}
    query_norm = normalize_query(query)
    filter_sig = (
        f"y{filters.year_min or ''}-{filters.year_max or ''}"
        f":t{','.join(sorted(filters.field_tags))}"
    )
    terms_sig = ",".join(sorted(selected_terms))
    return f"search:{query_norm}:{filter_sig}:s{sort_key}:e{terms_sig}"
