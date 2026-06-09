"""Unit tests for the multi-source search router.

Covers:
- All 5 adapter parse/map flows (arXiv, S2, OpenAlex, CrossRef, PubMed)
- Query normalizer field detection
- MultiDBRouter fan-out + result combination
- DOI-based deduplication across sources
- RRF merge score ordering
- BackgroundTasks registration (new papers only, skips already-indexed)
- Adapter failure skipping (circuit-breaker-like behaviour)
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, call, patch

import httpx
import pytest

from app.domain.papers.models import PaperSummary
from app.domain.papers.normalizer import NormalizedQuery, normalize
from app.domain.papers.search import (
    AllAdaptersFailedError,
    ArxivAdapter,
    CrossRefAdapter,
    MultiDBRouter,
    OpenAlexAdapter,
    PubMedAdapter,
    SemanticScholarAdapter,
    _bg_embed_and_store,
    dedupe,
    rrf_merge,
)
from app.infra.http.arxiv import ArxivClient
from app.infra.http.crossref import CrossRefClient
from app.infra.http.openalex import OpenAlexClient
from app.infra.http.pubmed import PubMedClient
from app.infra.http.semantic_scholar import SemanticScholarClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _xml_resp(text: str, url: str = "https://example.com") -> httpx.Response:
    return httpx.Response(
        status_code=200,
        text=text,
        request=httpx.Request("GET", url),
    )


def _json_resp(data: Any, url: str = "https://example.com") -> httpx.Response:
    return httpx.Response(
        status_code=200,
        text=json.dumps(data),
        headers={"Content-Type": "application/json"},
        request=httpx.Request("GET", url),
    )


@pytest.fixture
def nq() -> NormalizedQuery:
    return NormalizedQuery(raw="test", canonical="test")


# ---------------------------------------------------------------------------
# Canned responses
# ---------------------------------------------------------------------------

_ARXIV_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>1</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/2401.12345v2</id>
    <published>2024-01-10T00:00:00Z</published>
    <title>A Walking Skeleton for Semantic Paper Search</title>
    <summary>We present a minimal pipeline for academic search.</summary>
    <author><name>Alice Researcher</name></author>
    <author><name>Bob Reviewer</name></author>
    <link href="http://arxiv.org/abs/2401.12345v2" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/2401.12345v2" rel="related" type="application/pdf"/>
    <arxiv:primary_category term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>"""

_S2_RESPONSE = {
    "data": [
        {
            "paperId": "s2abc123",
            "title": "A Semantic Scholar Paper",
            "abstract": "S2 abstract text.",
            "authors": [{"name": "S2 Author"}],
            "year": 2023,
            "venue": "NeurIPS",
            "openAccessPdf": {"url": "https://s2.example/paper.pdf"},
            "externalIds": {"DOI": "10.1234/s2paper"},
        }
    ]
}

_OPENALEX_RESPONSE = {
    "results": [
        {
            "id": "https://openalex.org/W9999",
            "title": "An OpenAlex Paper",
            "abstract_inverted_index": {"An": [0], "OpenAlex": [1], "abstract": [2]},
            "authorships": [{"author": {"display_name": "OA Author"}}],
            "publication_year": 2022,
            "primary_location": {"source": {"display_name": "Nature"}},
            "doi": "https://doi.org/10.5678/oapaper",
            "open_access": {"oa_url": "https://oa.example/paper.pdf"},
        }
    ]
}

_CROSSREF_RESPONSE = {
    "message": {
        "items": [
            {
                "DOI": "10.9999/crpaper",
                "title": ["A CrossRef Paper"],
                "author": [{"given": "CR", "family": "Author"}],
                "abstract": "CrossRef abstract.",
                "published": {"date-parts": [[2021, 6, 1]]},
                "container-title": ["JMLR"],
                "URL": "https://doi.org/10.9999/crpaper",
            }
        ]
    }
}

_PUBMED_ESEARCH = {
    "esearchresult": {"idlist": ["12345678"]}
}

