"""Multi-DB search router (AGENTS.md §3.2 #01a, Sprint-Backlog-Search row 1).

`MultiDBRouter` is the abstraction every downstream feature depends on
("Router interface + arXiv adapter integration tests" DoD). Sprint 1 ships
exactly one adapter — `ArxivAdapter`. Sprint 2 plugs in Semantic Scholar /
OpenAlex / Crossref / PubMed via the same `SearchAdapter` Protocol.

Boundary checklist (AGENTS.md §5.2):
- ALLOWED imports: app.infra.http, app.crosscutting.ratelimit, app.container,
  app.domain.papers.models, app.domain.papers.normalizer.
- FORBIDDEN: app.domain.summarization, app.domain.translation, any other
  domain module.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Protocol

from app.domain.papers.models import PaperSummary
from app.domain.papers.normalizer import NormalizedQuery, normalize
from app.infra.http.arxiv import ArxivClient, ArxivEntry

logger = logging.getLogger(__name__)


class SearchAdapter(Protocol):
    """One adapter per external academic DB."""

    source: str

    async def search(self, nq: NormalizedQuery, *, limit: int) -> list[PaperSummary]:
        ...

    async def healthcheck(self) -> bool:
        ...


class ArxivAdapter:
    """Wraps `ArxivClient`; maps raw Atom entries → `PaperSummary` rows."""

    source = "arxiv"

    def __init__(self, client: ArxivClient | None = None) -> None:
        self._client = client or ArxivClient()

    async def search(self, nq: NormalizedQuery, *, limit: int) -> list[PaperSummary]:
        query = nq.for_arxiv()
        entries = await self._client.search(query, limit=limit)
        return [_to_summary(e) for e in entries]

    async def healthcheck(self) -> bool:
        return await self._client.healthcheck()

    async def aclose(self) -> None:
        await self._client.aclose()


def _to_summary(e: ArxivEntry) -> PaperSummary:
    return PaperSummary(
        id=e.arxiv_id or e.abs_url or "unknown",
        source="arxiv",
        title=e.title,
        authors=e.authors,
        abstract=e.summary,
        year=e.published_year,
        venue="arXiv",
        pdf_url=e.pdf_url,
        arxiv_url=e.abs_url,
    )


class MultiDBRouter:
    """Fan-out to every configured adapter and concatenate results.

    Sprint 1: a single adapter, so this is effectively `adapter.search()`.
    Sprint 2 adds dedupe + rerank (separate row in the backlog).
    """

    def __init__(self, adapters: list[SearchAdapter]) -> None:
        if not adapters:
            raise ValueError("MultiDBRouter requires at least one adapter")
        self._adapters = adapters

    @classmethod
    def default(cls) -> MultiDBRouter:
        """Sprint 1 default — arXiv only."""
        return cls([ArxivAdapter()])

    async def search(
        self, query: str, *, limit: int = 10, expand: bool = False
    ) -> tuple[list[PaperSummary], NormalizedQuery]:
        nq = await normalize(query, expand=expand)
        logger.info(
            "router.search adapters=%s expand=%s fields=%s",
            [a.source for a in self._adapters],
            expand,
            nq.fields,
        )
        results = await asyncio.gather(
            *(a.search(nq, limit=limit) for a in self._adapters),
            return_exceptions=True,
        )
        rows: list[PaperSummary] = []
        for adapter, res in zip(self._adapters, results, strict=True):
            if isinstance(res, BaseException):
                logger.warning("adapter %s failed: %s", adapter.source, res)
                continue
            rows.extend(res)
        # Sprint 2 will add dedupe + rerank here.
        return rows[:limit], nq

    async def healthcheck(self) -> dict[str, bool]:
        results = await asyncio.gather(
            *(a.healthcheck() for a in self._adapters), return_exceptions=True
        )
        return {
            a.source: (r is True)
            for a, r in zip(self._adapters, results, strict=True)
        }


# Module-level singleton so route handlers + tests share one HTTP client pool.
_router: MultiDBRouter | None = None


def get_router() -> MultiDBRouter:
    global _router
    if _router is None:
        _router = MultiDBRouter.default()
    return _router


def set_router(router: MultiDBRouter | None) -> None:
    """Test seam: inject a fake router (pass `None` to reset)."""
    global _router
    _router = router
