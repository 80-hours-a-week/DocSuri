"""Async PubMed eUtils client.

Uses the NCBI eUtils API (esearch + efetch) to search PubMed and parse the
returned XML into raw dataclasses. Pure transport layer — no domain mapping
happens here (that lives in `domain/papers/search.py`).

References:
- NCBI eUtils: https://www.ncbi.nlm.nih.gov/books/NBK25499/
- Rate limit: 3 req/s without API key, 10 req/s with key (AGENTS.md §4.5).
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

# NCBI allows 3 req/s without an API key (AGENTS.md §4.5).
_PUBMED_BUCKET = TokenBucket(rate_per_sec=3.0, capacity=3)


@dataclass
class PubMedEntry:
    """Raw record parsed from one PubMed article XML."""

    pmid: str
    title: str
    abstract: str | None
    authors: list[str]
    year: int | None
    journal: str | None


class PubMedClient:
    """Thin async wrapper around the NCBI PubMed eUtils API.

    Uses an injected `httpx.AsyncClient` so tests can hand in a mocked
    transport. Caller owns the client's lifetime (e.g. FastAPI lifespan).
    """

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    TIMEOUT = 5.0
    ESEARCH_URL = BASE_URL + "/esearch.fcgi"
    EFETCH_URL = BASE_URL + "/efetch.fcgi"

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        bucket: TokenBucket = _PUBMED_BUCKET,
        api_key: str = "",
    ) -> None:
        self._client = client or httpx.AsyncClient(timeout=self.TIMEOUT)
        self._owns_client = client is None
        self._bucket = bucket
        self._api_key = api_key

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _base_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {"db": "pubmed"}
        if self._api_key:
            params["api_key"] = self._api_key
        return params

    @RateLimitedRetry(max_attempts=3)
    async def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """Fetch JSON from NCBI eUtils (esearch).

        Time: O(N) JSON parse where N=retmax.
        Rate limit: 3 req/s without API key; 10 req/s with key.
        Edge: SSRF check raises SSRFViolation before network call.
        """
        verify_url(url)
        await self._bucket.acquire()
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    @RateLimitedRetry(max_attempts=3)
    async def _get_xml(self, url: str, params: dict[str, Any]) -> str:
        """Fetch XML from NCBI eUtils (efetch).

        Time: O(N) XML parse where N=number of PMIDs.
        Rate limit: 3 req/s without API key; 10 req/s with key.
        Edge: SSRF check raises SSRFViolation before network call.
        """
        verify_url(url)
        await self._bucket.acquire()
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        return resp.text

    async def search(self, query: str, *, limit: int = 10) -> list[PubMedEntry]:
        """Search PubMed via esearch + efetch and return parsed entries.

        Time: O(N) where N=limit (two sequential HTTP calls: esearch then efetch).
        Rate limit: 3 req/s without API key; 10_000 PMIDs max per esearch.
        Edge: esearch returns no PMIDs → returns [] without calling efetch.
        """
        logger.info("pubmed.search query=%r limit=%d", query, limit)
        pmids = await self._esearch(query, limit=max(1, min(limit, 10_000)))
        if not pmids:
            return []
        return await self._efetch(pmids)

    async def _esearch(self, query: str, *, limit: int) -> list[str]:
        params = {**self._base_params(), "term": query, "retmax": limit, "retmode": "json"}
        data = await self._get_json(self.ESEARCH_URL, params)
        return data.get("esearchresult", {}).get("idlist", [])

    async def _efetch(self, pmids: list[str]) -> list[PubMedEntry]:
        params = {
            **self._base_params(),
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract",
        }
        xml = await self._get_xml(self.EFETCH_URL, params)
        return _parse_pubmed_xml(xml)

    async def healthcheck(self) -> bool:
        """Cheap reachability probe (1-result query)."""
        try:
            await self.search("cancer", limit=1)
        except Exception:  # noqa: BLE001
            logger.warning("pubmed healthcheck failed", exc_info=True)
            return False
        return True


def _parse_pubmed_xml(xml: str) -> list[PubMedEntry]:
    root = ET.fromstring(xml)
    return [_parse_article(article) for article in root.findall("PubmedArticle")]


def _parse_article(article: ET.Element) -> PubMedEntry:
    citation = article.find("MedlineCitation")
    if citation is None:
        return PubMedEntry(pmid="", title="", abstract=None, authors=[], year=None, journal=None)

    pmid_node = citation.find("PMID")
    pmid = (pmid_node.text or "") if pmid_node is not None else ""

    art = citation.find("Article")
    if art is None:
        return PubMedEntry(pmid=pmid, title="", abstract=None, authors=[], year=None, journal=None)

    title_node = art.find("ArticleTitle")
    title = (title_node.text or "").strip() if title_node is not None else ""

    abstract_texts: list[str] = []
    abstract_node = art.find("Abstract")
    if abstract_node is not None:
        for at in abstract_node.findall("AbstractText"):
            text = at.text or ""
            label = at.attrib.get("Label")
            abstract_texts.append(f"{label}: {text}" if label else text)
    abstract = " ".join(abstract_texts) if abstract_texts else None

    authors: list[str] = []
    author_list = art.find("AuthorList")
    if author_list is not None:
        for author in author_list.findall("Author"):
            last = _el_text(author.find("LastName"))
            fore = _el_text(author.find("ForeName"))
            name = " ".join(filter(None, [fore, last]))
            if name:
                authors.append(name)

    journal_node = art.find("Journal")
    journal_title: str | None = None
    year: int | None = None
    if journal_node is not None:
        jt = journal_node.find("Title")
        journal_title = jt.text if jt is not None else None
        issue = journal_node.find("JournalIssue")
        if issue is not None:
            pub_date = issue.find("PubDate")
            if pub_date is not None:
                year_node = pub_date.find("Year")
                if year_node is not None and year_node.text and year_node.text.isdigit():
                    year = int(year_node.text)

    return PubMedEntry(
        pmid=pmid,
        title=title,
        abstract=abstract,
        authors=authors,
        year=year,
        journal=journal_title,
    )


def _el_text(node: ET.Element | None) -> str:
    return (node.text or "") if node is not None else ""
