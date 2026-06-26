from __future__ import annotations

from datetime import UTC, datetime

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


class _ExternalSource:
    def __init__(self, record: SourcePaperRecord) -> None:
        self.record = record
        self.since = None
        self.categories = None
        self.fetched_record: SourcePaperRecord | None = None

    def fetch_incremental(self, since, categories):
        self.since = since
        self.categories = tuple(categories)
        return (self.record,)

    def fetch_pdf(self, record: SourcePaperRecord) -> bytes:
        self.fetched_record = record
        return b"%PDF"


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


def test_external_source_incremental_delegates_by_source_name() -> None:
    record = SourcePaperRecord(
        source_name=SourceName.OPENALEX,
        source_id="oa-1",
        title="Paper",
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    provider = _ExternalSource(record)
    adapters = CorpusSourceAdapterSet(
        arxiv=FakeArxivSource([sample_metadata()]),
        openalex=provider,
    )

    records = tuple(
        adapters.fetch_incremental(
            SourceName.OPENALEX,
            datetime(2025, 1, 1, tzinfo=UTC),
            ("cs.LG",),
        )
    )

    assert records == (record,)
    assert provider.since == datetime(2025, 1, 1, tzinfo=UTC)
    assert provider.categories == ("cs.LG",)


def test_source_paper_record_payload_round_trips_retry_metadata() -> None:
    record = SourcePaperRecord(
        source_name=SourceName.SEMANTIC_SCHOLAR,
        source_id="s2-1",
        title="Paper",
        abstract="Abstract",
        authors=("Ada",),
        categories=("cs.LG",),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        published_at=datetime(2025, 12, 1, tzinfo=UTC),
        year=2025,
        pdf_url="https://example.test/p.pdf",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        doi="10.1000/x",
        version=2,
    )

    assert SourcePaperRecord.from_payload(record.to_payload()) == record


def test_external_record_text_fetches_pdf_then_grobid() -> None:
    grobid = _Grobid()
    record = SourcePaperRecord(
        source_name=SourceName.OPENALEX,
        source_id="oa-1",
        title="Paper",
        pdf_url="https://example.test/paper.pdf",
    )
    provider = _ExternalSource(record)
    adapters = CorpusSourceAdapterSet(
        arxiv=FakeArxivSource([sample_metadata()]),
        grobid=grobid,
        openalex=provider,
    )

    candidate = adapters.extract_record_text(record)

    assert provider.fetched_record == record
    assert grobid.seen_pdf == b"%PDF"
    assert candidate.source_tier == "OPENALEX_GROBID"
