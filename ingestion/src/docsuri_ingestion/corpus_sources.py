from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .domain.enums import FailureReason, SourceName
from .domain.errors import PermanentIngestionError
from .domain.models import MetadataRecord
from .ports import ArxivSourcePort


@dataclass(frozen=True, slots=True)
class SourcePaperRecord:
    source_name: SourceName
    source_id: str
    title: str
    pdf_url: str | None = None
    html_url: str | None = None
    license_url: str | None = None


@dataclass(frozen=True, slots=True)
class CorpusTextCandidate:
    source_name: SourceName
    source_id: str
    source_tier: str
    payload_kind: str
    text: str
    source_url: str


@runtime_checkable
class GrobidPort(Protocol):
    def extract_text(self, pdf: bytes) -> str: ...


class CorpusSourceAdapterSet:
    """Small source boundary for phase-1 Corpus collection.

    Existing arXiv code already handles HTML-first/PDF fallback. Semantic Scholar and OpenAlex
    enter through the PDF->GROBID boundary; raw PDF bytes are consumed in-memory and never
    returned as an artifact.
    """

    def __init__(self, *, arxiv: ArxivSourcePort, grobid: GrobidPort | None = None) -> None:
        self._arxiv = arxiv
        self._grobid = grobid

    def fetch_arxiv_text(self, metadata: MetadataRecord) -> CorpusTextCandidate:
        raw = self._arxiv.fetch_full_text(metadata)
        tier = "ARXIV_PDF" if "/pdf/" in raw.source_url else "ARXIV_HTML"
        return CorpusTextCandidate(
            source_name=SourceName.ARXIV,
            source_id=metadata.arxiv_ref,
            source_tier=tier,
            payload_kind="HTML" if tier == "ARXIV_HTML" else "PDF",
            text=raw.text,
            source_url=raw.source_url,
        )

    def extract_pdf_text(self, record: SourcePaperRecord, pdf: bytes) -> CorpusTextCandidate:
        if record.source_name not in {SourceName.SEMANTIC_SCHOLAR, SourceName.OPENALEX}:
            raise PermanentIngestionError(
                "PDF+GROBID path is only for non-arXiv sources",
                reason=FailureReason.VALIDATION_VIOLATION,
                stage="source",
            )
        if self._grobid is None:
            raise PermanentIngestionError(
                "GROBID adapter is not configured",
                reason=FailureReason.DEPENDENCY_UNAVAILABLE,
                stage="grobid",
            )
        text = self._grobid.extract_text(pdf).strip()
        if not text:
            raise PermanentIngestionError(
                "GROBID returned empty text",
                reason=FailureReason.PARSE_FAILURE,
                stage="grobid",
            )
        return CorpusTextCandidate(
            source_name=record.source_name,
            source_id=record.source_id,
            source_tier=f"{record.source_name.value}_GROBID",
            payload_kind="PDF",
            text=text,
            source_url=record.pdf_url or "",
        )
