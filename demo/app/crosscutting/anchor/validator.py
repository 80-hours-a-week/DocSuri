"""Anchor validator (AGENTS.md §4.4).

Sprint 1 stub — verifies format only (Sprint 2 Owner port adds GROBID
index matching so a forged `[§7.3]` to a non-existent section is rejected).
"""

from __future__ import annotations

import re

from app.domain.papers.models import Anchor, Paper

SECTION_RE = re.compile(r"\[§([\w\.]+)\]")
PAGE_RE = re.compile(r"\[p\.(\d+)\s*¶(\d+)\]")


def parse(raw: str) -> Anchor | None:
    if m := SECTION_RE.search(raw):
        return Anchor(section_id=m.group(1))
    if m := PAGE_RE.search(raw):
        return Anchor(section_id=f"p{m.group(1)}", page=int(m.group(1)), paragraph=int(m.group(2)))
    return None


def exists_in(anchor: Anchor, paper: Paper) -> bool:
    """Check anchor points to a real span. Sprint 1: section_id match only."""
    for s in paper.sections:
        if s.section_id == anchor.section_id:
            return True
    return False
