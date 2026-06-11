"""U4 HTTP 표면 — FastAPI APIRouter (u1/api.py 패턴).

POST /api/citations 가 엔벨로프 { view: CitationView(동결, §6.6),
top_influence: Top-3 }를 반환한다 — UI 보조 필드를 동결 DTO 밖에 두는
방식은 U1 SearchResponse(query_mapping) 전례를 따른다.

중심 논문 메타는 호출자(U1 SearchResult 카드)가 본문으로 전달한다 —
U4 입력 계약(`SearchResult.papers[i].id`, U4 §3)의 HTTP 구현.
렌더 분기는 서버의 FormFactorRouter가 결정하고 UI는 소비만 한다
(NFR-MOBILE-05 강제를 한 곳에 모음).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..u0.adapters import U0Ports
from ..u0.ports import PaperHit, Persona
from .service import CitationFetcher, FormFactorRouter, TopInfluenceSelector, build_view
from .views import CitationView


class CitationRequestPaper(BaseModel):
    """중심 논문 메타 — U1 SearchResultPaper의 부분집합 (difficulty는 U1 전용)."""

    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=500)
    authors: list[str] = Field(default_factory=list, max_length=20)
    year: int = 0
    citations: int = 0
    similarity: float = 0.0


class CitationRequest(BaseModel):
    paper: CitationRequestPaper
    viewport_width: int = Field(default=1280, ge=240, le=10_000)
    persona: Persona | None = None  # 미지정 시 서버 세션 기본값


class CitationResponse(BaseModel):
    view: CitationView
    top_influence: list[PaperHit]  # TRACE-02 — 학부 모드 카드 3장


def build_router(u0: U0Ports) -> APIRouter:
    fetcher = CitationFetcher(
        citation=u0.citation, cache=u0.cache, telemetry=u0.telemetry
    )
    form_factor = FormFactorRouter()
    top_influence = TopInfluenceSelector()
    router = APIRouter()

    @router.post("/api/citations", response_model=CitationResponse)
    def citations(req: CitationRequest) -> CitationResponse:
        persona = req.persona or u0.session.session().persona_mode
        one_hop = fetcher.fetch(req.paper.id)
        render = form_factor.route(req.viewport_width, persona)
        center = PaperHit(**req.paper.model_dump())
        return CitationResponse(
            view=build_view(center, one_hop, render),
            top_influence=top_influence.top3(one_hop.incoming),
        )

    return router
