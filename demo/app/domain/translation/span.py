"""SpanResolver — (paper_id, section_id, char_start, char_end) → text + ±200 char context.

Sprint 1 walking-skeleton: pulls from the in-memory store. The
±200-char context window gives the LLM enough surrounding sentences
to translate cohesively without bloating the prompt.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.infra.storage.memory import store

CONTEXT_RADIUS = 200


@dataclass
class ResolvedSpan:
    paper_id: str
    section_id: str
    char_start: int
    char_end: int
    span_text: str
    context: str


class SpanResolver:
    async def resolve(
        self,
        paper_id: str,
        section_id: str,
        char_start: int,
        char_end: int,
    ) -> ResolvedSpan:
        paper = await store.get(paper_id)
        if paper is None:
            raise KeyError(paper_id)

        section_text = _section_text(paper, section_id)
        if section_text is None:
            raise KeyError(f"{paper_id}::{section_id}")

        if char_start < 0 or char_end > len(section_text) or char_start >= char_end:
            raise ValueError(
                f"invalid span: start={char_start} end={char_end} "
                f"section_len={len(section_text)}"
            )

        span_text = section_text[char_start:char_end]
        ctx_start = max(0, char_start - CONTEXT_RADIUS)
        ctx_end = min(len(section_text), char_end + CONTEXT_RADIUS)
        context = section_text[ctx_start:ctx_end]

        return ResolvedSpan(
            paper_id=paper_id,
            section_id=section_id,
            char_start=char_start,
            char_end=char_end,
            span_text=span_text,
            context=context,
        )


def _section_text(paper, section_id: str) -> str | None:  # noqa: ANN001 (Paper is Pydantic)
    if section_id == "abstract":
        return paper.summary.abstract
    for section in paper.sections:
        if section.section_id == section_id:
            return "\n\n".join(section.paragraphs)
    return None
