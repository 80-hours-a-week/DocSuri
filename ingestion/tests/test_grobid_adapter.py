from __future__ import annotations

import pytest

from docsuri_ingestion.adapters.grobid import GrobidHttpClient, _tei_to_text
from docsuri_ingestion.domain.errors import PermanentIngestionError, RetriableIngestionError
from docsuri_ingestion.settings import IngestionSettings


def test_grobid_tei_to_text_extracts_body_text() -> None:
    text = _tei_to_text("<TEI><text><body><p>First</p><p>Second</p></body></text></TEI>")
    assert text == "First Second"


def test_grobid_tei_to_text_rejects_invalid_xml() -> None:
    with pytest.raises(PermanentIngestionError):
        _tei_to_text("<TEI>")


def test_corpus_settings_parse_grobid_and_alias_env() -> None:
    settings = IngestionSettings.model_validate(
        {
            "DOCSURI_GROBID_URL": "http://127.0.0.1:8070",
            "DOCSURI_OPENSEARCH_ALIAS": "docsuri-corpus",
            "DOCSURI_CORPUS_SOURCES": "ARXIV,OPENALEX",
        }
    )

    assert settings.grobid_url == "http://127.0.0.1:8070"
    assert settings.opensearch_alias == "docsuri-corpus"
    assert settings.corpus_sources == "ARXIV,OPENALEX"


class _Response:
    def __init__(self, status_code: int, text: str = "<TEI><text>ok</text></TEI>") -> None:
        self.status_code = status_code
        self.text = text


def test_grobid_429_is_retriable(monkeypatch) -> None:
    def post(*args, **kwargs):
        del args, kwargs
        return _Response(429)

    import httpx

    monkeypatch.setattr(httpx, "post", post)
    client = GrobidHttpClient(base_url="http://grobid.test")

    with pytest.raises(RetriableIngestionError):
        client.extract_text(b"%PDF")


def test_grobid_bad_pdf_400_is_permanent(monkeypatch) -> None:
    def post(*args, **kwargs):
        del args, kwargs
        return _Response(400)

    import httpx

    monkeypatch.setattr(httpx, "post", post)
    client = GrobidHttpClient(base_url="http://grobid.test")

    with pytest.raises(PermanentIngestionError):
        client.extract_text(b"%PDF")
