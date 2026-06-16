"""ResultAssembler — FR-4/FR-11 (BR-6/9/15; INV-2; PBT-09).

Maps grounded results / abstain to the external ``SearchResponse`` union. SEC-9: a card
exposes ONLY the 7 projected fields (``relevance`` is the display rank position, NOT the raw
RRF score). No empty success page — a no-match is an AbstainDTO (BR-9). When a degrade mode
is active for a successful response, returns DegradedResultDTO with the mode (BR-11).
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

from .models import AbstainResult, Candidate, DegradeMode, GroundedResults


def _card(candidate: Candidate, rank: int) -> ResultCardVM:
    """Project a real IndexRecord to the 7 card fields (SEC-9). ``relevance`` = 1-based rank
    (display-only; raw retrieval_score is NOT exposed)."""
    r = candidate.record
    return ResultCardVM(
        title=r.title,
        authors=list(r.authors),
        year=r.year,
        arxivId=r.arxivId,
        abstractSnippet=r.abstractSnippet,
        relevance=rank,
        arxivUrl=r.arxivUrl,
    )


class ResultAssembler:
    def assemble(
        self, result: GroundedResults | AbstainResult, degrade_mode: DegradeMode
    ) -> SearchResponse:
        if isinstance(result, AbstainResult):
            return SearchResponse(AbstainDTO(reason=result.reason))

        cards = [_card(c, rank=i + 1) for i, c in enumerate(result.items)]
        if degrade_mode is DegradeMode.NORMAL:
            meta = ResultMeta(resultCount=len(cards), degraded=False, degradationMode=None)
            return SearchResponse(SearchResultPageDTO(cards=cards, meta=meta))

        mode = DegradationMode(degrade_mode.value)
        meta = ResultMeta(resultCount=len(cards), degraded=True, degradationMode=mode)
        return SearchResponse(DegradedResultDTO(cards=cards, meta=meta, mode=mode))
