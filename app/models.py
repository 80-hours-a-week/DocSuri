from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class LengthPreset(StrEnum):
    tldr = "tldr"
    paragraph = "paragraph"
    page = "page"


class AnglePreset(StrEnum):
    contribution = "contribution"
    method = "method"
    results = "results"
    critical = "critical"


class PaperSummary(BaseModel):
    id: str
    title: str = "Untitled paper"
    abstract: str | None = None


class PaperChunk(BaseModel):
    id: str | None = None
    paper_id: str
    text: str
    anchor: str
    section: str | None = None
    page: int | None = None
    paragraph: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaperDocument(BaseModel):
    id: str
    title: str = "Untitled paper"
    text: str
    abstract: str | None = None
    chunks: list[PaperChunk] = Field(default_factory=list)


class GlossaryTerm(BaseModel):
    source: str
    target: str
    first_seen: bool = False


class Verification(BaseModel):
    label: str
    rationale: str


class SummarySentence(BaseModel):
    text: str
    anchors: list[str]
    verification: Verification


class SummaryRequest(BaseModel):
    paper_id: str
    session_id: str = "default"
    length_preset: LengthPreset = LengthPreset.paragraph
    angle_preset: AnglePreset = AnglePreset.contribution


class SummaryResponse(BaseModel):
    paper_id: str
    title: str
    length_preset: LengthPreset
    angle_preset: AnglePreset
    sentences: list[SummarySentence]
    glossary: list[GlossaryTerm]


class TranslateRequest(BaseModel):
    paper_id: str
    session_id: str = "default"
    section_id: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    selected_text: str | None = None
    preserve_citations: bool = True
    first_mention_glossing: bool = True


class TranslationUnit(BaseModel):
    anchor: str
    source_text: str
    translated_text: str
    verification: Verification


class TranslateResponse(BaseModel):
    paper_id: str
    title: str
    units: list[TranslationUnit]
    glossary: list[GlossaryTerm]
