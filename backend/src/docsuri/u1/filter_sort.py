"""FilterSortController — component-model §3.5 · US-DISC-02.

정렬·필터 상태의 단일 보유 + URL 직렬화 왕복. 필터 직렬화는 SessionPort에 위임하고
(U0 계약), sort_key는 U1 레벨에서 쿼리에 부가한다. 목록 정렬도 본 모듈의 순수 함수가
담당한다(SearchOrchestrator가 호출).

한국어 쿼리(US-DISC-04)는 난이도 점수 오름차순 가중으로 입문 적합 논문을 상위에 올린다 —
similarity 정렬 안에서 난이도 tier(입문<중급<고급)를 1차 키로 쓴다.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode

from ..u0.ports import Lang, SearchFilters, SessionPort
from .dtos import SearchResultPaper, SortKey

_DIFFICULTY_RANK = {"입문": 0, "중급": 1, "고급": 2}


class FilterSortController:
    def __init__(self, session: SessionPort) -> None:
        self._session = session

    def to_url(self, filters: SearchFilters, sort_key: SortKey) -> str:
        """필터(SessionPort 위임) + sort_key를 URL 쿼리로 직렬화 (새로고침 유지)."""
        filter_q = self._session.serialize_filters(filters)
        params = parse_qs(filter_q)
        flat = {k: v[0] for k, v in params.items()}
        flat["sort"] = sort_key
        return urlencode(flat)

    def from_url(self, url_query: str) -> tuple[SearchFilters, SortKey]:
        filters = self._session.restore_filters(url_query)
        parsed = parse_qs(url_query)
        sort_raw = parsed.get("sort", ["similarity"])[0]
        sort_key: SortKey = sort_raw if sort_raw in ("similarity", "citations", "recency") else "similarity"  # type: ignore[assignment]
        return filters, sort_key


def sort_papers(
    papers: list[SearchResultPaper], sort_key: SortKey, lang: Lang
) -> list[SearchResultPaper]:
    """정렬 적용 — DISC-02 명시 정렬 + DISC-04 한국어 입문 가중."""
    if sort_key == "citations":
        return sorted(papers, key=lambda p: p.citations, reverse=True)
    if sort_key == "recency":
        return sorted(papers, key=lambda p: p.year, reverse=True)
    # similarity (기본): 검색 순서가 이미 유사도 내림차순.
    if lang == "ko":
        # 입문 적합 상위: 난이도 tier 오름차순(1차) → 유사도 내림차순(2차)
        return sorted(
            papers,
            key=lambda p: (_DIFFICULTY_RANK[p.difficulty], -p.similarity),
        )
    return sorted(papers, key=lambda p: p.similarity, reverse=True)
