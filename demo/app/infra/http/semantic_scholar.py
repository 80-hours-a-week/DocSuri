"""Async Semantic Scholar Graph API client.

Queries the public S2 Graph API at https://api.semanticscholar.org/graph/v1/paper/search
and parses the returned JSON into raw dataclasses. Pure transport layer — no
domain mapping happens here (that lives in `domain/papers/search.py`).

References:
- S2 Graph API: https://api.semanticscholar.org/graph/v1
- Rate limit: 100 req / 5 min unauthenticated; 1 req/s conservative ceiling.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.crosscutting.ratelimit.backoff import RateLimitedRetry, TokenBucket
from app.crosscutting.verifier.port import verify_url

logger = logging.getLogger(__name__)

_S2_FIELDS = "paperId,title,abstract,authors,year,venue,openAccessPdf,externalIds"

# Unauthenticated limit ~0.33 req/s; 1.0 with small burst for retries.
_S2_BUCKET = TokenBucket(rate_per_sec=1.0, capacity=5)


@dataclass
class S2Entry:
    """Raw record parsed from one Semantic Scholar paper result."""

    paper_id: str
    title: str
    abstract: str | None
    authors: list[str]
    year: int | None
    venue: str | None
    pdf_url: str | None
    doi: str | None


class SemanticScholarClient:
    """Thin async wrapper around the Semantic Scholar Graph API.

    Uses an injected `httpx.AsyncClient` so tests can hand in a mocked
    transport. Caller owns the client's lifetime (e.g. FastAPI lifespan).
    """

    ENDPOINT = "https://api.semanticscholar.org/graph/v1/paper/search"
    TIMEOUT = 5.0

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        bucket: TokenBucket = _S2_BUCKET,
    ) -> None:
        self._client = client or httpx.AsyncClient(timeout=self.TIMEOUT)
        self._owns_client = client is None
        self._bucket = bucket

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @RateLimitedRetry(max_attempts=1)
    async def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        """Fetch JSON from S2 Graph API.

        Time: O(N) JSON parse where N=limit.
        Rate limit: 1 req/s unauthenticated (100 req/5 min); retried up to 3 times.
        Edge: SSRF check raises SSRFViolation before network call. 429 triggers retry.
        """
        verify_url(self.ENDPOINT)
        await self._bucket.acquire()
        resp = await self._client.get(self.ENDPOINT, params=params)
        resp.raise_for_status()
        return resp.json()

    async def search(self, query: str, *, limit: int = 10) -> list[S2Entry]:
        """Keyword search against S2 Graph API and return parsed entries.

        Time: O(N) where N=limit (JSON parse).
        Rate limit: 1 req/s ceiling; 100 results max per request.
        Edge: API returns `{"data": []}` → returns [].
        """
        params = {
            "query": query,
            "fields": _S2_FIELDS,
            "limit": max(1, min(limit, 100)),
        }
        logger.info("s2.search query=%r limit=%d", query, limit)
        data = await self._get(params)
        return _parse_results(data)

    async def healthcheck(self) -> bool:
        """Cheap reachability probe (1-result query)."""
        try:
            await self.search("deep learning", limit=1)
        except Exception:  # noqa: BLE001
            logger.warning("semantic_scholar healthcheck failed", exc_info=True)
            return False
        return True


def _parse_results(data: dict[str, Any]) -> list[S2Entry]:
    return [_parse_paper(p) for p in data.get("data", [])]


def _parse_paper(p: dict[str, Any]) -> S2Entry:
    authors = [a["name"] for a in p.get("authors", []) if a.get("name")]
    oa = p.get("openAccessPdf") or {}
    external_ids = p.get("externalIds") or {}
    return S2Entry(
        paper_id=p.get("paperId", ""),
        title=p.get("title") or "",
        abstract=p.get("abstract") or None,
        authors=authors,
        year=p.get("year"),
        venue=p.get("venue") or None,
        pdf_url=oa.get("url"),
        doi=external_ids.get("DOI"),
    )
