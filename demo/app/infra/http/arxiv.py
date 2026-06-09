"""Async arXiv API client.

Queries the public arXiv Atom feed at https://export.arxiv.org/api/query
and parses the returned XML into raw dicts. Pure transport layer — no
domain mapping happens here (that lives in `domain/papers/search.py`).

References:
- arXiv API user manual: https://info.arxiv.org/help/api/user-manual.html
- AGENTS.md §4.5 — rate-limited via `crosscutting/ratelimit`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from xml.etree import ElementTree as ET

import httpx

from app.crosscutting.ratelimit.backoff import RateLimitedRetry, TokenBucket
from app.crosscutting.verifier.port import verify_url

logger = logging.getLogger(__name__)

# Atom + arXiv namespaces (see arXiv API manual).
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}

# arXiv asks for ~1 req / 3s in their manual; AGENTS.md §4.5 sets a 3 req/s
# ceiling for PubMed. We expose a per-host quota the caller can configure.
_ARXIV_BUCKET = TokenBucket(rate_per_sec=3.0, capacity=3)


@dataclass
class ArxivEntry:
    """Raw record parsed from one Atom <entry>. Stable across arXiv field tweaks."""

    arxiv_id: str  # short id e.g. "2401.12345" or "cs.CL/0701001"
    title: str
    summary: str
    authors: list[str]
    published_year: int | None
    pdf_url: str | None
    abs_url: str | None
    primary_category: str | None


class ArxivClient:
    """Thin async wrapper around the arXiv Atom feed.

    Uses an injected `httpx.AsyncClient` so tests can hand in a mocked
    transport. Caller owns the client's lifetime (e.g. FastAPI lifespan).
    """

    ENDPOINT = "https://export.arxiv.org/api/query"
    TIMEOUT = 15.0

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        bucket: TokenBucket = _ARXIV_BUCKET,
    ) -> None:
        self._client = client or httpx.AsyncClient(timeout=self.TIMEOUT)
        self._owns_client = client is None
        self._bucket = bucket

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @RateLimitedRetry(max_attempts=3)
    async def _get(self, params: dict[str, Any]) -> str:
        """Fetch Atom XML from arXiv.

        Time: O(N) XML parse where N=max_results.
        Rate limit: 3 req/s via _ARXIV_BUCKET; retried up to 3 times on transient errors.
        Edge: SSRF check raises SSRFViolation before any network call.
        """
        verify_url(self.ENDPOINT)
        await self._bucket.acquire()
        resp = await self._client.get(self.ENDPOINT, params=params)
        resp.raise_for_status()
        return resp.text

    async def search(self, query: str, *, limit: int = 10) -> list[ArxivEntry]:
        """Run a `search_query` against arXiv and return parsed entries.

        Time: O(N) where N=max_results (XML parse).
        Rate limit: 3 req/s ceiling; 100 results max per request.
        Edge: empty feed → returns []. `query` passed as-is; callers may use arXiv syntax.
        """
        params = {
            "search_query": query,
            "start": 0,
            "max_results": max(1, min(limit, 100)),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        logger.info("arxiv.search query=%r limit=%d", query, limit)
        xml = await self._get(params)
        return _parse_feed(xml)

    async def healthcheck(self) -> bool:
        """Cheap reachability probe (1-result query)."""
        try:
            await self.search("test", limit=1)
        except Exception:  # noqa: BLE001
            logger.warning("arxiv healthcheck failed", exc_info=True)
            return False
        return True


def _parse_feed(xml: str) -> list[ArxivEntry]:
    """Parse an arXiv Atom feed into `ArxivEntry` rows. Tolerant of missing fields."""
    root = ET.fromstring(xml)
    entries: list[ArxivEntry] = []
    for node in root.findall("atom:entry", _NS):
        entries.append(_parse_entry(node))
    return entries


def _parse_entry(node: ET.Element) -> ArxivEntry:
    raw_id = _text(node.find("atom:id", _NS))
    arxiv_id = raw_id.rsplit("/", 1)[-1] if raw_id else ""
    # Strip trailing version suffix like "v3".
    if arxiv_id and "v" in arxiv_id.split(".")[-1]:
        arxiv_id = arxiv_id.rsplit("v", 1)[0]

    pdf_url: str | None = None
    abs_url: str | None = raw_id or None
    for link in node.findall("atom:link", _NS):
        if link.attrib.get("title") == "pdf":
            pdf_url = link.attrib.get("href")
        elif link.attrib.get("rel") == "alternate":
            abs_url = link.attrib.get("href", abs_url)

    authors = [
        _text(a.find("atom:name", _NS)) for a in node.findall("atom:author", _NS)
    ]
    authors = [a for a in authors if a]

    published = _text(node.find("atom:published", _NS))
    year: int | None = None
    if published[:4].isdigit():
        year = int(published[:4])

    primary_cat: str | None = None
    primary = node.find("arxiv:primary_category", _NS)
    if primary is not None:
        primary_cat = primary.attrib.get("term")

    return ArxivEntry(
        arxiv_id=arxiv_id,
        title=_text(node.find("atom:title", _NS)).strip(),
        summary=_text(node.find("atom:summary", _NS)).strip(),
        authors=authors,
        published_year=year,
        pdf_url=pdf_url,
        abs_url=abs_url,
        primary_category=primary_cat,
    )


def _text(node: ET.Element | None) -> str:
    if node is None or node.text is None:
        return ""
    return node.text
