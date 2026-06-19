"""PaperMetadataService — single-paper detail-header lookup (U2-owned corpus data).

Covers: known id (by paperId AND by display arxivId) → projected PaperMetaDTO with the full
abstract; unknown id → None (detail page degrades); store outage → SearchUnavailable (INV-3,
fail-closed). No FastAPI dependency — the service is exercised directly.
"""

from __future__ import annotations

import pytest

from discovery.mocks.adapters import MockPaperLookupAdapter
from discovery.ports.search_ports import IndexUnavailable, SearchUnavailable
from discovery.service.paper_metadata import PaperMetadataService, PaperMetaDTO


def _service() -> PaperMetadataService:
    return PaperMetadataService(MockPaperLookupAdapter())


def test_known_paper_by_paper_id_projects_full_metadata() -> None:
    meta = _service().get_paper_meta("2401.00001")
    assert isinstance(meta, PaperMetaDTO)
    assert meta.title == "Diffusion Models for Protein Structure Prediction"
    assert meta.authors == ["A. Researcher", "B. Scientist"]
    assert meta.year == 2024
    assert meta.arxivId == "2401.00001v1"
    # The detail endpoint exposes the FULL abstract (the paper's own page), not just a snippet.
    assert meta.abstract == "We apply diffusion models to predict protein structure from sequence."
    assert meta.arxivUrl == "https://arxiv.org/abs/2401.00001"


def test_known_paper_by_display_arxiv_id() -> None:
    # The detail route id is the display arxivId (e.g. "2401.00002v1"), not the version-less id.
    meta = _service().get_paper_meta("2401.00002v1")
    assert meta is not None
    assert meta.title == "Large Language Models as Few-Shot Learners"


def test_unknown_paper_returns_none() -> None:
    assert _service().get_paper_meta("9999.99999") is None


def test_store_outage_is_fail_closed() -> None:
    class _FailingLookup:
        def fetch_paper(self, paper_id: str):
            raise IndexUnavailable("mock store outage")

    with pytest.raises(SearchUnavailable):
        PaperMetadataService(_FailingLookup()).get_paper_meta("2401.00001")
