from __future__ import annotations

import pytest

from docsuri_ingestion.adapters.local import FakeArxivSource, sample_metadata
from docsuri_ingestion.corpus_sources import CorpusSourceAdapterSet, SourcePaperRecord
from docsuri_ingestion.domain.enums import SourceName
from docsuri_ingestion.domain.errors import PermanentIngestionError


class _Grobid:
    def __init__(self, text: str = "structured full text") -> None:
        self.text = text
        self.seen_pdf: bytes | None = None

    def extract_text(self, pdf: bytes) -> str:
        self.seen_pdf = pdf
        return self.text


def test_arxiv_source_reuses_existing_html_first_adapter() -> None:
    metadata = sample_metadata()
    adapters = CorpusSourceAdapterSet(arxiv=FakeArxivSource([metadata]))

    candidate = adapters.fetch_arxiv_text(metadata)

    assert candidate.source_name is SourceName.ARXIV
    assert candidate.source_tier == "ARXIV_HTML"
    assert candidate.payload_kind == "HTML"
    assert "deterministic ingestion" in candidate.text.lower()


def test_external_pdf_source_uses_grobid_without_returning_pdf_bytes() -> None:
    grobid = _Grobid()
    adapters = CorpusSourceAdapterSet(arxiv=FakeArxivSource([sample_metadata()]), grobid=grobid)
    record = SourcePaperRecord(
        source_name=SourceName.SEMANTIC_SCHOLAR,
        source_id="s2-1",
        title="Paper",
        pdf_url="https://example.test/paper.pdf",
    )

    candidate = adapters.extract_pdf_text(record, b"%PDF")

    assert grobid.seen_pdf == b"%PDF"
    assert candidate.source_tier == "SEMANTIC_SCHOLAR_GROBID"
    assert candidate.payload_kind == "PDF"
    assert candidate.text == "structured full text"
    assert not hasattr(candidate, "pdf")


def test_external_pdf_source_requires_grobid() -> None:
    adapters = CorpusSourceAdapterSet(arxiv=FakeArxivSource([sample_metadata()]))
    record = SourcePaperRecord(
        source_name=SourceName.OPENALEX,
        source_id="oa-1",
        title="Paper",
        pdf_url="https://example.test/paper.pdf",
    )

    with pytest.raises(PermanentIngestionError):
        adapters.extract_pdf_text(record, b"%PDF")
