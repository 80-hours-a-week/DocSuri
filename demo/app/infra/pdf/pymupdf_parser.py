"""Lightweight PyMuPDF section extractor (no Docker, no JVM).

Sits between GROBID (high-fidelity but heavy, Sprint 2+) and the
abstract-only fallback. AGENTS.md §3.1 explicitly allows ``pymupdf`` as
the lighter alternative with an accuracy trade-off; for the Sprint 1
walking-skeleton demo this lets a user actually pick *any* span of the
paper for summary/translation instead of just the abstract.

AGENTS.md §4.2 — in-memory only. ``fitz.open(stream=…)`` reads from a
bytes buffer; PDF never touches disk.
"""

from __future__ import annotations

import logging
import re
import statistics
from collections.abc import Iterable

import fitz  # PyMuPDF

from app.domain.papers.models import Section

logger = logging.getLogger(__name__)

# A line counts as a heading when its font is at least this multiple of the
# document body's median font size. Tuned on a few arXiv PDFs; 1.18 catches
# numbered headings without picking up bold-emphasised body words.
_HEADING_FONT_RATIO = 1.18
# Or matches one of these patterns (case where headings are body-sized but
# numerically prefixed — common in IEEE-style papers).
_HEADING_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\d+(\.\d+)*\.?\s+[A-Z][A-Za-z0-9 \-&/,]{2,80}$"),  # "1. Introduction", "3.2 Method"
    re.compile(r"^[A-Z][A-Z\s\-&/]{4,80}$"),                          # "INTRODUCTION", "RELATED WORK"
    re.compile(r"^(Abstract|ABSTRACT)$"),
]
# Headings whose body we drop — references blow up token budgets and add
# little summary value for the demo. Citations remain accessible because
# they're attached inline; we just skip parsing the bibliography list.
_DROP_HEADINGS: tuple[str, ...] = (
    "references", "bibliography", "acknowledgments", "acknowledgements",
)
# Hard cap on total characters per section so an over-eager parser doesn't
# overwhelm the LLM context. Matches §6.4 spirit (length caps).
_MAX_CHARS_PER_SECTION = 6_000

# Known good academic headings — kept regardless of body length so a short
# but real section (e.g. "Acknowledgements") doesn't get filtered.
_KNOWN_HEADINGS: frozenset[str] = frozenset({
    "abstract", "introduction", "background", "method", "methods",
    "methodology", "approach", "model", "experiment", "experiments",
    "experimental", "result", "results", "evaluation", "discussion",
    "conclusion", "conclusions", "related-work", "related",
    "ccs-concepts", "keywords",
})

# Lines that LOOK like headings but actually aren't — preprint metadata,
# author/affiliation blocks, and reference entries are the usual offenders.
_NON_HEADING_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^arXiv:", re.IGNORECASE),          # arXiv:2002.00741v1 […]
    re.compile(r"^\d{4}\.\s+"),                     # citation entry: "2017. Title…"
    re.compile(r"^doi:", re.IGNORECASE),
    re.compile(r"^https?://"),                      # raw URLs
    re.compile(r"^[A-Z][a-z]+\s+[A-Z][a-z]+(\s+[A-Z][a-z]+)?$"),  # "Jibang Wu" / "Aidan N Gomez"
]


def _slugify(title: str) -> str:
    """Stable section_id from a heading: lowercase, alnum/hyphen only."""
    s = re.sub(r"[^A-Za-z0-9]+", "-", title.strip()).strip("-").lower()
    return s or "section"


def _is_heading(text: str, span_size: float, body_size: float) -> bool:
    stripped = text.strip()
    if not stripped or len(stripped) > 120:
        return False
    # Hard reject preprint metadata, citation entries, author names, URLs.
    if any(p.match(stripped) for p in _NON_HEADING_PATTERNS):
        return False
    if span_size >= body_size * _HEADING_FONT_RATIO:
        return True
    return any(p.match(stripped) for p in _HEADING_PATTERNS)


