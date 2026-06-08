"""HTTP surface for #01a Search (Sprint 1 walking skeleton).

Thin handlers — all logic lives in `app.domain.papers.search` /
`app.domain.papers.normalizer`. Per AGENTS.md §5.2 the API layer is
allowed to depend on `domain/*` directly.

Endpoints:
- `POST /api/search`           — natural-language query → result rows
- `GET  /api/search/health`    — arXiv reachability probe
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.domain.papers.models import PaperSummary
from app.domain.papers.search import get_router

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=512)
    limit: int = Field(default=10, ge=1, le=50)
    expand: bool = False


class SearchResponse(BaseModel):
    results: list[PaperSummary]
    normalized: str  # the arXiv-syntax query actually fired
    expanded: bool
    count: int


class SearchHealth(BaseModel):
    status: str  # "ok" | "degraded"
    adapters: dict[str, bool]


@router.post("/search", response_model=SearchResponse)
async def post_search(req: SearchRequest) -> SearchResponse:
    rows, nq = await get_router().search(
        req.query, limit=req.limit, expand=req.expand
    )
    return SearchResponse(
        results=rows,
        normalized=nq.for_arxiv(),
        expanded=nq.expanded,
        count=len(rows),
    )


@router.get("/search/health", response_model=SearchHealth)
async def health() -> SearchHealth:
    adapters = await get_router().healthcheck()
    status = "ok" if all(adapters.values()) else "degraded"
    return SearchHealth(status=status, adapters=adapters)
