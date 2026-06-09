"""Async OpenAlex API client.

Queries the public OpenAlex API at https://api.openalex.org/works and parses
the returned JSON into raw dataclasses. Pure transport layer — no domain
mapping happens here (that lives in `domain/papers/search.py`).

References:
- OpenAlex API: https://docs.openalex.org/api-entities/works
- Polite pool: include mailto in User-Agent for higher rate limits.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.crosscutting.ratelimit.backoff import RateLimitedRetry, TokenBucket
from app.crosscutting.verifier.port import verify_url

logger = logging.getLogger(__name__)

_OPENALEX_SELECT = ",".join([
    "id",
    "title",
    "abstract_inverted_index",
    "authorships",
    "publication_year",
    "primary_location",
    "doi",
    "open_access",
])

# OpenAlex polite pool supports up to 10 req/s with mailto User-Agent.
_OPENALEX_BUCKET = TokenBucket(rate_per_sec=10.0, capacity=10)


@dataclass
class OpenAlexEntry:
    """Raw record parsed from one OpenAlex Work."""

    work_id: str        # short numeric id e.g. "W2741809807"
    title: str
    abstract: str | None
    authors: list[str]
    year: int | None
    venue: str | None
    doi: str | None     # bare DOI e.g. "10.1145/1234567"
    pdf_url: str | None


class OpenAlexClient:
    """Thin async wrapper around the OpenAlex Works API.

    Uses an injected `httpx.AsyncClient` so tests can hand in a mocked
    transport. Caller owns the client's lifetime (e.g. FastAPI lifespan).
    """

    ENDPOINT = "https://api.openalex.org/works"
    TIMEOUT = 5.0

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        bucket: TokenBucket = _OPENALEX_BUCKET,
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
    async def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        """Fetch JSON from OpenAlex Works API.

        Time: O(N) JSON parse where N=per-page.
        Rate limit: 10 req/s with polite-pool mailto header; retried up to 3 times.
        Edge: SSRF check raises SSRFViolation before network call.
        """
        verify_url(self.ENDPOINT)
        await self._bucket.acquire()
        resp = await self._client.get(self.ENDPOINT, params=params)
        resp.raise_for_status()
        return resp.json()

    async def search(self, query: str, *, limit: int = 10) -> list[OpenAlexEntry]:
        """Full-text search against OpenAlex works.

        Time: O(N) where N=limit (JSON parse + abstract reconstruction).
        Rate limit: 10 req/s polite pool; 200 results max per request.
        Edge: `abstract_inverted_index` absent or empty → abstract=None.
        """
        params = {
            "search": query,
            "per-page": max(1, min(limit, 200)),
            "select": _OPENALEX_SELECT,
        }
        logger.info("openalex.search query=%r limit=%d", query, limit)
        data = await self._get(params)
        return _parse_results(data)

    async def healthcheck(self) -> bool:
        """Cheap reachability probe (1-result query)."""
        try:
            await self.search("machine learning", limit=1)
        except Exception:  # noqa: BLE001
            logger.warning("openalex healthcheck failed", exc_info=True)
            return False
        return True


def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Rebuild abstract from OpenAlex inverted word-position index."""
    if not inverted_index:
        return None
    pos_word: dict[int, str] = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            pos_word[pos] = word
    if not pos_word:
        return None
    return " ".join(pos_word[i] for i in sorted(pos_word))


def _parse_results(data: dict[str, Any]) -> list[OpenAlexEntry]:
    return [_parse_work(w) for w in data.get("results", [])]


def _parse_work(w: dict[str, Any]) -> OpenAlexEntry:
    raw_id = w.get("id") or ""
    work_id = raw_id.rsplit("/", 1)[-1] if raw_id else ""

    authors = [
        ship["author"]["display_name"]
        for ship in w.get("authorships", [])
        if ship.get("author", {}).get("display_name")
    ]

    primary_loc = w.get("primary_location") or {}
    source = primary_loc.get("source") or {}
    venue = source.get("display_name") or None

    open_access = w.get("open_access") or {}
    pdf_url = open_access.get("oa_url") or None

    raw_doi = w.get("doi") or None
    doi: str | None = None
    if raw_doi:
        doi = raw_doi.rsplit("doi.org/", 1)[-1] if "doi.org/" in raw_doi else raw_doi

    return OpenAlexEntry(
        work_id=work_id,
        title=w.get("title") or "",
        abstract=_reconstruct_abstract(w.get("abstract_inverted_index")),
        authors=authors,
        year=w.get("publication_year"),
        venue=venue,
        doi=doi,
        pdf_url=pdf_url,
    )
