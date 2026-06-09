"""Shared paper/chunk/sentence Pydantic models.

Every domain module imports from here — single source of truth for the
walking-skeleton's data shapes. Per AGENTS.md §3.2, both #01a search and
#01b ingest live in `domain/papers/` and share these models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# ---------- §4.3 verifier label (4-way, AGENTS.md) ----------
VerifyLabel = Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "NOT_FOUND"]


class Anchor(BaseModel):
    """Per AGENTS.md §4.4: [§n.m] or [p.X ¶Y]."""

    section_id: str  # e.g. "abstract" or "4.2"
    page: int | None = None
    paragraph: int | None = None
    char_start: int = 0
    char_end: int = 0

    def render(self) -> str:
        if self.page is not None and self.paragraph is not None:
            return f"[p.{self.page} ¶{self.paragraph}]"
        return f"[§{self.section_id}]"


class PaperSummary(BaseModel):
    """Search result row — abstract-only view from #01a."""

    id: str  # primary identifier (arxiv_id, doi, or source-native id)
    source: Literal["arxiv", "s2", "openalex", "crossref", "pubmed"] = "arxiv"
    title: str
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""
    year: int | None = None
    venue: str | None = None
    pdf_url: str | None = None
    arxiv_url: str | None = None
    doi: str | None = None       # bare DOI e.g. "10.1145/1234567"
    arxiv_id: str | None = None  # arXiv short ID e.g. "2401.12345"


class Chunk(BaseModel):
    """Anchor-bearing chunk produced by #01b ingest (Sprint 2 will add embedding)."""

    paper_id: str
    chunk_id: str  # stable: paper_id + chunk index
    text: str
    anchor: Anchor


class Paper(BaseModel):
    """Full ingested paper (in-memory, AGENTS.md §4.2 no PDF persistence)."""

    summary: PaperSummary
    sections: list["Section"] = Field(default_factory=list)
    chunks: list[Chunk] = Field(default_factory=list)
    ingested_at: datetime | None = None


class Section(BaseModel):
    section_id: str
    title: str
    paragraphs: list[str] = Field(default_factory=list)


class Sentence(BaseModel):
    """LLM output sentence — §6.5 structured-output shape."""

    text: str
    anchor: Anchor
    verify_label: VerifyLabel = "SUPPORTED"
    confidence: float = 1.0


class GlossaryEntry(BaseModel):
    """§6.2 glossing: term first-occurrence map."""

    english: str
    korean: str
    first_seen_paper_id: str | None = None


Paper.model_rebuild()
