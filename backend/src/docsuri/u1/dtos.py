"""U1 DTO — component-model §3.7 'SearchResult' 스키마를 코드로 동결.

SearchResult는 U3·U4와의 *유일한 약속*이라 필드를 임의 추가·변경하지 않는다
(U1 §8). DISC-04의 한→영 매핑 1줄은 UI 표시 전용이므로 SearchResult가 아니라
API 엔벨로프(SearchResponse.query_mapping)에 싣는다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..u0.ports import Lang, PaperHit, SearchFilters

DifficultyLabel = Literal["입문", "중급", "고급"]
SortKey = Literal["similarity", "citations", "recency"]


class Difficulty(BaseModel):
    """DifficultyEstimator 결과 — A7 휴리스틱 (점수 + 라벨)."""

    score: float  # 0.0(쉬움) ~ 1.0(어려움)
    label: DifficultyLabel


class SearchResultPaper(BaseModel):
    """SearchResult.papers[i] — PaperHit 6메타 + 난이도 라벨 (NFR-UX-03 데스크톱 6메타)."""

    id: str
    title: str
    authors: list[str]
    year: int
    citations: int
    similarity: float
    difficulty: DifficultyLabel

    @classmethod
    def from_hit(cls, hit: PaperHit, difficulty: DifficultyLabel) -> "SearchResultPaper":
        return cls(
            id=hit.id,
            title=hit.title,
            authors=hit.authors,
            year=hit.year,
            citations=hit.citations,
            similarity=hit.similarity,
            difficulty=difficulty,
        )


class ExpandedTerm(BaseModel):
    """KeywordExpander 결과 1건 — US-DISC-03 체크/해제 칩."""

    term: str
    checked: bool = False


class SearchResult(BaseModel):
    """U1의 유일한 약속 (component-model §3.7) — 스키마 동결."""

    query: str
    expanded_terms: list[ExpandedTerm] = Field(default_factory=list)
    papers: list[SearchResultPaper] = Field(default_factory=list)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    lang: Lang = "en"


class QueryMapping(BaseModel):
    """US-DISC-04 한→영 매핑 1줄 표시 — UI 표시 전용(SearchResult 밖)."""

    en_keywords: list[str]
    explanation: str


class SearchResponse(BaseModel):
    """API 엔벨로프 + 캐시 값 — SearchResult(계약) + UI 보조(query_mapping)."""

    result: SearchResult
    query_mapping: QueryMapping | None = None
