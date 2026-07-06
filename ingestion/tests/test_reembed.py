"""AWS-free unit tests for the pure helpers of the re-embed rebuild runner. The step functions
themselves hit OpenSearch/Bedrock and are exercised in the live rebuild, not here."""

from docsuri_ingestion.reembed import _embed_text_for_source, _scroll_body
from docsuri_ingestion.settings import IngestionSettings


def test_embed_text_for_abstract_chunk_uses_abstract_field():
    src = {"section": "abstract", "abstract": "the abstract text", "lexicalTerms": ""}
    assert _embed_text_for_source(src) == "the abstract text"


def test_embed_text_for_body_chunk_uses_lexical_terms():
    src = {"section": "1", "lexicalTerms": "normalized body text", "abstract": "abs"}
    assert _embed_text_for_source(src) == "normalized body text"


def test_embed_text_body_chunk_falls_back_to_abstract_then_title():
    assert _embed_text_for_source({"section": "1", "lexicalTerms": "", "abstract": "abs"}) == "abs"
    assert _embed_text_for_source({"section": "1", "title": "the title"}) == "the title"


def test_embed_text_all_empty_returns_empty_string():
    assert _embed_text_for_source({"section": "1"}) == ""
    assert _embed_text_for_source({"section": "abstract"}) == ""


def test_scroll_body_has_no_slice_when_single_shard():
    settings = IngestionSettings()
    body = _scroll_body(settings, page_size=96)
    assert "slice" not in body
    assert body == {"query": {"match_all": {}}, "size": 96}


def test_scroll_body_includes_slice_when_sharded():
    settings = IngestionSettings(DOCSURI_REEMBED_SHARD_COUNT="3", DOCSURI_REEMBED_SHARD="1")
    body = _scroll_body(settings, page_size=50)
    assert body["slice"] == {"id": 1, "max": 3}
    assert body["size"] == 50
