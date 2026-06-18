"""InputRefiner — structure-aware cleaning (BR-S3 / Q2 / Q6).

REMOVE (non-experimental noise only): references/bibliography, header/footer,
page numbers, copyright lines, author/affiliation lines.
PRESERVE (may carry experimental info): Table/Figure captions, Appendix,
Supplementary Results, LaTeX formulas. Over-removal would drop result numbers (Q2).

Section derivation (Q6): U1 does not persist section structure, so headings are
recognized here by regex → (label, char span); failure degrades to span-only.
"""

from __future__ import annotations

import re

from .models import RefinedSource, Section

# A references/bibliography heading ends the body (everything after is noise).
_REFERENCES_RE = re.compile(r"^\s*(references|bibliography)\s*$", re.IGNORECASE | re.MULTILINE)

# Non-experimental noise lines (conservative — only obvious boilerplate).
_PAGE_NUM_RE = re.compile(r"^\s*\d{1,4}\s*$")
_COPYRIGHT_RE = re.compile(r"(?i)\b(copyright|\(c\)|©|all rights reserved)\b")
_AUTHOR_AFFIL_RE = re.compile(r"(?i)^\s*(corresponding author|affiliation|e-?mail)\b")
_HEADER_FOOTER_RE = re.compile(r"(?i)^\s*(preprint|under review|to appear in|arxiv:)\b")

# Section / caption / formula recognition (preserve captions & formulas).
_SECTION_RE = re.compile(
    r"^\s*(?:(?:\d+(?:\.\d+)*)\s+[A-Z][^\n]{0,80}|[A-Z][A-Z \-]{3,60})\s*$", re.MULTILINE
)
_CAPTION_RE = re.compile(r"^\s*(table|figure|fig\.?)\s*\d+[:.]\s.*$", re.IGNORECASE | re.MULTILINE)
_FORMULA_RE = re.compile(
    r"\$[^$]+\$|\\\[[^\]]+\\\]|\\begin\{equation\}.*?\\end\{equation\}", re.DOTALL
)
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _strip_noise_lines(text: str) -> str:
    kept: list[str] = []
    for line in text.splitlines():
        if _PAGE_NUM_RE.match(line) and line.strip():
            continue
        if _COPYRIGHT_RE.search(line):
            continue
        if _AUTHOR_AFFIL_RE.match(line):
            continue
        if _HEADER_FOOTER_RE.match(line):
            continue
        kept.append(line)
    return "\n".join(kept)


def _estimate_tokens(text: str) -> int:
    """Cheap, deterministic token estimate (~4 chars/token). Real caps are a runtime tune."""
    return max(1, len(text) // 4)


class InputRefiner:
    def refine(self, raw: str) -> RefinedSource:
        # Sanitize first (control chars; injection-isolation happens in the prompt layer).
        text = _CONTROL_RE.sub("", raw)

        # Cut references/bibliography tail (pure noise — BR-S3).
        match = _REFERENCES_RE.search(text)
        if match:
            text = text[: match.start()]

        # Remove non-experimental boilerplate lines (Q2 — captions/appendix untouched).
        body = _strip_noise_lines(text).strip()

        captions = tuple(m.group(0).strip() for m in _CAPTION_RE.finditer(body))
        formulas = tuple(m.group(0).strip() for m in _FORMULA_RE.finditer(body))
        sections = self._derive_sections(body)

        return RefinedSource(
            body=body,
            sections=sections,
            captions=captions,
            formulas=formulas,
            token_count=_estimate_tokens(body),
        )

    @staticmethod
    def _derive_sections(body: str) -> tuple[Section, ...]:
        """Recognize heading lines → (label, span). Empty when none found (span-only later)."""
        out: list[Section] = []
        for m in _SECTION_RE.finditer(body):
            label = m.group(0).strip()
            out.append(Section(label=label, start=m.start(), end=m.end()))
        return tuple(out)
