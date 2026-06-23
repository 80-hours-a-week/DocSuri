"""BR-29 full-text extraction — HTML→text purity/idempotence + fetch HTML→PDF fallback."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from docsuri_ingestion.adapters.local import sample_metadata
from docsuri_ingestion.domain.models import RawDocument
from docsuri_ingestion.full_text_extraction import html_to_text


def test_html_to_text_drops_script_style_and_keeps_blocks() -> None:
    html = (
        "<html><head><style>p{color:red}</style></head>"
        "<body><h1>Title</h1><p>Hello   world</p>"
        "<script>steal()</script><p>Second  line</p></body></html>"
    )
    assert html_to_text(html) == "Title\nHello world\nSecond line"


def test_html_to_text_empty_inputs() -> None:
    assert html_to_text("") == ""
    assert html_to_text("<html><body></body></html>") == ""


def test_html_to_text_idempotent_on_plain_text() -> None:
    plain = "Title\nHello world\nSecond line"
    assert html_to_text(plain) == plain


@given(st.text())
def test_html_to_text_never_raises_and_has_no_replacement_chars(text: str) -> None:
    out = html_to_text(text)
    # The #139 defect was decoding a compressed payload into replacement chars; the HTML
    # path must never emit U+FFFD from arbitrary text input.
    assert "�" not in out


class _FakeSource:
    """Minimal ArxivHttpSource double exercising the HTML→PDF fallback branch (BR-29).

    Both branches yield normalized *plain text* only (the viewer renders plain text); HTML is
    the preferred source, PDF the fallback.
    """

    def __init__(self, *, html: str | None, pdf_text: str) -> None:
        self._html = html
        self._pdf_text = pdf_text

    def fetch_full_text(self, metadata) -> RawDocument:
        if self._html is not None:
            text = html_to_text(self._html)
            if text:
                return RawDocument(metadata=metadata, text=text, source_url="html://x")
        return RawDocument(metadata=metadata, text=self._pdf_text, source_url="pdf://x")


def test_fetch_prefers_html_source_as_plain_text() -> None:
    meta = sample_metadata()
    raw = _FakeSource(html="<p>Body text</p>", pdf_text="ignored").fetch_full_text(meta)
    assert raw.text == "Body text"
    assert raw.source_url == "html://x"


def test_fetch_falls_back_to_pdf_when_no_html() -> None:
    meta = sample_metadata()
    raw = _FakeSource(html=None, pdf_text="Extracted PDF body").fetch_full_text(meta)
    assert raw.text == "Extracted PDF body"
    assert raw.source_url == "pdf://x"
