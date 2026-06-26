from __future__ import annotations

import pytest

from docsuri_ingestion.adapters.grobid import _tei_to_text
from docsuri_ingestion.domain.errors import PermanentIngestionError
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
