"""GROBID TEI XML → ``list[Section]`` conversion.

Uses stdlib ``xml.etree.ElementTree``. Handles the TEI default namespace
(``xmlns="http://www.tei-c.org/ns/1.0"``) by prefixing every tag lookup.

Sprint 1 scope (sufficient for the walking skeleton):
    - ``<teiHeader>/<fileDesc>/<titleStmt>/<title>`` → paper title
    - ``<body>/<div>`` → :class:`Section` (heading from optional ``<head>``)
    - ``<p>`` within a div → paragraph entry
    - ``<abstract>`` under ``<profileDesc>`` → an "abstract" section

We deliberately do not parse tables, equations, or refs — Sprint 2/3 work.
"""

from __future__ import annotations

import logging
from xml.etree import ElementTree as ET

from app.domain.papers.models import Section

logger = logging.getLogger(__name__)

TEI_NS = "http://www.tei-c.org/ns/1.0"
NS = {"tei": TEI_NS}


def _tag(name: str) -> str:
    """Qualified tag for find/findall calls."""
    return f"{{{TEI_NS}}}{name}"


def _text_of(elem: ET.Element | None) -> str:
    """Recursive text content of an element, joining nested runs with spaces."""
    if elem is None:
        return ""
    parts: list[str] = []
    if elem.text:
        parts.append(elem.text)
    for child in elem:
        parts.append(_text_of(child))
        if child.tail:
            parts.append(child.tail)
    return " ".join(p.strip() for p in parts if p and p.strip())


def parse_title(root: ET.Element) -> str:
    """Pull the paper title from the TEI header. Empty string if absent."""
    title_el = root.find(".//tei:teiHeader//tei:titleStmt/tei:title", NS)
    return _text_of(title_el)


def parse_abstract(root: ET.Element) -> Section | None:
    """Build an ``abstract`` section from ``profileDesc/abstract`` if present."""
    abs_el = root.find(".//tei:profileDesc/tei:abstract", NS)
    if abs_el is None:
        return None
    paragraphs = [
        _text_of(p) for p in abs_el.findall(".//tei:p", NS) if _text_of(p)
    ]
    if not paragraphs:
        text = _text_of(abs_el)
        paragraphs = [text] if text else []
    return Section(
        section_id="abstract",
        title="Abstract",
        paragraphs=paragraphs,
    )


def parse_body_sections(root: ET.Element) -> list[Section]:
    """Convert each top-level ``<body>/<div>`` into a :class:`Section`.

    ``section_id`` is a 1-based string index ("1", "2", …) — GROBID's TEI
    output doesn't expose stable numeric ids, but we want anchors stable
    within one ingest, which is enough for Sprint 1.
    """
    body = root.find(".//tei:text/tei:body", NS)
    if body is None:
        return []
    sections: list[Section] = []
    for i, div in enumerate(body.findall("tei:div", NS), start=1):
        head_el = div.find("tei:head", NS)
        title = _text_of(head_el) or f"Section {i}"
        paragraphs = [
            _text_of(p) for p in div.findall("tei:p", NS) if _text_of(p)
        ]
        if not paragraphs:
            # Skip empty divs — they're usually GROBID artefacts (figure
            # captions or floating refs) that add no semantic content.
            continue
        sections.append(
            Section(section_id=str(i), title=title, paragraphs=paragraphs)
        )
    return sections


def parse(tei_xml: str) -> list[Section]:
    """Entry point — TEI XML string → list of :class:`Section`.

    Returns at minimum the abstract section if it parses, even when the
    body is empty. Returns ``[]`` only if the XML is unparseable or truly
    empty — the caller treats that as a fall-through to the abstract-only
    construction.
    """
    try:
        root = ET.fromstring(tei_xml)
    except ET.ParseError as exc:
        logger.warning("TEI parse error: %s", exc)
        return []

    sections: list[Section] = []
    if (abstract := parse_abstract(root)) is not None:
        sections.append(abstract)
    sections.extend(parse_body_sections(root))
    return sections
