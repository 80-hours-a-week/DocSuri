"""U2 Comprehend DTOs.

The cross-unit DTOs in this file intentionally mirror
aidlc-docs/design-artifacts/units/unit-u2-comprehend.md §3.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from docsuri.u0.ports import KoTranslation, Persona

SectionKey = Literal["question", "method", "result", "limit"]
DocumentSourceKind = Literal["raw_text", "pdf_path", "arxiv_url", "url"]
InputMode = Literal["desktop", "mobile"]


class PaperSection(BaseModel):
    id: str
    title: str
    text: str


class PaperFigure(BaseModel):
    id: str
    caption: str
    context: str = ""


class PaperText(BaseModel):
    paper_id: str
    title: str
    sections: list[PaperSection]
    figures: list[PaperFigure] = Field(default_factory=list)
    source_url: str | None = None

    def plain_text(self) -> str:
        return "\n\n".join(f"{section.title}\n{section.text}" for section in self.sections)


class DocumentSource(BaseModel):
    kind: DocumentSourceKind
    value: str
    paper_id: str | None = None
    title: str | None = None


class SummarySections(BaseModel):
    question: str
    method: str
    result: str
    limit: str

    def combined_text(self) -> str:
        return "\n".join(
            [self.question, self.method, self.result, self.limit]
        )


class UsageCost(BaseModel):
    tokens_in: int
    tokens_out: int


class VocabExplanation(BaseModel):
    term: str
    ko: str
    note: str = ""

    @classmethod
    def from_translation(cls, translation: KoTranslation) -> "VocabExplanation":
        return cls(term=translation.term, ko=translation.ko, note=translation.note)


class SummaryResult(BaseModel):
    paper_id: str
    mode: Persona
    sections: SummarySections
    vocab_explanations: list[VocabExplanation] = Field(default_factory=list)
    cost: UsageCost


class TranslationSelection(BaseModel):
    source_excerpt: str
    input_mode: InputMode


class TranslationResult(BaseModel):
    source_excerpt: str
    target_text: str
    glossary_hits: list[VocabExplanation] = Field(default_factory=list)


class FigureContext(BaseModel):
    caption: str
    context: str = ""
    touch_target_width_css_px: int = 44
    touch_target_height_css_px: int = 44


class ReadabilityMetrics(BaseModel):
    sentence_count: int
    average_eojeol_per_sentence: float
    max_eojeol_per_sentence: int
    difficult_token_count: int = 0


class ReadabilityReport(BaseModel):
    mode: Persona
    passed: bool
    metrics: ReadabilityMetrics
    issues: list[str] = Field(default_factory=list)


class SectionToggleState(BaseModel):
    collapsed: dict[SectionKey, bool] = Field(
        default_factory=lambda: {
            "question": False,
            "method": False,
            "result": False,
            "limit": False,
        }
    )
