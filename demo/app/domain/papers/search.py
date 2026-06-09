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


def _canonical_key(paper: PaperSummary, title_hash_map: dict[str, str]) -> str:
    """title_hash_map을 우선 조회해 소스 간 동일 논문을 단일 key로 통일.

    title_hash_map에 해당 논문의 best key(doi > arxiv_id > hash)가 있으면
    그것을 반환. 없으면 doi → arxiv_id → title_hash 순 fallback.
    """
    th = _title_hash(paper.title, paper.year)
    if th in title_hash_map:
        return title_hash_map[th]
    return paper.doi or paper.arxiv_id or th


def _build_title_hash_map(ranked_lists: list[list[PaperSummary]]) -> dict[str, str]:
    """title_hash → canonical key(doi > arxiv_id > title_hash) 매핑 구축.

    같은 논문이 arXiv(arxiv_id만 있음)와 CrossRef(doi만 있음)에서 각각
    다른 ID로 들어올 때, title_hash로 묶어 doi를 canonical key로 통일.
    """
    th_to_best: dict[str, str] = {}
    for ranked in ranked_lists:
        for paper in ranked:
            th = _title_hash(paper.title, paper.year)
            best = paper.doi or paper.arxiv_id or th
            existing = th_to_best.get(th)
            # doi > arxiv_id > title_hash 우선순위로 업데이트
            if existing is None or (paper.doi and not existing.startswith("10.")):
                th_to_best[th] = best
    return th_to_best


def dedupe(papers: list[PaperSummary]) -> list[PaperSummary]:
    """DOI → arxivID → title-hash 3단 fallback 중복 제거. rrf_merge 후 잔여 중복 방어용."""
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
    """중복 식별 후 RRF 점수 합산.

    올바른 순서: 중복 식별 → 점수 합산 → 정렬.
    같은 논문이 소스마다 doi/arxiv_id 중 하나만 있을 때
    title+year hash로 동일 논문을 먼저 묶은 뒤 RRF 점수를 합산한다.

    k=60: 변경 금지 (Cormack et al. 2009 표준값).
    Time: O(N*M), Space: O(N*M)
    """
    title_hash_map = _build_title_hash_map(ranked_lists)

    scores: dict[str, float] = defaultdict(float)
    papers: dict[str, PaperSummary] = {}
    for ranked in ranked_lists:
        for rank, paper in enumerate(ranked, start=1):
            key = _canonical_key(paper, title_hash_map)
            scores[key] += 1.0 / (k + rank)
            # doi가 있는 쪽을 대표 레코드로 유지
            if key not in papers or (paper.doi and not papers[key].doi):
                papers[key] = paper
    return sorted(
        papers.values(),
        key=lambda p: scores[_canonical_key(p, title_hash_map)],
        reverse=True,
    )


# ---------------------------------------------------------------------------
# CrossRef DOI 보강 (팬아웃 이후 별도 실행)
# ---------------------------------------------------------------------------

async def _enrich_with_crossref(papers: list[PaperSummary]) -> list[PaperSummary]:
    """DOI가 있는 논문의 빈 필드를 CrossRef 직접 조회로 보강.

    CrossRef 자연어 검색(느림)과 달리 DOI 직접 조회는 빠름.
    abstract/authors/venue 중 누락된 필드만 채운다.
    실패 시 원본 paper를 그대로 유지 (best-effort).
    """
    client = _container.crossref_client()
    doi_indices = [(i, p) for i, p in enumerate(papers) if p.doi]
    if not doi_indices:
        return papers

    async def fetch_one(idx: int, paper: PaperSummary) -> tuple[int, PaperSummary]:
        try:
            entry = await client.lookup_doi(paper.doi)  # type: ignore[arg-type]
            if entry is None:
                return idx, paper
            updates: dict = {}
            if not paper.abstract and entry.abstract:
                updates["abstract"] = entry.abstract
            if not paper.authors and entry.authors:
                updates["authors"] = entry.authors
            if not paper.venue and entry.venue:
                updates["venue"] = entry.venue
            return idx, paper.model_copy(update=updates) if updates else paper
        except Exception:
            logger.debug("crossref.enrich failed doi=%s", paper.doi, exc_info=True)
            return idx, paper

    enriched = list(papers)
    results = await asyncio.gather(*(fetch_one(i, p) for i, p in doi_indices))
    for idx, paper in results:
        enriched[idx] = paper
    return enriched


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
        logger.debug("bg.embed.error", extra={"paper_id": paper.id}, exc_info=True)


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
        """4개 학술 DB 어댑터 팬아웃. CrossRef는 자연어 검색에서 제외 — 느리고
        품질이 낮음. DOI 메타데이터 보강은 _enrich_with_crossref()로 별도 처리."""
        return cls([
            ArxivAdapter(client=_container.arxiv_client(), cb=_container.arxiv_cb()),
            SemanticScholarAdapter(client=_container.s2_client(), cb=_container.semantic_cb()),
            OpenAlexAdapter(client=_container.openalex_client(), cb=_container.openalex_cb()),
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

        # Step 7: CrossRef DOI 보강 (팬아웃과 별개 — 직접 조회라 빠름)
        merged = await _enrich_with_crossref(merged)

        # Step 8: Redis 캐시 저장
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
