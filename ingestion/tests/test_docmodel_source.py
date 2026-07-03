"""ArxivHttpSource.fetch_html_source (BR-30, Q6 ladder): ar5iv -> native HTML tiering.

ar5iv is preferred: its LaTeXML HTML is what the doc-model parser's sanitizer is built for,
whereas native arXiv HTML leaks raw TeX/pgf into fullText. Native HTML stays a last-resort
rung so a paper ar5iv cannot render still yields a doc-model source.
"""

from __future__ import annotations

from docsuri_shared.dtos import SourceTier

from docsuri_ingestion.adapters.arxiv import ArxivHttpSource


def _source_with(html_by_base: dict[str, str]) -> ArxivHttpSource:
    src = ArxivHttpSource()

    def fake_get_html_at(base: str, arxiv_id: str) -> str | None:
        return html_by_base.get(base)

    src._get_html_at = fake_get_html_at  # type: ignore[method-assign]
    return src


def test_prefers_ar5iv_when_both_available() -> None:
    src = _source_with(
        {
            "https://ar5iv.labs.arxiv.org/html": "<html>ar5iv</html>",
            "https://arxiv.org/html": "<html>native</html>",
        }
    )
    result = src.fetch_html_source("2401.00001v1")
    assert result == ("<html>ar5iv</html>", SourceTier.ar5iv)


def test_uses_ar5iv_tier() -> None:
    src = _source_with({"https://ar5iv.labs.arxiv.org/html": "<html>ar5iv</html>"})
    result = src.fetch_html_source("2401.00001v1")
    assert result == ("<html>ar5iv</html>", SourceTier.ar5iv)


def test_falls_back_to_native_html_when_ar5iv_unavailable() -> None:
    src = _source_with({"https://arxiv.org/html": "<html>native</html>"})
    result = src.fetch_html_source("2401.00001v1")
    assert result == ("<html>native</html>", SourceTier.native_html)


def test_returns_none_when_no_html_rung_yields() -> None:
    assert _source_with({}).fetch_html_source("2401.00001v1") is None