def _section_is_noise(section: "Section") -> bool:
    """Final post-filter: keep canonical headings + anything substantive."""
    title_slug = _slugify(section.title)
    if title_slug in _KNOWN_HEADINGS:
        return False
    body_chars = sum(len(p) for p in section.paragraphs)
    # Short orphan blocks (author names, page numbers that slipped through)
    # carry no useful content for summary/translation.
    return body_chars < 120


def _gather_lines(doc: "fitz.Document") -> Iterable[tuple[str, float]]:
    """Yield (line_text, max_font_size) across the document.

    Each line is reconstructed from PyMuPDF's span dicts; we keep the max
    font size on the line so a single bolded heading word doesn't get lost
    if PyMuPDF spans split mid-line.
    """
    for page in doc:
        block_dict = page.get_text("dict")
        for block in block_dict.get("blocks", []):
            if block.get("type", 0) != 0:
                continue  # skip images
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                text = "".join(s.get("text", "") for s in spans).strip()
                if not text:
                    continue
                max_size = max((s.get("size", 0.0) for s in spans), default=0.0)
                yield text, max_size


def parse(pdf_bytes: bytes, *, drop_references: bool = True) -> list[Section]:
    """Parse a PDF byte stream into anchor-bearing sections.

    Returns sections in document order. If no headings are detected (e.g.
    a scanned PDF without text layer), returns a single ``"body"`` section
    containing everything we could extract — the caller can decide whether
    to fall back further to abstract-only.

    All chunking lives upstream in `domain/papers/ingest.py` so anchor
    construction and chunk size policy stay there.
    """

    # AGENTS.md §4.2 — bytes are read directly from RAM; never persisted.
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        lines = list(_gather_lines(doc))

    if not lines:
        return []

    sizes = [s for _, s in lines if s > 0]
    body_size = statistics.median(sizes) if sizes else 0.0
    logger.debug("pymupdf parse: %d lines, body median font %.2f", len(lines), body_size)

    sections: list[Section] = []
    seen_ids: set[str] = set()
    current_title = "Body"
    current_id = "body"
    current_paragraphs: list[str] = []
    current_buffer: list[str] = []
    drop_current = False

    def flush_paragraph() -> None:
        if current_buffer:
            current_paragraphs.append(" ".join(current_buffer).strip())
            current_buffer.clear()

    def flush_section() -> None:
        nonlocal current_paragraphs
        flush_paragraph()
        if drop_current or not current_paragraphs:
            current_paragraphs = []
            return
        # Enforce per-section cap so the LLM context stays sane.
        joined = "\n\n".join(current_paragraphs)
        if len(joined) > _MAX_CHARS_PER_SECTION:
            joined = joined[:_MAX_CHARS_PER_SECTION].rsplit(" ", 1)[0] + "…"
            current_paragraphs = [joined]
        sections.append(
            Section(
                section_id=current_id,
                title=current_title,
                paragraphs=list(current_paragraphs),
            )
        )
        current_paragraphs = []

    for text, size in lines:
        if _is_heading(text, size, body_size):
            # Heading boundary — close out the prior section first.
            flush_section()
            current_title = text.strip()
            base_id = _slugify(current_title)
            # Make section_id unique even if two headings slugify the same.
            sid, n = base_id, 1
            while sid in seen_ids:
                n += 1
                sid = f"{base_id}-{n}"
            seen_ids.add(sid)
            current_id = sid
            drop_current = drop_references and base_id in _DROP_HEADINGS
        else:
            # Body text: heuristically join words; treat short stand-alone
            # lines (page numbers, footers) as paragraph breaks.
            if len(text) < 4 and not current_buffer:
                continue
            current_buffer.append(text)
            # Treat sentence-ending punctuation followed by short tail as a
            # paragraph hint. Avoid hyphenated line-break stitching for now.
            if text.endswith((".", "!", "?")) and len(" ".join(current_buffer)) > 120:
                flush_paragraph()

    flush_section()
    return [s for s in sections if not _section_is_noise(s)]
