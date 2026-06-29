"""ResultAssembler — FR-4/FR-11 (BR-6/9/15; INV-2; PBT-09).

Maps grounded results / no-match / abstain to the external ``SearchResponse`` union. SEC-9: a
card exposes ONLY the projected fields (``relevance`` is the display rank position, NOT the
raw RRF score). A no-match (or a grounding pass that filtered out every candidate) is an
explicit empty page (resultCount=0), distinct from a grounding *refusal* which is an AbstainDTO
(BR-9 / U5 B3-a: 기권 ≠ 빈 결과). When a degrade mode is active for a non-empty successful
response, returns DegradedResultDTO with the mode (BR-11).
"""

from __future__ import annotations

from docsuri_shared.dtos import (
    AbstainDTO,
    DegradationMode,
    DegradedResultDTO,
    ResultCardVM,
    ResultMeta,
    SearchResponse,
    SearchResultPageDTO,
)
from docsuri_shared.vector_spec import IndexRecord

from .models import AbstainResult, Candidate, DegradeMode, GroundedResults, NoMatchResult


def _source_ref(r: IndexRecord) -> tuple[str, str]:
    """Source-neutral (name, url) projection for the multi-source corpus (Phase 2 / Q2).

    arXiv path keeps ``arxivUrl``; a non-arXiv record (Semantic Scholar / OpenAlex) uses its
    ``sourceProvenance.sourceUrl`` (or a DOI link), falling back to ``arxivUrl`` if neither is
    set. Legacy/arXiv-only records (no provenance) default to "arXiv" + arxivUrl. Only these two
    derived fields are exposed — the full ``sourceProvenance`` stays internal (SEC-9 / Q3)."""
    prov = r.sourceProvenance
    if prov is None or not prov.sourceName:
        return "arXiv", r.arxivUrl
    if prov.sourceName.lower() == "arxiv":
        return prov.sourceName, r.arxivUrl
    url = prov.sourceUrl or (f"https://doi.org/{prov.doi}" if prov.doi else r.arxivUrl)
    return prov.sourceName, url


def _card(candidate: Candidate, rank: int) -> ResultCardVM:
    """Project a real IndexRecord to the exposed card fields (SEC-9). ``relevance`` = 1-based
    rank (display-only; raw retrieval_score is NOT exposed). Phase 2 (Q2): adds source-neutral
    ``sourceName``/``sourceUrl`` so non-arXiv results carry a real link (FR-5)."""
    r = candidate.record
    source_name, source_url = _source_ref(r)
    return ResultCardVM(
        title=r.title,
        authors=list(r.authors),
        year=r.year,
        arxivId=r.arxivId,
        abstractSnippet=r.abstractSnippet,
        relevance=rank,
        arxivUrl=r.arxivUrl,
        sourceName=source_name,
        sourceUrl=source_url,
    )


class ResultAssembler:
    def assemble(
        self,
        result: GroundedResults | AbstainResult | NoMatchResult,
        degrade_mode: DegradeMode,
    ) -> SearchResponse:
        # A grounding *refusal* (verdict block/abstain) is the only true abstain.
        if isinstance(result, AbstainResult):
            return SearchResponse(AbstainDTO(reason=result.reason))

        # No-match, or a grounding pass that filtered out every candidate: an explicit empty
        # page (resultCount=0), NOT an abstain (BR-9 / U5 B3-a: 기권 ≠ 빈 결과). The empty page
        # carries no degrade banner — there are no cards to qualify.
        # Order matters: NoMatchResult is checked first so ``.items`` is only read on the
        # remaining GroundedResults branch (NoMatchResult has no ``items``).
        if isinstance(result, NoMatchResult) or not result.items:
            meta = ResultMeta(resultCount=0, degraded=False, degradationMode=None)
            return SearchResponse(SearchResultPageDTO(cards=[], meta=meta))

        cards = [_card(c, rank=i + 1) for i, c in enumerate(result.items)]
        if degrade_mode is DegradeMode.NORMAL:
            meta = ResultMeta(resultCount=len(cards), degraded=False, degradationMode=None)
            return SearchResponse(SearchResultPageDTO(cards=cards, meta=meta))

        mode = DegradationMode(degrade_mode.value)
        meta = ResultMeta(resultCount=len(cards), degraded=True, degradationMode=mode)
        return SearchResponse(DegradedResultDTO(cards=cards, meta=meta, mode=mode))
