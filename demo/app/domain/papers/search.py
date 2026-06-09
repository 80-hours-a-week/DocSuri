"""Multi-DB search router (AGENTS.md §3.2 #01a, Sprint-Backlog-Search row 1).

`MultiDBRouter` is the abstraction every downstream feature depends on
("Router interface + arXiv adapter integration tests" DoD). Ships with five
adapters — arXiv, Semantic Scholar, OpenAlex, CrossRef, PubMed — merged via
Reciprocal Rank Fusion (k=60) with DOI / title+year deduplication.

Boundary checklist (AGENTS.md §5.2):
- ALLOWED imports: app.infra.http, app.crosscutting.ratelimit, app.container,
  app.domain.papers.models, app.domain.papers.normalizer.
- FORBIDDEN: app.domain.summarization, app.domain.translation, any other
  domain module.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from collections import defaultdict
from typing import TYPE_CHECKING, Protocol

import app.container as _container
from fastapi import BackgroundTasks

from app.crosscutting.ratelimit.circuit_breaker import CircuitBreaker
from app.domain.papers.models import PaperSummary
from app.domain.papers.normalizer import NormalizedQuery, normalize

if TYPE_CHECKING:
    from app.infra.http.arxiv import ArxivClient, ArxivEntry
    from app.infra.http.crossref import CrossRefClient, CrossRefEntry
    from app.infra.http.openalex import OpenAlexClient, OpenAlexEntry
    from app.infra.http.pubmed import PubMedClient, PubMedEntry
    from app.infra.http.semantic_scholar import S2Entry, SemanticScholarClient
    from app.infra.storage.pgvector import VectorSearchResult

logger = logging.getLogger(__name__)

_RRF_K = 60
_SEARCH_CACHE_TTL = 3600  # 1h


def _search_cache_key(canonical: str) -> str:
    return f"search:{hashlib.sha256(canonical.encode()).hexdigest()}"


def _vec_to_summary(r: VectorSearchResult) -> PaperSummary:
    is_doi = r.paper_id.startswith("10.")
    return PaperSummary(
        id=r.paper_id,
        source="crossref" if is_doi else "arxiv",
        title=r.title,
        abstract=r.abstract,
        doi=r.paper_id if is_doi else None,
    )


async def _try_pgvector_search(nq: NormalizedQuery, limit: int) -> list[PaperSummary]:
    """Best-effort pgvector semantic search; returns [] on any failure."""
    try:
        result = await _container.embedding().embed(nq.canonical)
        vec_results = await _container.pgvector().search(result.vector, limit=limit)
        return [_vec_to_summary(r) for r in vec_results]
    except Exception:
        logger.debug("pgvector.search skipped", exc_info=True)
        return []


class AllAdaptersFailedError(Exception):
    """Raised when every configured adapter fails (e.g. all CBs open).

    Callers should surface this as HTTP 503 — there are no sources to serve
    results from, so an empty 200 would silently mislead clients.
    """


class SearchAdapter(Protocol):
    """One adapter per external academic DB."""

    source: str

    async def search(self, nq: NormalizedQuery, *, limit: int) -> list[PaperSummary]:
        ...

    async def healthcheck(self) -> bool:
        ...


# ---------------------------------------------------------------------------
# arXiv
# ---------------------------------------------------------------------------

class ArxivAdapter:
    """Wraps `ArxivClient`; maps raw Atom entries → `PaperSummary` rows."""

    source = "arxiv"

    def __init__(
        self,
        client: ArxivClient | None = None,
        *,
        cb: CircuitBreaker | None = None,
    ) -> None:
        self._client = client if client is not None else _container.arxiv_client()
        self._cb = cb or CircuitBreaker()

    async def search(self, nq: NormalizedQuery, *, limit: int) -> list[PaperSummary]:
        async with self._cb:
            entries = await self._client.search(nq.for_arxiv(), limit=limit)
        return [_arxiv_to_summary(e) for e in entries]

    async def healthcheck(self) -> bool:
        return await self._client.healthcheck()

    async def aclose(self) -> None:
        await self._client.aclose()


def _arxiv_to_summary(e: ArxivEntry) -> PaperSummary:
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
        arxiv_id=e.arxiv_id or None,
    )


# ---------------------------------------------------------------------------
# Semantic Scholar
# ---------------------------------------------------------------------------

class SemanticScholarAdapter:
    """Wraps `SemanticScholarClient`; maps S2 entries → `PaperSummary` rows."""

    source = "s2"

    def __init__(
        self,
        client: SemanticScholarClient | None = None,
        *,
        cb: CircuitBreaker | None = None,
    ) -> None:
        self._client = client if client is not None else _container.s2_client()
        self._cb = cb or CircuitBreaker()

    async def search(self, nq: NormalizedQuery, *, limit: int) -> list[PaperSummary]:
        async with self._cb:
            entries = await self._client.search(nq.for_semantic_scholar(), limit=limit)
        return [_s2_to_summary(e) for e in entries]

    async def healthcheck(self) -> bool:
        return await self._client.healthcheck()

    async def aclose(self) -> None:
        await self._client.aclose()


def _s2_to_summary(e: S2Entry) -> PaperSummary:
    return PaperSummary(
        id=e.doi or e.paper_id,
        source="s2",
        title=e.title,
        authors=e.authors,
        abstract=e.abstract or "",
        year=e.year,
        venue=e.venue,
        pdf_url=e.pdf_url,
        doi=e.doi or None,
    )


# ---------------------------------------------------------------------------
# OpenAlex
# ---------------------------------------------------------------------------

class OpenAlexAdapter:
    """Wraps `OpenAlexClient`; maps OpenAlex works → `PaperSummary` rows."""

    source = "openalex"

    def __init__(
        self,
        client: OpenAlexClient | None = None,
        *,
        cb: CircuitBreaker | None = None,
    ) -> None:
        self._client = client if client is not None else _container.openalex_client()
        self._cb = cb or CircuitBreaker()

    async def search(self, nq: NormalizedQuery, *, limit: int) -> list[PaperSummary]:
        async with self._cb:
            entries = await self._client.search(nq.for_openalex(), limit=limit)
        return [_openalex_to_summary(e) for e in entries]

    async def healthcheck(self) -> bool:
        return await self._client.healthcheck()

    async def aclose(self) -> None:
        await self._client.aclose()


def _openalex_to_summary(e: OpenAlexEntry) -> PaperSummary:
    return PaperSummary(
        id=e.doi or e.work_id,
        source="openalex",
        title=e.title,
        authors=e.authors,
        abstract=e.abstract or "",
        year=e.year,
        venue=e.venue,
        pdf_url=e.pdf_url,
        doi=e.doi or None,
    )


# ---------------------------------------------------------------------------
# CrossRef
# ---------------------------------------------------------------------------

class CrossRefAdapter:
    """Wraps `CrossRefClient`; maps CrossRef items → `PaperSummary` rows."""

    source = "crossref"

    def __init__(
        self,
        client: CrossRefClient | None = None,
        *,
        cb: CircuitBreaker | None = None,
    ) -> None:
        self._client = client if client is not None else _container.crossref_client()
        self._cb = cb or CircuitBreaker()

    async def search(self, nq: NormalizedQuery, *, limit: int) -> list[PaperSummary]:
        async with self._cb:
            entries = await self._client.search(nq.for_crossref(), limit=limit)
        return [_crossref_to_summary(e) for e in entries]

    async def healthcheck(self) -> bool:
        return await self._client.healthcheck()

    async def aclose(self) -> None:
        await self._client.aclose()


def _crossref_to_summary(e: CrossRefEntry) -> PaperSummary:
    return PaperSummary(
        id=e.doi,
        source="crossref",
        title=e.title,
        authors=e.authors,
        abstract=e.abstract or "",
        year=e.year,
        venue=e.venue,
        doi=e.doi or None,
    )


# ---------------------------------------------------------------------------
# PubMed
# ---------------------------------------------------------------------------

class PubMedAdapter:
    """Wraps `PubMedClient`; maps PubMed articles → `PaperSummary` rows."""

    source = "pubmed"

    def __init__(
        self,
        client: PubMedClient | None = None,
        *,
        cb: CircuitBreaker | None = None,
    ) -> None:
        self._client = client if client is not None else _container.pubmed_client()
        self._cb = cb or CircuitBreaker()

    async def search(self, nq: NormalizedQuery, *, limit: int) -> list[PaperSummary]:
        async with self._cb:
            entries = await self._client.search(nq.for_pubmed(), limit=limit)
        return [_pubmed_to_summary(e) for e in entries]

    async def healthcheck(self) -> bool:
        return await self._client.healthcheck()

    async def aclose(self) -> None:
        await self._client.aclose()


def _pubmed_to_summary(e: PubMedEntry) -> PaperSummary:
    return PaperSummary(
        id=e.pmid,
        source="pubmed",
        title=e.title,
        authors=e.authors,
        abstract=e.abstract or "",
        year=e.year,
        venue=e.journal,
    )


# ---------------------------------------------------------------------------
# Dedup + RRF merge
# ---------------------------------------------------------------------------

def _title_hash(title: str, year: int | None) -> str:
    norm = re.sub(r"\s+", " ", title.lower().strip())
    return hashlib.sha256(f"{norm}|{year}".encode()).hexdigest()


def dedupe(papers: list[PaperSummary]) -> list[PaperSummary]:
    """DOI → arxivID → title-hash 3단 fallback 중복 제거.

    Time: O(N), Space: O(N)
    Edge: DOI/arxivID 없는 논문 → title+year 해시로 fallback.
    Edge: 빈 title → title-hash만 사용, 연도 무관.
    """
    seen: set[str] = set()
    result: list[PaperSummary] = []
    for p in papers:
        key = p.doi or p.arxiv_id or _title_hash(p.title, p.year)
        if key in seen:
            continue
        seen.add(key)
        result.append(p)
    return result


def rrf_merge(
    ranked_lists: list[list[PaperSummary]],
    k: int = _RRF_K,
) -> list[PaperSummary]:
    """Reciprocal Rank Fusion 점수 병합.

    Time: O(N*M) where N=소스 수, M=소스당 결과 수
    Space: O(N*M)
    Edge: ranked_lists 빈 리스트(전체 CB Open) → 빈 결과 반환.
    k=60: 변경 금지. 상위 결과 간 점수 차이 완화 표준값.
    """
    scores: dict[str, float] = defaultdict(float)
    papers: dict[str, PaperSummary] = {}
    for ranked in ranked_lists:
        for rank, paper in enumerate(ranked, start=1):
            key = paper.doi or paper.arxiv_id or paper.id
            scores[key] += 1.0 / (k + rank)
            papers[key] = paper
    return sorted(
        papers.values(),
        key=lambda p: scores[p.doi or p.arxiv_id or p.id],
        reverse=True,
    )


# ---------------------------------------------------------------------------
# Background tasks — embedding (idempotent, non-blocking)
# ---------------------------------------------------------------------------

async def _bg_embed_and_store(paper: PaperSummary) -> None:
    """Generate and store an embedding for `paper`.

    Idempotent: calls `has_paper()` before embedding so a re-run after a
    partial failure never produces a duplicate row or a wasted API call.
    Failure is logged and re-raised so that monitoring/tracing systems
    (OpenTelemetry, Langfuse) can detect and alert on persistent failures.
    FastAPI BackgroundTasks catches the re-raised exception — the HTTP
    response is already sent at that point, so the caller is unaffected.
    """
    try:
        pg = _container.pgvector()
        if await pg.has_paper(paper.id):
            logger.debug("bg.embed.skip paper_id=%s already_indexed=True", paper.id)
            return
        embedder = _container.embedding()
        text = f"{paper.title}\n\n{paper.abstract}".strip()
        result = await embedder.embed(text)
        await pg.upsert_paper(
            paper_id=paper.id,
            title=paper.title,
            abstract=paper.abstract,
            year=paper.year,
            vector=result.vector,
            doi=paper.doi,
        )
        logger.info("bg.embed.stored paper_id=%s", paper.id)
    except Exception:
        logger.exception("bg.embed.error", extra={"paper_id": paper.id})
        raise


async def _register_bg_tasks(
    papers: list[PaperSummary],
    bg: BackgroundTasks,
) -> None:
    """Batch-check pgvector and register tasks only for papers not yet indexed.

    Falls back to scheduling all papers when pgvector is unreachable —
    the bg tasks themselves are idempotent, so over-scheduling is safe.
    """
    try:
        pg = _container.pgvector()
        exists_flags: list[bool | BaseException] = list(
            await asyncio.gather(
                *(pg.has_paper(p.id) for p in papers),
                return_exceptions=True,
            )
        )
    except Exception:  # noqa: BLE001 — pgvector not configured / unreachable
        logger.debug(
            "bg.schedule: pgvector unavailable, scheduling all %d papers", len(papers)
        )
        exists_flags = [False] * len(papers)

    for paper, exists in zip(papers, exists_flags, strict=True):
        if isinstance(exists, BaseException) or not exists:
            bg.add_task(_bg_embed_and_store, paper)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class MultiDBRouter:
    """Fan-out to every configured adapter, deduplicate, then RRF-rerank."""

    def __init__(self, adapters: list[SearchAdapter]) -> None:
        if not adapters:
            raise ValueError("MultiDBRouter requires at least one adapter")
        self._adapters = adapters

    @classmethod
    def default(cls) -> MultiDBRouter:
        """All 5 academic DB adapters, each with an independent Circuit Breaker."""
        return cls([
            ArxivAdapter(client=_container.arxiv_client(), cb=_container.arxiv_cb()),
            SemanticScholarAdapter(client=_container.s2_client(), cb=_container.semantic_cb()),
            OpenAlexAdapter(client=_container.openalex_client(), cb=_container.openalex_cb()),
            CrossRefAdapter(client=_container.crossref_client(), cb=_container.crossref_cb()),
            PubMedAdapter(client=_container.pubmed_client(), cb=_container.pubmed_cb()),
        ])

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
        expand: bool = False,
        background_tasks: BackgroundTasks | None = None,
    ) -> tuple[list[PaperSummary], NormalizedQuery]:
        # Step 1: normalize
        nq = await normalize(query, expand=expand)

        # Step 2: Redis cache check — hit 시 즉시 반환
        cache = _container.cache()
        cache_key = _search_cache_key(nq.canonical)
        cached = await cache.get(cache_key)
        if cached:
            logger.debug("router.search cache_hit key=%s", cache_key)
            papers = [PaperSummary.model_validate(d) for d in json.loads(cached)]
            if background_tasks is not None and papers:
                await _register_bg_tasks(papers, background_tasks)
            return papers, nq

        logger.info(
            "router.search adapters=%s expand=%s fields=%s",
            [a.source for a in self._adapters],
            expand,
            nq.fields,
        )

        # Steps 3+4: 어댑터 팬아웃 + pgvector 병렬 수행
        all_results = await asyncio.gather(
            *(a.search(nq, limit=limit) for a in self._adapters),
            _try_pgvector_search(nq, limit),
            return_exceptions=True,
        )
        adapter_results = all_results[:-1]
        vec_result = all_results[-1]

        # Step 5: 어댑터 결과 분류
        ranked_lists: list[list[PaperSummary]] = []
        failures: list[BaseException] = []
        for adapter, res in zip(self._adapters, adapter_results, strict=True):
            if isinstance(res, BaseException):
                logger.warning("adapter %s failed: %s", adapter.source, res)
                failures.append(res)
                continue
            ranked_lists.append(res)

        if not isinstance(vec_result, BaseException) and vec_result:
            ranked_lists.append(vec_result)

        if not ranked_lists and failures:
            raise AllAdaptersFailedError(
                f"all {len(failures)} adapter(s) failed — sources unavailable"
            )

        # Step 6: dedupe + RRF 병합
        merged = dedupe(rrf_merge(ranked_lists))[:limit]

        # Step 7: Redis 캐시 저장
        await cache.set(
            cache_key,
            json.dumps([p.model_dump() for p in merged]),
            ex=_SEARCH_CACHE_TTL,
        )

        if background_tasks is not None and merged:
            await _register_bg_tasks(merged, background_tasks)

        return merged, nq

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