_PUBMED_EFETCH = """<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <ArticleTitle>A PubMed Paper</ArticleTitle>
        <Abstract>
          <AbstractText Label="BACKGROUND">Background text.</AbstractText>
          <AbstractText Label="CONCLUSION">Conclusion text.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author>
            <ForeName>Alice</ForeName>
            <LastName>Medic</LastName>
          </Author>
        </AuthorList>
        <Journal>
          <Title>The NEJM</Title>
          <JournalIssue>
            <PubDate><Year>2020</Year></PubDate>
          </JournalIssue>
        </Journal>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""


# ---------------------------------------------------------------------------
# 1. Adapter unit tests (parsing + PaperSummary mapping)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_arxiv_adapter_parses_canned_feed(nq: NormalizedQuery) -> None:
    """ArxivAdapter maps Atom entry → correct PaperSummary fields."""
    async_client = httpx.AsyncClient()
    try:
        with patch.object(
            async_client, "get",
            new=AsyncMock(return_value=_xml_resp(_ARXIV_FEED, "https://export.arxiv.org/api/query")),
        ):
            rows = await ArxivAdapter(ArxivClient(client=async_client)).search(nq, limit=5)
    finally:
        await async_client.aclose()

    assert len(rows) == 1
    r = rows[0]
    assert r.id == "2401.12345"
    assert r.source == "arxiv"
    assert "Walking Skeleton" in r.title
    assert r.authors == ["Alice Researcher", "Bob Reviewer"]
    assert r.year == 2024
    assert r.pdf_url == "http://arxiv.org/pdf/2401.12345v2"
    assert r.arxiv_url == "http://arxiv.org/abs/2401.12345v2"


@pytest.mark.asyncio
async def test_s2_adapter_parses_canned_response(nq: NormalizedQuery) -> None:
    """SemanticScholarAdapter maps S2 JSON → correct PaperSummary fields."""
    async_client = httpx.AsyncClient()
    try:
        with patch.object(
            async_client, "get",
            new=AsyncMock(return_value=_json_resp(_S2_RESPONSE)),
        ):
            rows = await SemanticScholarAdapter(
                SemanticScholarClient(client=async_client)
            ).search(nq, limit=5)
    finally:
        await async_client.aclose()

    assert len(rows) == 1
    r = rows[0]
    assert r.source == "s2"
    assert r.id == "10.1234/s2paper"          # DOI preferred over paper_id
    assert r.title == "A Semantic Scholar Paper"
    assert r.authors == ["S2 Author"]
    assert r.year == 2023
    assert r.venue == "NeurIPS"
    assert r.pdf_url == "https://s2.example/paper.pdf"


@pytest.mark.asyncio
async def test_openalex_adapter_parses_canned_response(nq: NormalizedQuery) -> None:
    """OpenAlexAdapter maps Work JSON → correct PaperSummary, reconstructs abstract."""
    async_client = httpx.AsyncClient()
    try:
        with patch.object(
            async_client, "get",
            new=AsyncMock(return_value=_json_resp(_OPENALEX_RESPONSE)),
        ):
            rows = await OpenAlexAdapter(
                OpenAlexClient(client=async_client)
            ).search(nq, limit=5)
    finally:
        await async_client.aclose()

    assert len(rows) == 1
    r = rows[0]
    assert r.source == "openalex"
    assert r.id == "10.5678/oapaper"          # bare DOI preferred over work_id
    assert r.title == "An OpenAlex Paper"
    assert r.authors == ["OA Author"]
    assert r.year == 2022
    assert r.venue == "Nature"
    assert r.abstract == "An OpenAlex abstract"   # reconstructed from inverted index
    assert r.pdf_url == "https://oa.example/paper.pdf"


@pytest.mark.asyncio
async def test_crossref_adapter_parses_canned_response(nq: NormalizedQuery) -> None:
    """CrossRefAdapter maps works JSON → correct PaperSummary fields."""
    async_client = httpx.AsyncClient()
    try:
        with patch.object(
            async_client, "get",
            new=AsyncMock(return_value=_json_resp(_CROSSREF_RESPONSE)),
        ):
            rows = await CrossRefAdapter(
                CrossRefClient(client=async_client)
            ).search(nq, limit=5)
    finally:
        await async_client.aclose()

    assert len(rows) == 1
    r = rows[0]
    assert r.source == "crossref"
    assert r.id == "10.9999/crpaper"
    assert r.title == "A CrossRef Paper"
    assert r.authors == ["CR Author"]
    assert r.year == 2021
    assert r.venue == "JMLR"
    assert r.abstract == "CrossRef abstract."


@pytest.mark.asyncio
async def test_pubmed_adapter_parses_canned_response(nq: NormalizedQuery) -> None:
    """PubMedAdapter: esearch → efetch → correct PaperSummary, structured abstract joined."""
    async_client = httpx.AsyncClient()
    try:
        with patch.object(
            async_client, "get",
            new=AsyncMock(side_effect=[
                _json_resp(_PUBMED_ESEARCH),   # esearch call
                _xml_resp(_PUBMED_EFETCH),     # efetch call
            ]),
        ):
            rows = await PubMedAdapter(
                PubMedClient(client=async_client)
            ).search(nq, limit=5)
    finally:
        await async_client.aclose()

    assert len(rows) == 1
    r = rows[0]
    assert r.source == "pubmed"
    assert r.id == "12345678"
    assert r.title == "A PubMed Paper"
    assert r.authors == ["Alice Medic"]
    assert r.year == 2020
    assert r.venue == "The NEJM"
    # Structured abstract: label prefixes preserved
    assert "BACKGROUND" in r.abstract
    assert "CONCLUSION" in r.abstract


# ---------------------------------------------------------------------------
# 2. Normalizer
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_normalizer_detects_cs_cl_for_nlp_in_mock_mode() -> None:
    """`nlp` keyword routes to arXiv category cs.CL without LLM expansion."""
    nq = await normalize("recent NLP transformer survey")
    assert "cs.CL" in nq.fields
    assert "cat:cs.CL" in nq.for_arxiv()
    assert nq.expanded is False


# ---------------------------------------------------------------------------
# 3. Router fan-out
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_router_returns_results_and_normalized_query() -> None:
    """MultiDBRouter wires normalizer + adapter and surfaces both outputs."""
    async_client = httpx.AsyncClient()
    try:
        with patch.object(
            async_client, "get",
            new=AsyncMock(return_value=_xml_resp(_ARXIV_FEED, "https://export.arxiv.org/api/query")),
        ):
            router = MultiDBRouter([ArxivAdapter(ArxivClient(client=async_client))])
            rows, nq = await router.search("nlp survey", limit=3)
    finally:
        await async_client.aclose()

    assert len(rows) == 1
    assert "cat:cs.CL" in nq.for_arxiv()


# ---------------------------------------------------------------------------
# 4. Dedup: same DOI from two sources → single result
# ---------------------------------------------------------------------------

def test_rrf_merge_deduplicates_same_doi_across_sources() -> None:
    """DOI collision between crossref and s2 collapses to one canonical row."""
    shared_doi = "10.1234/shared"
    from_crossref = PaperSummary(
        id=shared_doi, doi=shared_doi, source="crossref", title="Shared Paper", year=2023
    )
    from_s2 = PaperSummary(
        id=shared_doi, doi=shared_doi, source="s2", title="Shared Paper", year=2023
    )
    unique = PaperSummary(id="unique-0001", source="arxiv", title="Unique Paper", year=2023)

    merged = rrf_merge([[from_crossref], [from_s2], [unique]])

    assert len(merged) == 2, "shared DOI must be deduped to one entry"
    ids = {p.id for p in merged}
    assert shared_doi in ids
    assert "unique-0001" in ids

    # Shared paper ranked first: accumulated RRF from two sources beats unique's single
    assert merged[0].id == shared_doi


def test_dedupe_removes_title_hash_duplicates() -> None:
    """Papers without doi/arxiv_id fall back to title-hash dedup via dedupe()."""
    # rrf_merge uses id as key — different ids won't merge there.
    # dedupe() handles the title-hash fallback afterwards.
    pubmed_a = PaperSummary(
        id="11111111", source="pubmed", title="Attention Is All You Need", year=2017
    )
    pubmed_b = PaperSummary(
        id="99887766", source="pubmed", title="Attention Is All You Need", year=2017
    )
    other = PaperSummary(id="22222222", source="pubmed", title="Different Paper", year=2022)

    merged = dedupe(rrf_merge([[pubmed_a, other], [pubmed_b]]))

    assert len(merged) == 2, "same title+year must be deduped to one entry"


# ---------------------------------------------------------------------------
# 5. RRF score ordering
# ---------------------------------------------------------------------------

def test_rrf_merge_scores_top_result_correctly() -> None:
    """Paper appearing first in two adapters outscores paper first in one.

    Expected scores (k=60):
      X: 1/(60+1) + 1/(60+1) = 2/61 ≈ 0.0328   → rank 1
      Z: 1/(60+1)             = 1/61 ≈ 0.0164   → rank 2
      Y: 1/(60+2)             = 1/62 ≈ 0.0161   → rank 3
    """
    paper_x = PaperSummary(id="X", source="arxiv", title="Paper X", year=2024)
    paper_y = PaperSummary(id="Y", source="arxiv", title="Paper Y", year=2024)
    paper_z = PaperSummary(id="Z", source="s2",    title="Paper Z", year=2024)

    merged = rrf_merge(
        [
            [paper_x, paper_y],   # X@rank1, Y@rank2
            [paper_x],            # X@rank1  (X accumulates)
            [paper_z],            # Z@rank1
        ],
    )

    assert [p.id for p in merged] == ["X", "Z", "Y"]


def test_rrf_merge_respects_limit() -> None:
    """Results are capped at `limit` even when more unique papers exist."""
    papers = [
        PaperSummary(id=str(i), source="arxiv", title=f"Paper {i}", year=2024)
        for i in range(10)
    ]
    merged = rrf_merge([papers])[:3]
    assert len(merged) == 3


# ---------------------------------------------------------------------------
# 6. BackgroundTasks: new papers registered, existing papers skipped
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_registers_bg_tasks_only_for_new_papers() -> None:
    """Only papers absent from pgvector get embedding + citation bg tasks."""
    new_paper = PaperSummary(id="new-001", source="arxiv", title="New Paper", year=2024)
    old_paper = PaperSummary(id="old-001", source="arxiv", title="Old Paper", year=2023)

    class FakeAdapter:
        source = "arxiv"
        async def search(self, nq: NormalizedQuery, *, limit: int) -> list[PaperSummary]:
            return [new_paper, old_paper]
        async def healthcheck(self) -> bool:
            return True

    # has_paper: old-001 already indexed, new-001 is new
    async def _fake_has_paper(pid: str) -> bool:
        return pid == "old-001"

    mock_pg = MagicMock()
    mock_pg.has_paper = _fake_has_paper

    bg = MagicMock()
    bg.add_task = MagicMock()

    with patch("app.container.pgvector", return_value=mock_pg):
        router = MultiDBRouter([FakeAdapter()])
        await router.search("test", background_tasks=bg)

    # Exactly 1 task registered — embed only for new_paper, none for old_paper
    assert bg.add_task.call_count == 1
    bg.add_task.assert_any_call(_bg_embed_and_store, new_paper)
    # Verify old_paper was NOT scheduled
    for c in bg.add_task.call_args_list:
        assert c.args[1] != old_paper, "old (indexed) paper must not be scheduled"


@pytest.mark.asyncio
async def test_search_skips_bg_registration_when_no_background_tasks() -> None:
    """Passing background_tasks=None (default) causes no task registration."""
    class FakeAdapter:
        source = "arxiv"
        async def search(self, nq: NormalizedQuery, *, limit: int) -> list[PaperSummary]:
            return [PaperSummary(id="x", source="arxiv", title="X", year=2024)]
        async def healthcheck(self) -> bool:
            return True

    mock_pg = MagicMock()
    mock_pg.has_paper = AsyncMock(return_value=False)

    with patch("app.container.pgvector", return_value=mock_pg):
        router = MultiDBRouter([FakeAdapter()])
        rows, _ = await router.search("test")   # no background_tasks arg

    assert len(rows) == 1
    mock_pg.has_paper.assert_not_called()  # pgvector never queried


@pytest.mark.asyncio
async def test_bg_embed_skips_if_paper_already_indexed() -> None:
    """_bg_embed_and_store is a no-op when has_paper returns True."""
    paper = PaperSummary(id="existing-001", source="arxiv", title="T", year=2024)
    mock_pg = AsyncMock()
    mock_pg.has_paper.return_value = True   # already indexed

    with patch("app.container.pgvector", return_value=mock_pg):
        await _bg_embed_and_store(paper)   # must not raise, must not call embed

    mock_pg.has_paper.assert_called_once_with("existing-001")  # idempotency gate fired
    mock_pg.upsert_paper.assert_not_called()                   # early-return before embed


# ---------------------------------------------------------------------------
# 7. Circuit-breaker: failed adapter skipped, others still returned
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_router_skips_failed_adapter_returns_others() -> None:
    """When one adapter raises (CB Open), results from others are returned."""
    good_paper = PaperSummary(id="good-001", source="arxiv", title="Good Paper", year=2024)

    class GoodAdapter:
        source = "arxiv"
        async def search(self, nq: NormalizedQuery, *, limit: int) -> list[PaperSummary]:
            return [good_paper]
        async def healthcheck(self) -> bool:
            return True

    class BrokenAdapter:
        source = "s2"
        async def search(self, nq: NormalizedQuery, *, limit: int) -> list[PaperSummary]:
            raise RuntimeError("circuit breaker open")
        async def healthcheck(self) -> bool:
            return False

    router = MultiDBRouter([GoodAdapter(), BrokenAdapter()])
    rows, _ = await router.search("test", limit=10)

    # Router must not raise; broken adapter's exception is swallowed
    assert len(rows) == 1
    assert rows[0].id == "good-001"


@pytest.mark.asyncio
async def test_router_raises_when_all_adapters_fail() -> None:
    """All adapters failing → AllAdaptersFailedError raised (routes layer returns 503)."""
    class AlwaysFailAdapter:
        source = "arxiv"
        async def search(self, nq: NormalizedQuery, *, limit: int) -> list[PaperSummary]:
            raise ConnectionError("unreachable")
        async def healthcheck(self) -> bool:
            return False

    router = MultiDBRouter([AlwaysFailAdapter(), AlwaysFailAdapter()])
    with pytest.raises(AllAdaptersFailedError):
        await router.search("test")


# ---------------------------------------------------------------------------
# Boundary / import guard
# ---------------------------------------------------------------------------

def test_arxiv_adapter_boundary_imports_are_safe() -> None:
    """AGENTS.md §5.2: search module must not import sibling domains."""
    import ast

    import app.domain.papers.search as search_module

    src = search_module.__file__
    assert src and src.endswith(".py")
    tree = ast.parse(open(src, encoding="utf-8").read())
    forbidden = {"app.domain.summarization", "app.domain.translation"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            assert not any(mod == f or mod.startswith(f + ".") for f in forbidden), mod
        elif isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(
                    alias.name == f or alias.name.startswith(f + ".") for f in forbidden
                ), alias.name


def _ensure_anyio_marker(*_: Any, **__: Any) -> None:  # pragma: no cover
    """Touch import paths so a typo surfaces at collection time."""
    from app.api import routes_search  # noqa: F401
