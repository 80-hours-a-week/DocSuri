"""ResultAssembler terminal-state mapping (BR-9 / U5 B3-a: 기권 ≠ 빈 결과).

A no-match — or a grounding pass that filters every candidate out — is an explicit empty page
(resultCount=0, not silent), in BOTH normal and degraded modes. Only a grounding *refusal*
(AbstainResult) becomes an AbstainDTO.
"""

from __future__ import annotations

from docsuri_shared.dtos import AbstainDTO, SearchResultPageDTO
from docsuri_shared.vector_spec import SourceProvenance

from discovery.domain.assembler import ResultAssembler
from discovery.domain.models import (
    AbstainResult,
    Candidate,
    DegradeMode,
    GroundedResults,
    NoMatchResult,
)
from discovery.mocks.fixtures import RECORDS

_assembler = ResultAssembler()


def _first_card(record):
    """Assemble a single-result success page and return its card."""
    items = (Candidate(record=record, retrieval_score=1.0),)
    response = _assembler.assemble(GroundedResults(items=items), DegradeMode.NORMAL)
    assert isinstance(response.root, SearchResultPageDTO)
    return response.root.cards[0]


def _provenance(*, source_name: str, source_url: str = "", doi: str = "") -> SourceProvenance:
    return SourceProvenance(
        sourceName=source_name,
        sourceId="src-1",
        sourceTier="oa",
        sourceUrl=source_url,
        doi=doi,
        arxivId="",
    )


def test_no_match_is_empty_page_not_abstain() -> None:
    response = _assembler.assemble(NoMatchResult(), DegradeMode.NORMAL)
    assert isinstance(response.root, SearchResultPageDTO)
    assert response.root.cards == []
    assert response.root.meta.resultCount == 0


def test_empty_grounded_normal_is_empty_page() -> None:
    response = _assembler.assemble(GroundedResults(items=()), DegradeMode.NORMAL)
    assert isinstance(response.root, SearchResultPageDTO)
    assert response.root.meta.resultCount == 0


def test_empty_grounded_degraded_is_empty_page_no_banner() -> None:
    # An empty result carries no degrade banner — there are no cards to qualify.
    response = _assembler.assemble(GroundedResults(items=()), DegradeMode.LEXICAL_ONLY)
    assert isinstance(response.root, SearchResultPageDTO)
    assert response.root.meta.degraded is False


def test_no_match_degraded_is_empty_page_no_banner() -> None:
    # Same invariant for a no-match under an active degrade mode: empty page, no banner.
    response = _assembler.assemble(NoMatchResult(), DegradeMode.LEXICAL_ONLY)
    assert isinstance(response.root, SearchResultPageDTO)
    assert response.root.meta.resultCount == 0
    assert response.root.meta.degraded is False


def test_grounding_refusal_is_abstain() -> None:
    response = _assembler.assemble(AbstainResult(reason="no_grounded_results"), DegradeMode.NORMAL)
    assert isinstance(response.root, AbstainDTO)
    assert response.root.reason == "no_grounded_results"


# --- Phase 2 (Q2): source-neutral card projection --------------------------------------------

def test_arxiv_card_defaults_to_arxiv_source() -> None:
    # Legacy/arXiv-only record (no sourceProvenance) → sourceName="arXiv", sourceUrl=arxivUrl.
    record = RECORDS[0]
    assert record.sourceProvenance is None
    card = _first_card(record)
    assert card.sourceName == "arXiv"
    assert card.sourceUrl == record.arxivUrl


def test_non_arxiv_card_uses_provenance_source_url() -> None:
    prov = _provenance(
        source_name="Semantic Scholar", source_url="https://www.semanticscholar.org/paper/abc"
    )
    record = RECORDS[0].model_copy(update={"sourceProvenance": prov})
    card = _first_card(record)
    assert card.sourceName == "Semantic Scholar"
    assert card.sourceUrl == "https://www.semanticscholar.org/paper/abc"


def test_non_arxiv_card_falls_back_to_doi_link() -> None:
    # No sourceUrl but a DOI → resolvable doi.org link (FR-5: real link, no fabrication).
    prov = _provenance(source_name="OpenAlex", source_url="", doi="10.1234/abcd")
    record = RECORDS[0].model_copy(update={"sourceProvenance": prov})
    card = _first_card(record)
    assert card.sourceName == "OpenAlex"
    assert card.sourceUrl == "https://doi.org/10.1234/abcd"


def test_non_arxiv_card_falls_back_to_arxiv_url_when_no_link() -> None:
    # Neither sourceUrl nor DOI → fall back to the record's arxivUrl (still a real link).
    prov = _provenance(source_name="OpenAlex", source_url="", doi="")
    record = RECORDS[0].model_copy(update={"sourceProvenance": prov})
    card = _first_card(record)
    assert card.sourceUrl == record.arxivUrl
