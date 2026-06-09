"""Async CrossRef REST API client.

Queries the public CrossRef API at https://api.crossref.org/works and parses
the returned JSON into raw dataclasses. Supports both keyword search and
direct DOI lookup. Pure transport layer — no domain mapping happens here.

References:
- CrossRef REST API: https://api.crossref.org/swagger-ui/index.html
- Polite pool: include mailto in User-Agent for 50 req/s allowance.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.crosscutting.ratelimit.backoff import RateLimitedRetry, TokenBucket
from app.crosscutting.verifier.port import verify_url

logger = logging.getLogger(__name__)

# Polite pool allows 50 req/s; conservative 5 req/s default without mailto.
_CROSSREF_BUCKET = TokenBucket(rate_per_sec=5.0, capacity=10)

_SELECT_FIELDS = "DOI,title,author,abstract,published,container-title,URL"


@dataclass
class CrossRefEntry:
    """Raw record parsed from one CrossRef work item."""

    doi: str
    title: str
    abstract: str | None
    authors: list[str]
    year: int | None
    venue: str | None   # container-title (journal name)
    url: str | None


class CrossRefClient:
    """Thin async wrapper around the CrossRef Works REST API.

    Uses an injected `httpx.AsyncClient` so tests can hand in a mocked
    transport. Caller owns the client's lifetime (e.g. FastAPI lifespan).
    """

    BASE_URL = "https://api.crossref.org"
    TIMEOUT = 5.0

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        bucket: TokenBucket = _CROSSREF_BUCKET,
        mailto: str = "",
    ) -> None:
        headers = {"User-Agent": f"DocSuri/1.0 (mailto:{mailto})"} if mailto else {}
        self._client = client or httpx.AsyncClient(timeout=self.TIMEOUT, headers=headers)
        self._owns_client = client is None
        self._bucket = bucket

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @RateLimitedRetry(max_attempts=3)
    async def _get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fetch JSON from CrossRef REST API.

        Time: O(N) JSON parse where N=rows.
        Rate limit: 5 req/s default; 50 req/s with polite-pool mailto header.
        Edge: SSRF check on caller-supplied `url` raises SSRFViolation before network call.
        """
        verify_url(url)
        await self._bucket.acquire()
        resp = await self._client.get(url, params=params or {})
        resp.raise_for_status()
        return resp.json()

    async def search(self, query: str, *, limit: int = 10) -> list[CrossRefEntry]:
        """Keyword search against CrossRef works.

        Time: O(N) where N=rows (JSON parse).
        Rate limit: 5 req/s default; 1000 rows max per request.
        Edge: empty `items` array → returns [].
        """
        params: dict[str, Any] = {
            "query": query,
            "rows": max(1, min(limit, 1000)),
            "select": _SELECT_FIELDS,
        }
        logger.info("crossref.search query=%r limit=%d", query, limit)
        data = await self._get(f"{self.BASE_URL}/works", params)
        return _parse_results(data)

    async def lookup_doi(self, doi: str) -> CrossRefEntry | None:
        """Direct DOI lookup. Returns None when the DOI is not found (404)."""
        logger.info("crossref.lookup_doi doi=%r", doi)
        try:
            data = await self._get(f"{self.BASE_URL}/works/{doi}")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        return _parse_item(data.get("message", {}))

    async def healthcheck(self) -> bool:
        """Cheap reachability probe (1-result query)."""
        try:
            await self.search("neural network", limit=1)
        except Exception:  # noqa: BLE001
            logger.warning("crossref healthcheck failed", exc_info=True)
            return False
        return True


def _parse_results(data: dict[str, Any]) -> list[CrossRefEntry]:
    items = data.get("message", {}).get("items", [])
    return [_parse_item(item) for item in items]


def _parse_item(item: dict[str, Any]) -> CrossRefEntry:
    titles = item.get("title") or []
    title = titles[0] if titles else ""

    author_list = item.get("author") or []
    authors = [
        " ".join(filter(None, [a.get("given", ""), a.get("family", "")]))
        for a in author_list
        if a.get("family") or a.get("given")
    ]

    published = item.get("published") or {}
    date_parts = (published.get("date-parts") or [[]])[0]
    year: int | None = date_parts[0] if date_parts else None

    containers = item.get("container-title") or []
    venue = containers[0] if containers else None

    return CrossRefEntry(
        doi=item.get("DOI", ""),
        title=title,
        abstract=item.get("abstract") or None,
        authors=authors,
        year=year,
        venue=venue,
        url=item.get("URL"),
    )
