"""PaperMetadataService — single-paper header metadata for the detail route.

A small, search-pipeline-independent service: given a paper id (paperId or display arxivId),
read ONE corpus record via the injected ``PaperLookupAdapter`` and project it to the external
``PaperMetaDTO``. This lives in U2 (discovery), not U7 (summarization), because title/authors/
abstract are corpus/index data that U2 owns — U7 has no such fields.

SEC-9: the projection is an explicit field whitelist. Unlike the SEARCH card (which exposes
only the abstract *snippet*), the detail endpoint deliberately returns the FULL abstract — it
is the paper's own public arXiv abstract shown on that paper's own page, not a cross-paper
search leak. Internal index fields (vector/lexicalTerms/chunkId/section/categories) are never
exposed. Fail-closed: a store failure surfaces as ``SearchUnavailable`` (INV-3/SEC-15).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ..ports.search_ports import IndexUnavailable, PaperLookupAdapter, SearchUnavailable


class PaperMetaDTO(BaseModel):
    """External paper-detail header contract (GET /api/papers/{id}). Mirrors the frontend
    hand-authored ``PaperMetaVM`` (arxivId/title/authors/year/abstract/arxivUrl)."""

    model_config = ConfigDict(extra="forbid")

    arxivId: str
    title: str
    authors: list[str]
    year: int
    abstract: str
    arxivUrl: str


class PaperMetadataService:
    def __init__(self, lookup: PaperLookupAdapter) -> None:
        self._lookup = lookup

    def get_paper_meta(self, paper_id: str) -> PaperMetaDTO | None:
        """Return the detail-header metadata for ``paper_id``, or None when not indexed.

        Raises ``SearchUnavailable`` on a store outage (no fallback for the index — INV-3)."""
        try:
            record = self._lookup.fetch_paper(paper_id)
        except IndexUnavailable as exc:
            raise SearchUnavailable("paper lookup unavailable") from exc
        if record is None:
            return None
        return PaperMetaDTO(
            arxivId=record.arxivId,
            title=record.title,
            authors=list(record.authors),
            year=record.year,
            abstract=record.abstract,
            arxivUrl=record.arxivUrl,
        )
