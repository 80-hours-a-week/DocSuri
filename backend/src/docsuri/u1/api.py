"""U1 HTTP 표면 — FastAPI APIRouter (ADR-D1 Python+FastAPI).

POST /api/search 가 SearchResponse(SearchResult 계약 + UI 보조 매핑)를 반환한다.
정렬 변경·필터·확장 키워드 토글·재검색은 모두 파라미터를 바꾼 동일 엔드포인트
호출로 충족한다(US-DISC-01·02·03·04). UI 렌더(데스크톱6/모바일3)는 다음 라운드.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..u0.ports import SearchFilters
from .dtos import SearchResponse, SortKey
from .service import U1Services


class SearchRequest(BaseModel):
    query: str
    filters: SearchFilters = Field(default_factory=SearchFilters)
    sort_key: SortKey = "similarity"
    selected_terms: list[str] = Field(default_factory=list)


def build_router(services: U1Services) -> APIRouter:
    router = APIRouter()

    @router.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @router.post("/api/search", response_model=SearchResponse)
    def search(req: SearchRequest) -> SearchResponse:
        return services.orchestrator.search_for(
            query=req.query,
            filters=req.filters,
            sort_key=req.sort_key,
            selected_terms=req.selected_terms,
        )

    return router
