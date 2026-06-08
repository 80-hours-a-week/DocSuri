"""Unit tests for the #01a Search slice (Sprint 1 walking skeleton).

Scope (per Sprint-Backlog-Search row 1 DoD):
- `ArxivAdapter` parses canned arXiv Atom XML into >= 1 `PaperSummary`.
- Query normalizer maps `nlp` → `cs.CL` with the mock LLM.

Live arXiv hits are NOT made — `httpx.AsyncClient.get` is patched with a
canned XML string. The mock LLM is the default (no `ANTHROPIC_API_KEY`).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.domain.papers.models import PaperSummary
from app.domain.papers.normalizer import normalize
from app.domain.papers.search import ArxivAdapter, MultiDBRouter
from app.infra.http.arxiv import ArxivClient

# Minimal but realistic arXiv Atom feed (1 entry).
_CANNED_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>1</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/2401.12345v2</id>
    <updated>2024-01-15T00:00:00Z</updated>
    <published>2024-01-10T00:00:00Z</published>
    <title>A Walking Skeleton for Semantic Paper Search</title>
    <summary>We present a minimal pipeline for academic search.</summary>
    <author><name>Alice Researcher</name></author>
    <author><name>Bob Reviewer</name></author>
    <link href="http://arxiv.org/abs/2401.12345v2" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/2401.12345v2" rel="related" type="application/pdf"/>
    <arxiv:primary_category term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>
"""


def _fake_response(text: str, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        text=text,
        request=httpx.Request("GET", "https://export.arxiv.org/api/query"),
    )


@pytest.mark.asyncio
async def test_arxiv_adapter_parses_canned_feed() -> None:
    """ArxivAdapter.search → at least one fully-populated PaperSummary."""
    async_client = httpx.AsyncClient()
    try:
        with patch.object(
            async_client,
            "get",
            new=AsyncMock(return_value=_fake_response(_CANNED_FEED)),
        ):
            adapter = ArxivAdapter(ArxivClient(client=async_client))
            nq = await normalize("walking skeleton")
            rows = await adapter.search(nq, limit=5)
    finally:
        await async_client.aclose()

    assert len(rows) >= 1
    row = rows[0]
    assert isinstance(row, PaperSummary)
    assert row.id == "2401.12345"  # version suffix stripped
    assert row.source == "arxiv"
    assert "Walking Skeleton" in row.title
    assert row.authors == ["Alice Researcher", "Bob Reviewer"]
    assert row.year == 2024
    assert row.pdf_url == "http://arxiv.org/pdf/2401.12345v2"
    assert row.arxiv_url == "http://arxiv.org/abs/2401.12345v2"


@pytest.mark.asyncio
async def test_normalizer_detects_cs_cl_for_nlp_in_mock_mode() -> None:
    """`nlp` keyword routes to arXiv category cs.CL even without LLM expansion."""
    nq = await normalize("recent NLP transformer survey")
    assert "cs.CL" in nq.fields
    arxiv_query = nq.for_arxiv()
    assert "cat:cs.CL" in arxiv_query
    assert nq.expanded is False


@pytest.mark.asyncio
async def test_router_returns_results_and_normalized_query() -> None:
    """MultiDBRouter wires normalizer + adapter and surfaces both outputs."""
    async_client = httpx.AsyncClient()
    try:
        with patch.object(
            async_client,
            "get",
            new=AsyncMock(return_value=_fake_response(_CANNED_FEED)),
        ):
            router = MultiDBRouter(
                [ArxivAdapter(ArxivClient(client=async_client))]
            )
            rows, nq = await router.search("nlp survey", limit=3)
    finally:
        await async_client.aclose()

    assert len(rows) == 1
    assert "cat:cs.CL" in nq.for_arxiv()


def test_arxiv_adapter_boundary_imports_are_safe() -> None:
    """AGENTS.md §5.2: search module must not import sibling domains.

    Parses the AST so a docstring or comment naming the forbidden modules
    (e.g. a §5.2 rationale string) does not produce a false positive.
    """
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
