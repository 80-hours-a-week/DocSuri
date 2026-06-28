"""GROBID TEI -> structured DocModel (BR-30, D1): sections, data tables, image formulas/figures."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from docsuri_ingestion.docmodel.tei import parse_tei_to_docmodel
from docsuri_shared.dtos import SourceTier

_NS = 'xmlns="http://www.tei-c.org/ns/1.0"'

_TEI = f"""
<TEI {_NS}>
  <text><body>
    <div>
      <head>1. Introduction</head>
      <p>We study diffusion over <ref>protein</ref> structure.</p>
      <formula><label>(1)</label>E = mc^2</formula>
    </div>
    <div>
      <head>2. Method</head>
      <p>The backbone is modelled directly.</p>
    </div>
    <figure type="table" coords="3,10,20,100,50">
      <head>Table 1</head>
      <figDesc>Ablation results.</figDesc>
      <table>
        <row><cell>model</cell><cell>score</cell></row>
        <row><cell>ours</cell><cell>0.92</cell></row>
      </table>
    </figure>
    <figure coords="2,10,40,100,50">
      <head>Figure 1</head>
      <figDesc>The pipeline.</figDesc>
    </figure>
  </body></text>
</TEI>
"""


def _parse(tei: str):
    return parse_tei_to_docmodel(
        tei,
        paper_id="src-abc",
        version=1,
        title="A Paper",
        abstract="An abstract.",
        source_tier=SourceTier.pdf,
        parser_version="pv",
        schema_version="sv",
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_sections_and_paragraphs_preserve_order_and_titles() -> None:
    doc = _parse(_TEI)
    titles = [s.title for s in doc.sections]
    # abstract section first, then the two body divs, then the grouped figures/tables section
    assert titles[:3] == ["Abstract", "1. Introduction", "2. Method"]
    intro = doc.sections[1]
    assert intro.blocks[0].root.type == "paragraph"
    assert "diffusion over protein structure" in intro.blocks[0].root.text


def test_block_formula_is_image_fallback_no_latex() -> None:
    doc = _parse(_TEI)
    intro = doc.sections[1]
    formula = next(b.root for b in intro.blocks if b.root.type == "formula")
    # PDF path: no reliable LaTeX -> image assetRef, anchor label from <label>
    assert formula.latex is None
    assert formula.assetRef is not None
    assert formula.assetRef.type.value == "formula"
    assert formula.assetRef.assetId == "src-abc:v1:formula:0"
    assert formula.anchorLabel == "(1)"


def test_table_is_structured_data_not_image() -> None:
    doc = _parse(_TEI)
    figures = doc.sections[-1]  # trailing grouped section
    table = next(b.root for b in figures.blocks if b.root.type == "table")
    assert table.anchorLabel == "Table 1"
    assert table.caption == "Ablation results."
    assert [c.text for c in table.rows[0].cells] == ["model", "score"]
    assert [c.text for c in table.rows[1].cells] == ["ours", "0.92"]


def test_figure_is_image_assetref_with_caption() -> None:
    doc = _parse(_TEI)
    figures = doc.sections[-1]
    figure = next(b.root for b in figures.blocks if b.root.type == "figure")
    assert figure.assetRef.assetId == "src-abc:v1:figure:0"
    assert figure.caption == "The pipeline."
    assert figure.anchorLabel == "Figure 1"


def test_full_text_excludes_image_formula_but_keeps_table_data() -> None:
    doc = _parse(_TEI)
    assert "0.92" in doc.fullText  # table cell data is searchable
    assert "mc^2" not in doc.fullText  # image-only formula contributes no text


def test_deterministic_same_tei_same_docmodel() -> None:
    assert _parse(_TEI).model_dump() == _parse(_TEI).model_dump()


def test_malformed_tei_raises() -> None:
    import xml.etree.ElementTree as ET

    with pytest.raises(ET.ParseError):
        _parse("<TEI>")
